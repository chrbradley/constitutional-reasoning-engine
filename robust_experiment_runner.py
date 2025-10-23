"""
Robust experiment runner with state management, batching, and resumption
"""
import asyncio
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add experiments/src to path
sys.path.append('experiments/src')

from models import get_model_response, MODELS
from scenarios import load_scenarios
from constitutions import CONSTITUTIONS
from prompts import (
    build_fact_establishment_prompt,
    build_constitutional_reasoning_prompt,
    build_integrity_evaluation_prompt
)
from experiment_state import ExperimentManager, TestDefinition, TestStatus
from graceful_parser import GracefulJsonParser, ParseStatus
from truncation_detector import TruncationDetector


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
        
        # Layer 1: Establish facts (using Claude for consistency)
        fact_prompt = build_fact_establishment_prompt(scenario_data)
        fact_response = await get_model_response(
            model_id="claude-sonnet-4-5",
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
        
        # Layer 2: Constitutional reasoning (with truncation detection and retry)
        reasoning_prompt = build_constitutional_reasoning_prompt(
            scenario=scenario_data,
            constitution=constitution_data,
            established_facts=facts['establishedFacts'],
            ambiguous_elements=facts['ambiguousElements']
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
        
        # Layer 3: Integrity evaluation (using Claude for consistency)
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
        
        return {"successful": successful, "failed": failed}
    else:
        print(f"Batch {batch_num}: All tests already completed")
        return {"successful": 0, "failed": 0}


def create_batches(tests: List[TestDefinition], batch_size: int = 12) -> List[List[TestDefinition]]:
    """
    Create batches of tests, distributing across models for rate limit management
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
    
    # Get iterators for each model group
    model_iterators = {model_id: iter(tests) for model_id, tests in model_groups.items()}
    
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
    Main experiment runner with state management
    """
    print("Constitutional Reasoning Engine - Robust Experiment Runner")
    print("=" * 70)
    
    # Initialize experiment manager
    experiment_manager = ExperimentManager()
    
    # Load data
    scenarios = load_scenarios()
    constitutions = CONSTITUTIONS
    models = MODELS
    
    print(f"Loaded: {len(scenarios)} scenarios, {len(constitutions)} constitutions, {len(models)} models")
    
    # Create or resume experiment
    experiment_id = experiment_manager.create_experiment(scenarios, constitutions, models)
    
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
    models_dict = {m['id']: m for m in models}
    
    # Create batches
    batches = create_batches(all_tests, batch_size=12)
    print(f"Created {len(batches)} batches (12 tests per batch)")
    
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
                print(f"⏳ Waiting 30 seconds before next batch...")
                await asyncio.sleep(30)
                
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
        print("\n🎉 Experiment completed successfully!")
    else:
        print(f"\n⏸️  Experiment paused with {final_progress['progress']['pending']} tests remaining.")
        print("Run this script again to resume.")


if __name__ == "__main__":
    asyncio.run(main())