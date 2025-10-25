"""
Robust experiment runner with state management, batching, and resumption
"""
import argparse
import asyncio
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from src.core.models import get_model_response, load_models, get_default_layer3_evaluator
from src.core.scenarios import load_scenarios
from src.core.constitutions import load_constitutions
from src.core.prompts import (
    build_fact_establishment_prompt,
    build_constitutional_reasoning_prompt,
    build_integrity_evaluation_prompt
)
from src.core.experiment_state import ExperimentManager, TestDefinition, TestStatus
from src.core.graceful_parser import GracefulJsonParser, ParseStatus
from src.core.truncation_detector import TruncationDetector
from src.core.manifest_generator import save_manifest

# Phase 1 Configuration: Skip Layer 1 (facts from scenario JSON)
SKIP_LAYER_1 = True


def clean_json_response(response: str) -> str:
    """Clean JSON response by removing markdown code blocks"""
    clean = response.strip()
    if clean.startswith('```json'):
        clean = clean[7:]
    if clean.endswith('```'):
        clean = clean[:-3]
    return clean.strip()


def robust_json_parse(response: str) -> dict:
    """
    Robust JSON parsing for model responses with multiple fallback methods
    Handles issues with Llama and other models that may return malformed JSON
    """
    import re
    
    # Method 1: Standard cleaning
    try:
        clean = clean_json_response(response)
        return json.loads(clean)
    except:
        pass
    
    # Method 2: Remove control characters
    try:
        clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', response)
        clean = clean_json_response(clean)
        return json.loads(clean)
    except:
        pass
    
    # Method 3: Extract first complete JSON object
    try:
        start = response.find('{')
        if start == -1:
            raise ValueError("No JSON object found")
            
        brace_count = 0
        end = start
        in_string = False
        escape_next = False
        
        for i, char in enumerate(response[start:], start):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
        
        if brace_count == 0:
            json_str = response[start:end+1]
            # Clean any control characters
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
            return json.loads(json_str)
            
    except:
        pass
    
    # Method 4: Remove trailing content after last }
    try:
        clean = clean_json_response(response)
        last_brace = clean.rfind('}')
        if last_brace != -1:
            clean = clean[:last_brace+1]
        return json.loads(clean)
    except:
        pass
    
    raise ValueError(f"Could not parse JSON from response: {response[:200]}...")


async def run_single_test(
    test_def: TestDefinition,
    scenario_data: Dict,
    constitution_data: Dict,
    model_data: Dict,
    experiment_manager: ExperimentManager
) -> bool:
    """
    Run a single test through the 3-layer pipeline
    Returns True if successful, False if failed
    """
    test_id = test_def.test_id
    # Use experiment_id for organizing manual review files
    parser = GracefulJsonParser(experiment_id=experiment_manager.experiment_id)
    
    try:
        # Mark as in progress
        experiment_manager.mark_test_in_progress(test_id)

        print(f"\n🔄 Starting: {test_id}")

        # Layer 1: Establish facts
        try:
            if SKIP_LAYER_1:
                # Phase 1: Use facts directly from scenario JSON
                facts = {
                    "establishedFacts": scenario_data.established_facts,
                    "ambiguousElements": scenario_data.ambiguous_elements,
                    "keyQuestions": []  # Not present in scenario JSON structure
                }
                print(f"📋 Using facts from scenario JSON (Layer 1 bypassed)")

                # Save Layer 1 output (facts from JSON, no API call)
                layer1_data = {
                    "testId": test_id,
                    "timestamp": datetime.now().isoformat(),
                    "source": "scenario_json",
                    "skipped": True,
                    "facts": facts
                }
                experiment_manager.save_layer_result(test_id, 1, layer1_data)
                experiment_manager.update_layer_status(test_id, 1, "skipped")
            else:
                # Phase 2+: Establish facts via API call
                fact_prompt = build_fact_establishment_prompt(scenario_data)
                fact_response = await get_model_response(
                    model_id="gpt-4o",
                    prompt=fact_prompt,
                    temperature=0.3,
                    max_tokens=1000
                )

                # Parse facts with graceful fallback
                facts, fact_status = parser.parse_constitutional_response(fact_response, f"{test_id}_facts")
                if fact_status == ParseStatus.MANUAL_REVIEW:
                    print(f"⚠️  Facts parsing needs manual review for {test_id}")
                elif fact_status == ParseStatus.PARTIAL_SUCCESS:
                    print(f"⚠️  Partial facts extraction for {test_id}")

                # Ensure we have the basic structure for facts
                if 'establishedFacts' not in facts:
                    facts['establishedFacts'] = ["[MANUAL_REVIEW] See raw response"]
                if 'ambiguousElements' not in facts:
                    facts['ambiguousElements'] = ["[MANUAL_REVIEW] See raw response"]

                # Save Layer 1 output (facts from API)
                layer1_data = {
                    "testId": test_id,
                    "timestamp": datetime.now().isoformat(),
                    "source": "gpt-4o",
                    "skipped": False,
                    "facts": facts,
                    "parseStatus": fact_status.value
                }
                experiment_manager.save_layer_result(test_id, 1, layer1_data)
                experiment_manager.update_layer_status(test_id, 1, "completed", "gpt-4o")

        except Exception as e:
            error_msg = f"Layer 1 (fact establishment) failed: {str(e)}"
            experiment_manager.update_layer_status(test_id, 1, "failed", "gpt-4o", error_msg)
            experiment_manager.mark_test_failed(test_id, error_msg)
            print(f"❌ {test_id} - {error_msg}")
            return False

        # Layer 2: Constitutional reasoning (with truncation detection and retry)
        try:
            # Note: ambiguous_elements are documented in scenario JSON but NOT passed to prompt
            # This allows constitutional frameworks to identify their own value tensions
            reasoning_prompt = build_constitutional_reasoning_prompt(
                scenario=scenario_data,
                constitution=constitution_data,
                established_facts=facts['establishedFacts']
            )

            # Try with increasing max_tokens if truncated
            truncation_detector = TruncationDetector()
            max_tokens_constitutional = 8000  # Start with baseline
            max_retries = 3

            for attempt in range(max_retries):
                constitutional_response = await get_model_response(
                    model_id=model_data['id'],
                    prompt=reasoning_prompt,
                    system_prompt=constitution_data.system_prompt,
                    temperature=0.7,
                    max_tokens=max_tokens_constitutional
                )

                # Parse constitutional response with graceful fallback
                response_data, constitutional_status = parser.parse_constitutional_response(constitutional_response, f"{test_id}_constitutional")

                # Check if truncated
                is_truncated, trunc_reason = truncation_detector.is_truncated(
                    constitutional_response,
                    parse_success=(constitutional_status == ParseStatus.SUCCESS)
                )

                if not is_truncated or constitutional_status == ParseStatus.SUCCESS:
                    # Success or not truncated - keep the result
                    break

                # Truncated - retry with higher limit
                if attempt < max_retries - 1:
                    new_limit = truncation_detector.get_next_token_limit(max_tokens_constitutional)
                    print(f"⚠️  Response truncated ({trunc_reason}), retrying with max_tokens={new_limit}")
                    max_tokens_constitutional = new_limit
                else:
                    print(f"⚠️  Max retries reached, using partial response")

            if constitutional_status == ParseStatus.MANUAL_REVIEW:
                print(f"⚠️  Constitutional response parsing needs manual review for {test_id}")
            elif constitutional_status == ParseStatus.PARTIAL_SUCCESS:
                print(f"⚠️  Partial constitutional response extraction for {test_id}")

            # Log the final max_tokens used for this model
            if max_tokens_constitutional > 8000:
                print(f"📊 {model_data['id']} required {max_tokens_constitutional} tokens for complete response")

            # Save Layer 2 output (constitutional reasoning)
            layer2_data = {
                "testId": test_id,
                "timestamp": datetime.now().isoformat(),
                "model": model_data['id'],
                "constitution": constitution_data.id,
                "scenario": scenario_data.id,
                "response": response_data,
                "parseStatus": constitutional_status.value,
                "maxTokensUsed": max_tokens_constitutional
            }
            experiment_manager.save_layer_result(test_id, 2, layer2_data)
            experiment_manager.update_layer_status(test_id, 2, "completed", model_data['id'])

        except Exception as e:
            error_msg = f"Layer 2 (constitutional reasoning with {model_data['id']}) failed: {str(e)}"
            experiment_manager.update_layer_status(test_id, 2, "failed", model_data['id'], error_msg)
            experiment_manager.mark_test_failed(test_id, error_msg)
            print(f"❌ {test_id} - {error_msg}")
            return False

        # Layer 3: Integrity evaluation (using Claude for consistency)
        try:
            eval_prompt = build_integrity_evaluation_prompt(
                established_facts=facts['establishedFacts'],
                ambiguous_elements=facts['ambiguousElements'],
                constitutional_response=response_data
            )

            integrity_response = await get_model_response(
                model_id="claude-sonnet-4-5",
                prompt=eval_prompt,
                temperature=0.3,
                max_tokens=2000
            )

            # Parse integrity response with graceful fallback
            integrity_data, integrity_status = parser.parse_integrity_response(integrity_response, f"{test_id}_integrity")
            if integrity_status == ParseStatus.MANUAL_REVIEW:
                print(f"⚠️  Integrity response parsing needs manual review for {test_id}")
            elif integrity_status == ParseStatus.PARTIAL_SUCCESS:
                print(f"⚠️  Partial integrity response extraction for {test_id}")

            # Calculate overall score (handle manual review cases)
            if integrity_status == ParseStatus.MANUAL_REVIEW:
                # Use -1 scores for manual review (already set in fallback)
                overall_score = -1
            else:
                # Calculate normal score
                overall_score = (
                    integrity_data['factualAdherence']['score'] +
                    integrity_data['valueTransparency']['score'] +
                    integrity_data['logicalCoherence']['score']
                ) / 3
                integrity_data['overallScore'] = round(overall_score)

            # Save Layer 3 output (integrity evaluation)
            layer3_data = {
                "testId": test_id,
                "timestamp": datetime.now().isoformat(),
                "evaluationModel": "claude-sonnet-4-5",
                "integrityEvaluation": integrity_data,
                "parseStatus": integrity_status.value
            }
            experiment_manager.save_layer_result(test_id, 3, layer3_data)
            experiment_manager.update_layer_status(test_id, 3, "completed", "claude-sonnet-4-5")

            # Compile complete result
            result = {
                "testId": test_id,
                "timestamp": datetime.now().isoformat(),
                "scenario": scenario_data.model_dump(),
                "constitution": constitution_data.id,
                "model": model_data['id'],
                "facts": facts,
                "constitutionalResponse": response_data,
                "integrityEvaluation": integrity_data
            }

            # Mark as completed
            experiment_manager.mark_test_completed(test_id, result)

            print(f"✅ {test_id} - Score: {integrity_data['overallScore']}/100")
            return True

        except Exception as e:
            error_msg = f"Layer 3 (integrity evaluation with claude-sonnet-4-5) failed: {str(e)}"
            experiment_manager.update_layer_status(test_id, 3, "failed", "claude-sonnet-4-5", error_msg)
            experiment_manager.mark_test_failed(test_id, error_msg)
            print(f"❌ {test_id} - {error_msg}")
            return False
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        experiment_manager.mark_test_failed(test_id, error_msg)
        print(f"❌ {test_id} - Error: {error_msg}")
        return False


async def run_batch(
    batch: List[TestDefinition],
    scenarios_dict: Dict,
    constitutions_dict: Dict,
    models_dict: Dict,
    experiment_manager: ExperimentManager,
    batch_num: int,
    total_batches: int
) -> Dict[str, int]:
    """
    Run a batch of tests in parallel
    """
    print(f"\n{'='*80}")
    print(f"Batch {batch_num}/{total_batches} - {len(batch)} tests")
    print(f"{'='*80}")
    
    # Create coroutines for all tests in batch
    tasks = []
    for test_def in batch:
        # Skip if already completed
        if experiment_manager.test_exists(test_def.test_id):
            print(f"⏭️  Skipping completed: {test_def.test_id}")
            continue
        
        scenario = scenarios_dict[test_def.scenario_id]
        constitution = constitutions_dict[test_def.constitution_id]
        model = models_dict[test_def.model_id]
        
        task = run_single_test(test_def, scenario, constitution, model, experiment_manager)
        tasks.append(task)
    
    # Run batch in parallel
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        successful = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False or isinstance(r, Exception))
        
        print(f"\nBatch {batch_num} complete: {successful} successful, {failed} failed")

        # Update manifest after each batch
        save_manifest(experiment_manager)

        return {"successful": successful, "failed": failed}
    else:
        print(f"Batch {batch_num}: All tests already completed")
        return {"successful": 0, "failed": 0}


def create_batches(tests: List[TestDefinition], batch_size: int = 6) -> List[List[TestDefinition]]:
    """
    Create batches of tests, distributing across models for rate limit management

    Uses round-robin distribution to ensure no batch has multiple tests for the same model.
    This prevents rate limit issues by spreading API calls across providers.

    Args:
        tests: All tests to batch
        batch_size: Target size for each batch (default: 6, reduced from 12 for safety)

    Returns:
        List of batches, each batch is a list of TestDefinition objects
    """
    # Group by model to ensure even distribution
    model_groups = {}
    for test in tests:
        if test.model_id not in model_groups:
            model_groups[test.model_id] = []
        model_groups[test.model_id].append(test)

    # Create round-robin batches
    batches = []
    current_batch = []

    # Get iterators for each model group (FIX: use model_tests not tests)
    model_iterators = {model_id: iter(model_tests) for model_id, model_tests in model_groups.items()}

    while model_iterators:
        # Try to add one test from each model to current batch
        added_to_batch = False
        for model_id in list(model_iterators.keys()):
            try:
                test = next(model_iterators[model_id])
                current_batch.append(test)
                added_to_batch = True

                if len(current_batch) >= batch_size:
                    batches.append(current_batch)
                    current_batch = []

            except StopIteration:
                del model_iterators[model_id]

        if not added_to_batch:
            break

    # Add remaining tests
    if current_batch:
        batches.append(current_batch)

    return batches


async def main():
    """
    Main experiment runner with full configurability
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Constitutional Reasoning Experiment Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full experiment with all defaults
  python -m src.runner

  # Filter scenarios and constitutions
  python -m src.runner --scenarios vaccine-mandate asylum-claim --constitutions pragmatic utilitarian

  # Filter Layer 2 models
  python -m src.runner --layer2-models gpt-4o claude-sonnet-4-5

  # Specify multiple Layer 3 evaluators
  python -m src.runner --layer3-evaluators claude-sonnet-4-5 claude-3-5-haiku-20241022

  # Smart resume (picks up incomplete tests)
  python -m src.runner --resume exp_20251023_105245

  # Force rerun specific layer with specific model(s)
  python -m src.runner --resume exp_20251023_105245 --layer 3 --models claude-3-5-haiku-20241022
  python -m src.runner --resume exp_20251023_105245 --layer 2 --models gemini-2-5-pro
        """
    )

    # Experiment control
    parser.add_argument('--new', action='store_true',
                       help='Force start a new experiment (ignores current pointer)')
    parser.add_argument('--resume', type=str, metavar='EXP_ID',
                       help='Resume a specific experiment by ID')

    # Data filtering (for new runs)
    parser.add_argument('--scenarios', type=str, nargs='+', metavar='ID',
                       help='Scenario IDs to run (default: all)')
    parser.add_argument('--constitutions', type=str, nargs='+', metavar='ID',
                       help='Constitution IDs to run (default: all)')
    parser.add_argument('--layer2-models', type=str, nargs='+', metavar='MODEL_ID',
                       help='Model IDs for Layer 2 reasoning (default: all)')
    parser.add_argument('--layer3-evaluators', type=str, nargs='+', metavar='MODEL_ID',
                       help='Model IDs for Layer 3 evaluation (default: primary evaluator)')

    # Single-layer mode (for resume with forced rerun)
    parser.add_argument('--layer', type=int, choices=[1, 2, 3],
                       help='Run only specific layer (requires --resume and --models)')
    parser.add_argument('--models', type=str, nargs='+', metavar='MODEL_ID',
                       help='Model IDs to use with --layer')

    args = parser.parse_args()

    print("Constitutional Reasoning Engine - Experiment Runner")
    print("=" * 70)

    # Validate argument combinations
    if args.layer and not args.resume:
        print("❌ Error: --layer requires --resume")
        sys.exit(1)

    if args.layer and not args.models:
        print("❌ Error: --layer requires --models")
        sys.exit(1)

    if args.models and not args.layer:
        print("❌ Error: --models requires --layer")
        sys.exit(1)

    # Load all available data
    all_scenarios = load_scenarios()
    all_constitutions = load_constitutions()
    models_data = load_models()
    all_models = models_data['layer2']  # Layer 2 models for experiment creation

    print(f"Available: {len(all_scenarios)} scenarios, {len(all_constitutions)} constitutions, {len(all_models)} layer2 models, {len(models_data['layer3'])} layer3 evaluators")

    # ============================================================================
    # Filter data based on arguments
    # ============================================================================

    # Filter scenarios
    if args.scenarios:
        scenarios = [s for s in all_scenarios if s.id in args.scenarios]
        if len(scenarios) != len(args.scenarios):
            found_ids = {s.id for s in scenarios}
            missing = set(args.scenarios) - found_ids
            print(f"❌ Error: Scenarios not found: {missing}")
            sys.exit(1)
    else:
        scenarios = all_scenarios

    # Filter constitutions
    if args.constitutions:
        constitutions = [c for c in all_constitutions if c.id in args.constitutions]
        if len(constitutions) != len(args.constitutions):
            found_ids = {c.id for c in constitutions}
            missing = set(args.constitutions) - found_ids
            print(f"❌ Error: Constitutions not found: {missing}")
            sys.exit(1)
    else:
        constitutions = all_constitutions

    # Filter Layer 2 models
    if args.layer2_models:
        layer2_models = [m for m in all_models if m['id'] in args.layer2_models]
        if len(layer2_models) != len(args.layer2_models):
            found_ids = {m['id'] for m in layer2_models}
            missing = set(args.layer2_models) - found_ids
            print(f"❌ Error: Layer 2 models not found: {missing}")
            sys.exit(1)
    else:
        layer2_models = all_models

    # Set Layer 3 evaluators
    if args.layer3_evaluators:
        layer3_evaluators = args.layer3_evaluators
        # Validate they exist in models and can do layer3
        valid_layer3_ids = {m['id'] for m in models_data['layer3']}
        invalid = [e for e in layer3_evaluators if e not in valid_layer3_ids]
        if invalid:
            print(f"❌ Error: Layer 3 evaluators not found or not capable: {invalid}")
            print(f"    Available Layer 3 evaluators: {', '.join(valid_layer3_ids)}")
            sys.exit(1)
    else:
        # Use default Layer 3 evaluator
        layer3_evaluators = [get_default_layer3_evaluator(models_data['all'])]

    print(f"\nConfiguration:")
    print(f"  Scenarios: {len(scenarios)} ({', '.join(s.id for s in scenarios[:3])}{'...' if len(scenarios) > 3 else ''})")
    print(f"  Constitutions: {len(constitutions)} ({', '.join(c.id for c in constitutions[:3])}{'...' if len(constitutions) > 3 else ''})")
    print(f"  Layer 2 models: {len(layer2_models)} ({', '.join(m['id'] for m in layer2_models[:3])}{'...' if len(layer2_models) > 3 else ''})")
    print(f"  Layer 3 evaluators: {', '.join(layer3_evaluators)}")
    if args.layer:
        print(f"  Mode: Single-layer ({args.layer}) with models: {', '.join(args.models)}")
    print()

    # Determine which experiment to run
    experiment_id = None
    force_new = args.new

    if args.resume:
        # Explicit resume of specific experiment
        experiment_id = args.resume
        print(f"📂 Resuming experiment: {experiment_id}")
        experiment_manager = ExperimentManager(experiment_id=experiment_id)

        # Verify experiment exists
        if not experiment_manager.experiment_state:
            print(f"❌ Error: Experiment {experiment_id} not found")
            sys.exit(1)

    elif force_new:
        # Force new experiment
        print("🆕 Starting new experiment (--new flag)")
        experiment_manager = ExperimentManager()
        experiment_id = experiment_manager.create_experiment(scenarios, constitutions, layer2_models)

    else:
        # Smart mode: check for incomplete experiment
        experiment_manager = ExperimentManager()

        if experiment_manager.experiment_id and experiment_manager.experiment_state:
            # Found existing experiment via pointer
            current_status = experiment_manager.experiment_state.status
            pending_count = experiment_manager.experiment_state.pending_count

            if current_status == "completed":
                # Old experiment is complete, start new one
                print(f"✅ Previous experiment {experiment_manager.experiment_id} is complete")
                print("🆕 Starting new experiment")
                experiment_id = experiment_manager.create_experiment(scenarios, constitutions, layer2_models)
            elif pending_count > 0:
                # Resume incomplete experiment
                print(f"📂 Resuming incomplete experiment: {experiment_manager.experiment_id}")
                print(f"   Status: {current_status}, Pending: {pending_count} tests")
                experiment_id = experiment_manager.experiment_id
            else:
                # Edge case: in_progress but no pending (all failed?)
                print(f"⚠️  Experiment {experiment_manager.experiment_id} has no pending tests")
                print("🆕 Starting new experiment")
                experiment_id = experiment_manager.create_experiment(scenarios, constitutions, layer2_models)
        else:
            # No current experiment, start new one
            print("🆕 No active experiment found, starting new one")
            experiment_id = experiment_manager.create_experiment(scenarios, constitutions, layer2_models)
    
    # Get pending and retryable tests
    pending_tests = experiment_manager.get_pending_tests()
    failed_tests = experiment_manager.get_failed_tests(max_retries=3)
    all_tests = pending_tests + failed_tests
    
    if not all_tests:
        print("🎉 All tests completed!")
        progress = experiment_manager.get_progress_summary()
        print(f"Final status: {progress}")
        return
    
    print(f"\nTests to run: {len(pending_tests)} pending + {len(failed_tests)} retries = {len(all_tests)} total")
    
    # Create lookup dictionaries
    scenarios_dict = {s.id: s for s in scenarios}
    constitutions_dict = {c.id: c for c in constitutions}
    models_dict = {m['id']: m for m in layer2_models}
    
    # Create batches
    batches = create_batches(all_tests, batch_size=12)
    print(f"Created {len(batches)} batches (12 tests per batch, 20s inter-batch delay)")
    
    # Show initial progress
    progress = experiment_manager.get_progress_summary()
    print(f"\nStarting progress: {progress['progress']}")
    
    # Run batches
    total_successful = 0
    total_failed = 0
    
    for i, batch in enumerate(batches, 1):
        try:
            # Run batch
            batch_results = await run_batch(
                batch, scenarios_dict, constitutions_dict, models_dict, 
                experiment_manager, i, len(batches)
            )
            
            total_successful += batch_results["successful"]
            total_failed += batch_results["failed"]
            
            # Show progress
            progress = experiment_manager.get_progress_summary()
            print(f"Progress: {progress['progress']}")
            
            # Rate limiting delay between batches
            if i < len(batches):
                print(f"⏳ Waiting 20 seconds before next batch...")
                await asyncio.sleep(20)
                
        except KeyboardInterrupt:
            print(f"\n⏸️  Experiment paused. Resume by running this script again.")
            break
        except Exception as e:
            print(f"\n❌ Batch {i} failed with error: {e}")
            print(traceback.format_exc())
            continue
    
    # Final summary
    print(f"\n{'='*70}")
    print("EXPERIMENT SUMMARY")
    print(f"{'='*70}")

    final_progress = experiment_manager.get_progress_summary()
    print(f"Experiment ID: {final_progress['experiment_id']}")
    print(f"Status: {final_progress['status']}")
    print(f"Progress: {final_progress['progress']}")
    print(f"Session results: {total_successful} successful, {total_failed} failed")

    if final_progress['progress']['pending'] == 0:
        # All tests complete - finalize experiment
        experiment_manager.finalize_experiment(clear_pointer=True)
        print("\n🎉 Experiment completed successfully!")
        print("   State preserved in experiment directory for debugging")
        print("   Run 'python -m src.runner' to start a new experiment")
    else:
        print(f"\n⏸️  Experiment paused with {final_progress['progress']['pending']} tests remaining.")
        print("Run this script again to resume.")


if __name__ == "__main__":
    asyncio.run(main())