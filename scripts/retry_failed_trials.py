#!/usr/bin/env python3
"""
Retry Failed Trials

This script identifies failed trials in an experiment and retries them through
the appropriate layers of the pipeline. It handles two failure types:

1. **Layer 2 failures**: Retry Layer 2 reasoning → then run Layer 3 evaluation
2. **Layer 3 failures**: Layer 2 exists and succeeded, retry Layer 3 only

Usage:
    poetry run python scripts/retry_failed_trials.py \
        --experiment exp_20251028_134615

Features:
    - Analyzes failure point (Layer 2 or Layer 3)
    - Retries only what failed (efficient)
    - Preserves successful results
    - Resumable (skips already-retried trials)
    - Rate limit friendly (batched with delays)
    - Auto-cleanup: Deletes *.error.json files after successful retries
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Add project root to Python path (fixes ModuleNotFoundError)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.experiment_state import ExperimentManager
from src.core.scenarios import load_scenarios
from src.core.constitutions import load_constitutions
from src.core.models import load_models, get_model_response
from src.core.prompts import (
    build_constitutional_reasoning_prompt,
    build_integrity_evaluation_prompt_likert,
    build_integrity_evaluation_prompt_binary,
    build_integrity_evaluation_prompt_ternary
)
from src.core.graceful_parser import GracefulJsonParser, ParseStatus
from src.core.truncation_detector import TruncationDetector
from src.core.layer3_evaluator import evaluate_layer3


def cleanup_error_file(trial_id: str, experiment_dir: Path) -> bool:
    """
    Delete the error file for a trial after successful retry.

    Returns:
        True if file was deleted or didn't exist, False on error
    """
    error_file = experiment_dir / "data" / "layer2" / f"{trial_id}.error.json"

    if error_file.exists():
        try:
            error_file.unlink()
            return True
        except Exception as e:
            print(f"    ⚠️ Could not delete error file: {e}")
            return False

    return True  # File didn't exist, which is fine


def analyze_failure(
    trial_id: str,
    experiment_dir: Path
) -> Tuple[str, Dict[str, Any]]:
    """
    Analyze where a trial failed.

    Returns:
        ("layer2_failed", trial_data) - Layer 2 failed, needs full retry
        ("layer3_failed", trial_data) - Layer 2 succeeded, Layer 3 failed
        ("unknown", trial_data) - Cannot determine failure point
    """
    layer2_dir = experiment_dir / "data" / "layer2"
    layer3_dir = experiment_dir / "data" / "layer3"

    # Check Layer 2
    layer2_file = layer2_dir / f"{trial_id}.json"
    if not layer2_file.exists():
        return ("layer2_failed", {})

    with open(layer2_file) as f:
        layer2_data = json.load(f)

    # Layer 2 completed successfully
    if layer2_data.get("status") == "completed":
        # Check Layer 3
        layer3_file = layer3_dir / f"{trial_id}.json"
        if not layer3_file.exists():
            return ("layer3_failed", layer2_data)

    return ("layer2_failed", layer2_data)


async def retry_layer2_trial(
    trial_id: str,
    trial_registry_entry: Dict[str, Any],
    scenario_data: Any,
    constitution_data: Any,
    model_data: Dict[str, Any],
    experiment_manager: ExperimentManager,
    parser: GracefulJsonParser,
    experiment_dir: Path
) -> Tuple[bool, Dict[str, Any]]:
    """
    Retry Layer 2 reasoning for a failed trial.

    Returns:
        (success: bool, response_data: dict)
    """
    print(f"  Retrying Layer 2 for {trial_id}...")

    try:
        # Build facts (from scenario since SKIP_LAYER_1 is True)
        facts = {
            "establishedFacts": scenario_data.established_facts,
            "ambiguousElements": scenario_data.ambiguous_elements,
            "keyQuestions": []
        }

        # Build prompt
        reasoning_prompt = build_constitutional_reasoning_prompt(
            scenario=scenario_data,
            constitution=constitution_data,
            established_facts=facts['establishedFacts']
        )

        # Audit callback
        def layer2_audit_callback(request_params, response, error, http_status, retry_attempt):
            experiment_manager.save_api_audit_log(
                trial_id=trial_id,
                layer=2,
                model_id=model_data['id'],
                request_params=request_params,
                response=response,
                error=error,
                http_status=http_status,
                retry_attempt=retry_attempt
            )

        # Retry with truncation detection
        truncation_detector = TruncationDetector()
        max_tokens = 8000
        max_retries = 3

        for attempt in range(max_retries):
            constitutional_response = await get_model_response(
                model_id=model_data['id'],
                prompt=reasoning_prompt,
                system_prompt=constitution_data.system_prompt,
                temperature=0.7,
                max_tokens=max_tokens,
                use_response_format=True,
                audit_callback=layer2_audit_callback
            )

            response_data, status = parser.parse_constitutional_response(
                constitutional_response,
                f"{trial_id}_constitutional"
            )

            is_truncated, trunc_reason = truncation_detector.is_truncated(
                constitutional_response,
                parse_success=(status == ParseStatus.SUCCESS)
            )

            if not is_truncated or status == ParseStatus.SUCCESS:
                break

            if attempt < max_retries - 1:
                max_tokens = truncation_detector.get_next_token_limit(max_tokens)
                print(f"    ⚠️ Truncated, retrying with {max_tokens} tokens")

        # Save Layer 2 result
        layer2_data = {
            "trial_id": trial_id,
            "layer": 2,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "scenario_id": scenario_data.id,
            "model": model_data['id'],
            "constitution": constitution_data.id,
            "prompt_sent": reasoning_prompt,
            "response_raw": constitutional_response,
            "response_parsed": response_data,
            "parsing": {
                "success": status == ParseStatus.SUCCESS,
                "method": "standard_json" if status == ParseStatus.SUCCESS else "manual_review",
                "fallback_attempts": 0,
                "error": None if status == ParseStatus.SUCCESS else status.value,
                "manual_review_path": None
            },
            "tokens_used": max_tokens,
            "latency_ms": 0,  # Not tracked in retry
            "truncation_detected": is_truncated
        }

        experiment_manager.save_layer_result(trial_id, 2, layer2_data)
        experiment_manager.update_layer_status(trial_id, 2, "completed", model_data['id'])

        # Clean up error file after successful retry
        cleanup_error_file(trial_id, experiment_dir)

        print(f"    ✓ Layer 2 completed")
        return (True, response_data)

    except Exception as e:
        error_msg = f"Layer 2 retry failed: {str(e)}"
        print(f"    ✗ {error_msg}")

        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat(),
            "layer": 2,
            "model_id": model_data['id']
        }

        experiment_manager.save_error_response(trial_id, 2, error_details)
        experiment_manager.update_layer_status(trial_id, 2, "failed", model_data['id'], error_msg)

        return (False, {})


async def retry_layer3_trial(
    trial_id: str,
    layer2_data: Dict[str, Any],
    scenario_data: Any,
    layer3_evaluators: List[str],
    evaluation_strategy: str,
    experiment_manager: ExperimentManager,
    parser: GracefulJsonParser,
    experiment_dir: Path
) -> bool:
    """
    Retry Layer 3 evaluation for a trial where Layer 2 succeeded.

    Returns:
        success: bool
    """
    print(f"  Retrying Layer 3 for {trial_id}...")

    try:
        # Extract facts and response from Layer 2
        facts = {
            "establishedFacts": scenario_data.established_facts,
            "ambiguousElements": scenario_data.ambiguous_elements
        }
        response_data = layer2_data.get("response_parsed", {})

        # Build evaluation prompt based on strategy
        if evaluation_strategy == 'binary':
            eval_prompt = build_integrity_evaluation_prompt_binary(
                established_facts=facts['establishedFacts'],
                ambiguous_elements=facts['ambiguousElements'],
                constitutional_response=response_data
            )
        elif evaluation_strategy == 'ternary':
            eval_prompt = build_integrity_evaluation_prompt_ternary(
                established_facts=facts['establishedFacts'],
                ambiguous_elements=facts['ambiguousElements'],
                constitutional_response=response_data
            )
        else:  # likert
            eval_prompt = build_integrity_evaluation_prompt_likert(
                established_facts=facts['establishedFacts'],
                ambiguous_elements=facts['ambiguousElements'],
                constitutional_response=response_data
            )

        # Run all evaluators
        layer3_file_path = experiment_manager.layer3_dir / f"{trial_id}.json"
        primary_success = False

        for idx, evaluator_id in enumerate(layer3_evaluators):
            is_primary = (idx == 0)

            eval_result = await evaluate_layer3(
                trial_id=trial_id,
                eval_prompt=eval_prompt,
                evaluator_id=evaluator_id,
                is_primary=is_primary,
                experiment_manager=experiment_manager,
                parser=parser,
                save_result=False
            )

            if eval_result["success"]:
                # Merge with existing Layer 3 file
                if layer3_file_path.exists():
                    with open(layer3_file_path, 'r') as f:
                        merged_layer3 = json.load(f)
                else:
                    merged_layer3 = {
                        "trial_id": trial_id,
                        "layer": 3,
                        "scenario_id": layer2_data.get("scenario_id"),
                        "model": layer2_data.get("model"),
                        "constitution": layer2_data.get("constitution"),
                        "evaluations": {}
                    }

                merged_layer3["evaluations"][evaluator_id] = {
                    "timestamp": eval_result["layer3_data"]["timestamp"],
                    "status": "completed",
                    "evaluation_strategy": evaluation_strategy,
                    "prompt_sent": eval_result["layer3_data"]["prompt_sent"],
                    "response_raw": eval_result["layer3_data"]["response_raw"],
                    "response_parsed": eval_result["integrity_data"],
                    "parsing": eval_result["layer3_data"]["parsing"],
                    "tokens_used": eval_result["max_tokens_used"],
                    "latency_ms": eval_result["elapsed_ms"]
                }

                experiment_manager.save_layer_result(trial_id, 3, merged_layer3)

                if is_primary:
                    primary_success = True
                    experiment_manager.update_layer_status(trial_id, 3, "completed", evaluator_id)

                    # Clean up error file after successful retry
                    cleanup_error_file(trial_id, experiment_dir)

                    print(f"    ✓ Layer 3 completed")
            else:
                print(f"    ✗ Evaluator {evaluator_id} failed: {eval_result['error']}")
                if is_primary:
                    return False

            await asyncio.sleep(2)  # Rate limit delay

        return primary_success

    except Exception as e:
        error_msg = f"Layer 3 retry failed: {str(e)}"
        print(f"    ✗ {error_msg}")
        return False


async def retry_failed_trials(
    experiment_id: str,
    batch_size: int = 6,
    batch_delay: int = 20
) -> Dict[str, Any]:
    """
    Retry all failed trials in an experiment.

    Args:
        experiment_id: Experiment ID to retry
        batch_size: Trials per batch (default: 6)
        batch_delay: Seconds between batches (default: 20)

    Returns:
        {
            "total_failed": int,
            "layer2_retries": int,
            "layer3_retries": int,
            "successful_retries": int,
            "still_failed": int
        }
    """
    # Load experiment
    experiment_manager = ExperimentManager(experiment_id=experiment_id)
    if not experiment_manager.experiment_state:
        print(f"❌ Experiment {experiment_id} not found")
        sys.exit(1)

    experiment_dir = Path("results/experiments") / experiment_id

    # Load trial registry
    registry_file = experiment_dir / "state" / "trial_registry.json"
    with open(registry_file) as f:
        registry = json.load(f)

    # Find failed trials
    failed_trials = [
        (trial_id, trial_data)
        for trial_id, trial_data in registry["trials"].items()
        if trial_data.get("status") == "failed"
    ]

    print(f"\n{'='*80}")
    print(f"Retry Failed Trials: {experiment_id}")
    print(f"Total failed: {len(failed_trials)}")
    print(f"{'='*80}\n")

    if not failed_trials:
        print("No failed trials to retry.")
        return {
            "total_failed": 0,
            "layer2_retries": 0,
            "layer3_retries": 0,
            "successful_retries": 0,
            "still_failed": 0
        }

    # Load experiment configuration
    scenarios = {s.id: s for s in load_scenarios()}
    constitutions = {c.id: c for c in load_constitutions()}
    models_data = load_models()
    models = {m['id']: m for m in models_data['all']}

    # Get Layer 3 evaluators from experiment state
    exp_state_file = experiment_dir / "state" / "experiment_state.json"
    with open(exp_state_file) as f:
        exp_state = json.load(f)
    layer3_evaluators = exp_state.get("layer3_evaluators", ["claude-sonnet-4-5"])
    evaluation_strategy = exp_state.get("evaluation_strategy", "likert")

    # Initialize parser
    parser = GracefulJsonParser(experiment_id=experiment_id)

    # Analyze failures
    layer2_failures = []
    layer3_failures = []

    for trial_id, trial_data in failed_trials:
        failure_type, failure_data = analyze_failure(trial_id, experiment_dir)

        if failure_type == "layer2_failed":
            layer2_failures.append((trial_id, trial_data, failure_data))
        elif failure_type == "layer3_failed":
            layer3_failures.append((trial_id, trial_data, failure_data))

    print(f"Analysis:")
    print(f"  Layer 2 failures: {len(layer2_failures)}")
    print(f"  Layer 3 failures: {len(layer3_failures)}")
    print()

    # Retry in batches
    successful = 0
    still_failed = 0
    all_retries = layer2_failures + layer3_failures
    total_batches = (len(all_retries) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        batch_start = batch_idx * batch_size
        batch_end = min((batch_idx + 1) * batch_size, len(all_retries))
        batch = all_retries[batch_start:batch_end]

        print(f"Batch {batch_idx + 1}/{total_batches} ({len(batch)} trials)")

        for trial_id, trial_data, failure_data in batch:
            # Determine if Layer 2 or Layer 3 retry
            is_layer2_retry = (trial_id, trial_data, failure_data) in layer2_failures

            # Get trial configuration
            scenario_id = trial_data.get("scenario_id")
            constitution_id = trial_data.get("constitution")
            model_id = trial_data.get("model")

            scenario_data = scenarios.get(scenario_id)
            constitution_data = constitutions.get(constitution_id)
            model_data = models.get(model_id)

            if not all([scenario_data, constitution_data, model_data]):
                print(f"  ✗ {trial_id}: Missing configuration")
                still_failed += 1
                continue

            try:
                if is_layer2_retry:
                    # Retry Layer 2 then Layer 3
                    l2_success, response_data = await retry_layer2_trial(
                        trial_id,
                        trial_data,
                        scenario_data,
                        constitution_data,
                        model_data,
                        experiment_manager,
                        parser,
                        experiment_dir
                    )

                    if l2_success:
                        # Now run Layer 3
                        layer2_file = experiment_dir / "data" / "layer2" / f"{trial_id}.json"
                        with open(layer2_file) as f:
                            layer2_data = json.load(f)

                        l3_success = await retry_layer3_trial(
                            trial_id,
                            layer2_data,
                            scenario_data,
                            layer3_evaluators,
                            evaluation_strategy,
                            experiment_manager,
                            parser,
                            experiment_dir
                        )

                        if l3_success:
                            experiment_manager.mark_test_completed(trial_id, {})
                            successful += 1
                        else:
                            still_failed += 1
                    else:
                        still_failed += 1

                else:
                    # Layer 3 retry only
                    l3_success = await retry_layer3_trial(
                        trial_id,
                        failure_data,
                        scenario_data,
                        layer3_evaluators,
                        evaluation_strategy,
                        experiment_manager,
                        parser,
                        experiment_dir
                    )

                    if l3_success:
                        experiment_manager.mark_test_completed(trial_id, {})
                        successful += 1
                    else:
                        still_failed += 1

            except Exception as e:
                print(f"  ✗ {trial_id}: {str(e)}")
                still_failed += 1

        # Batch delay
        if batch_idx < total_batches - 1:
            print(f"\n⏳ Waiting {batch_delay}s before next batch...\n")
            await asyncio.sleep(batch_delay)

    results = {
        "total_failed": len(failed_trials),
        "layer2_retries": len(layer2_failures),
        "layer3_retries": len(layer3_failures),
        "successful_retries": successful,
        "still_failed": still_failed
    }

    print(f"\n{'='*80}")
    print(f"Retry Complete")
    print(f"{'='*80}")
    print(f"Total failed: {results['total_failed']}")
    print(f"Layer 2 retries: {results['layer2_retries']}")
    print(f"Layer 3 retries: {results['layer3_retries']}")
    print(f"Successful: {results['successful_retries']}")
    print(f"Still failed: {results['still_failed']}")
    print()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Retry failed trials in an experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--experiment', '-e',
        type=str,
        required=True,
        help='Experiment ID to retry (e.g., exp_20251028_134615)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=6,
        help='Trials per batch (default: 6)'
    )

    parser.add_argument(
        '--batch-delay',
        type=int,
        default=20,
        help='Seconds between batches (default: 20)'
    )

    parser.add_argument(
        '--cleanup-orphaned',
        action='store_true',
        help='Clean up orphaned *.error.json files from previously successful retries'
    )

    args = parser.parse_args()

    try:
        # Handle orphaned error file cleanup
        if args.cleanup_orphaned:
            experiment_dir = Path("results/experiments") / args.experiment
            registry_file = experiment_dir / "state" / "trial_registry.json"
            layer2_dir = experiment_dir / "data" / "layer2"

            if not registry_file.exists():
                print(f"❌ Experiment {args.experiment} not found")
                sys.exit(1)

            with open(registry_file) as f:
                registry = json.load(f)
                trials = registry.get('trials', registry)

            error_files = list(layer2_dir.glob("*.error.json"))
            orphaned = []

            for error_file in error_files:
                trial_id = error_file.stem.replace('.error', '')
                status = trials.get(trial_id, {}).get('status', 'NOT_IN_REGISTRY')

                if status == 'completed':
                    orphaned.append((trial_id, error_file))

            if orphaned:
                print(f"\n{'='*80}")
                print(f"Cleaning up orphaned error files: {args.experiment}")
                print(f"{'='*80}\n")
                print(f"Found {len(orphaned)} orphaned *.error.json files\n")

                for trial_id, error_file in orphaned:
                    try:
                        error_file.unlink()
                        print(f"  ✓ Deleted {error_file.name}")
                    except Exception as e:
                        print(f"  ✗ Failed to delete {error_file.name}: {e}")

                print(f"\n✅ Cleanup complete\n")
            else:
                print(f"\n✅ No orphaned error files found\n")

            sys.exit(0)

        # Normal retry flow
        results = asyncio.run(retry_failed_trials(
            experiment_id=args.experiment,
            batch_size=args.batch_size,
            batch_delay=args.batch_delay
        ))

        sys.exit(0 if results["still_failed"] == 0 else 1)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
