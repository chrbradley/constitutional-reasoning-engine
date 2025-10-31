"""
Backfill missing evaluators in Layer 3 evaluation directories.

This script identifies trials with incomplete evaluations (< expected number of evaluators)
and re-evaluates ONLY the missing evaluators, avoiding redundant API calls.

Usage:
    # Preview what will be backfilled
    python scripts/backfill_missing_evaluators.py \
        --experiment exp_20251028_134615 \
        --evaluation-strategy binary \
        --target-evaluators claude-sonnet-4-5 gpt-4o gemini-2-5-pro grok-3 deepseek-chat \
        --dry-run

    # Execute backfill
    python scripts/backfill_missing_evaluators.py \
        --experiment exp_20251028_134615 \
        --evaluation-strategy binary \
        --target-evaluators claude-sonnet-4-5 gpt-4o gemini-2-5-pro grok-3 deepseek-chat

    # Validate completion
    python scripts/backfill_missing_evaluators.py \
        --experiment exp_20251028_134615 \
        --evaluation-strategy binary \
        --target-evaluators claude-sonnet-4-5 gpt-4o gemini-2-5-pro grok-3 deepseek-chat \
        --validate-only
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any
import asyncio
from datetime import datetime

# Add project root to Python path (same as reeval_with_rubric.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.experiment_state import ExperimentManager
from src.core.models import get_model_response
from src.core.truncation_detector import TruncationDetector
from src.core.graceful_parser import GracefulJsonParser, ParseStatus
from src.core.scenarios import load_scenarios
from src.core.prompts import (
    build_integrity_evaluation_prompt_likert,
    build_integrity_evaluation_prompt_binary,
    build_integrity_evaluation_prompt_ternary
)


def get_scenario_facts(scenario_id: str) -> Dict[str, List[str]]:
    """Get established facts and ambiguous elements for a scenario."""
    scenarios = load_scenarios()

    for scenario in scenarios:
        if scenario.id == scenario_id:
            return {
                'establishedFacts': scenario.established_facts,
                'ambiguousElements': scenario.ambiguous_elements
            }

    raise ValueError(f"Scenario not found: {scenario_id}")


def scan_incomplete_trials(
    layer3_dir: Path,
    target_evaluators: List[str]
) -> List[Tuple[str, Set[str]]]:
    """
    Scan Layer 3 directory for trials with missing evaluators.

    Args:
        layer3_dir: Path to layer3_* directory
        target_evaluators: List of expected evaluator IDs

    Returns:
        List of (trial_id, missing_evaluator_ids) tuples
    """
    incomplete_trials = []
    target_set = set(target_evaluators)

    for trial_file in sorted(layer3_dir.glob("trial_*.json")):
        with open(trial_file, 'r') as f:
            data = json.load(f)

        existing_evaluators = set(data.get('evaluations', {}).keys())
        missing_evaluators = target_set - existing_evaluators

        if missing_evaluators:
            incomplete_trials.append((trial_file.stem, missing_evaluators))

    return incomplete_trials


async def evaluate_single_evaluator(
    evaluator_id: str,
    scenario_id: str,
    layer2_data: Dict[str, Any],
    strategy: str,
    parser: GracefulJsonParser,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Evaluate a single evaluator with exponential backoff retry.

    Args:
        evaluator_id: ID of the evaluator model
        scenario_id: Scenario ID for fetching facts
        layer2_data: Layer 2 reasoning data
        strategy: Evaluation strategy (likert, binary, ternary)
        parser: GracefulJsonParser instance
        max_retries: Maximum retry attempts for rate limits

    Returns:
        Evaluation data dict ready for merging
    """
    # Select prompt builder based on strategy
    if strategy == "likert":
        prompt_builder = build_integrity_evaluation_prompt_likert
    elif strategy == "binary":
        prompt_builder = build_integrity_evaluation_prompt_binary
    elif strategy == "ternary":
        prompt_builder = build_integrity_evaluation_prompt_ternary
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # Get scenario facts
    facts = get_scenario_facts(scenario_id)

    # Build prompt
    eval_prompt = prompt_builder(
        established_facts=facts['establishedFacts'],
        ambiguous_elements=facts['ambiguousElements'],
        constitutional_response=layer2_data
    )

    # Truncation handling
    truncation_detector = TruncationDetector()
    max_tokens = 4000
    max_truncation_retries = 3

    # Retry logic with exponential backoff for rate limits
    rate_limit_delays = [3, 10, 30]  # seconds

    for rate_attempt in range(max_retries):
        try:
            # Special handling for grok-3 (add baseline delay)
            if evaluator_id == "grok-3":
                await asyncio.sleep(2)  # Gentle rate limiting

            # Inner loop for truncation retries
            for trunc_attempt in range(max_truncation_retries):
                integrity_response = await get_model_response(
                    model_id=evaluator_id,
                    prompt=eval_prompt,
                    temperature=0.3,
                    max_tokens=max_tokens
                )

                # Parse response
                integrity_data, status = parser.parse_integrity_response(
                    integrity_response,
                    f"backfill_{evaluator_id}"
                )

                # Check truncation
                is_truncated, trunc_reason = truncation_detector.is_truncated(
                    integrity_response,
                    parse_success=(status == ParseStatus.SUCCESS)
                )

                if not is_truncated or status == ParseStatus.SUCCESS:
                    break

                if trunc_attempt < max_truncation_retries - 1:
                    max_tokens = truncation_detector.get_next_token_limit(max_tokens)

            # Calculate overall score
            if status == ParseStatus.MANUAL_REVIEW:
                overall_score = -1
            else:
                # Try new 2D format first
                if 'epistemicIntegrity' in integrity_data and 'valueTransparency' in integrity_data:
                    overall_score = (
                        integrity_data['epistemicIntegrity']['score'] +
                        integrity_data['valueTransparency']['score']
                    ) / 2
                # Fall back to old 3D format
                elif 'factualAdherence' in integrity_data and 'valueTransparency' in integrity_data and 'logicalCoherence' in integrity_data:
                    overall_score = (
                        integrity_data['factualAdherence']['score'] +
                        integrity_data['valueTransparency']['score'] +
                        integrity_data['logicalCoherence']['score']
                    ) / 3
                else:
                    overall_score = -1
                integrity_data['overallScore'] = round(overall_score)

            # Return evaluation dict ready for merging
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'completed',
                'response_raw': integrity_response,
                'response_parsed': integrity_data,
                'parsing': {
                    'success': status == ParseStatus.SUCCESS,
                    'method': 'standard_json' if status == ParseStatus.SUCCESS else 'manual_review',
                    'error': None if status == ParseStatus.SUCCESS else status.value
                },
                'tokens_used': max_tokens
            }

        except Exception as e:
            error_msg = str(e)

            # Check for rate limiting
            is_rate_limit = (
                "429" in error_msg or
                "rate limit" in error_msg.lower() or
                "too many requests" in error_msg.lower()
            )

            if is_rate_limit and rate_attempt < max_retries - 1:
                delay = rate_limit_delays[rate_attempt]
                print(f"      Rate limit detected, waiting {delay}s before retry...")
                await asyncio.sleep(delay)
                continue
            else:
                # Not rate limit or exhausted retries
                raise


def merge_evaluation_into_trial(
    trial_path: Path,
    evaluator_id: str,
    evaluation_data: Dict[str, Any]
) -> None:
    """
    Merge a new evaluator evaluation into existing trial file.

    Args:
        trial_path: Path to trial JSON file
        evaluator_id: ID of the evaluator
        evaluation_data: Evaluation data to add
    """
    # Load existing trial data
    with open(trial_path, 'r') as f:
        trial_data = json.load(f)

    # Add new evaluation
    if 'evaluations' not in trial_data:
        trial_data['evaluations'] = {}

    trial_data['evaluations'][evaluator_id] = evaluation_data

    # Atomic write (write to .tmp, then rename)
    tmp_path = trial_path.with_suffix('.tmp')
    with open(tmp_path, 'w') as f:
        json.dump(trial_data, f, indent=2)

    # Atomic rename
    tmp_path.rename(trial_path)


async def backfill_trial(
    trial_id: str,
    missing_evaluators: Set[str],
    layer2_dir: Path,
    layer3_dir: Path,
    strategy: str,
    parser: GracefulJsonParser,
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Backfill missing evaluators for a single trial.

    Args:
        trial_id: Trial ID (e.g., "trial_001")
        missing_evaluators: Set of missing evaluator IDs
        layer2_dir: Path to layer2 directory
        layer3_dir: Path to layer3_* directory
        strategy: Evaluation strategy
        parser: GracefulJsonParser instance
        dry_run: If True, don't make API calls

    Returns:
        (successful_count, failed_count) tuple
    """
    # Load Layer 2 data
    layer2_file = layer2_dir / f"{trial_id}.json"
    if not layer2_file.exists():
        print(f"      ❌ Layer 2 file not found: {layer2_file}")
        return (0, len(missing_evaluators))

    with open(layer2_file, 'r') as f:
        layer2_full_data = json.load(f)

    # Extract scenario_id and response
    scenario_id = layer2_full_data.get('scenario_id', '')
    layer2_response = layer2_full_data.get('response_parsed', {})

    successful = 0
    failed = 0

    for evaluator_id in sorted(missing_evaluators):
        if dry_run:
            print(f"      [DRY-RUN] Would evaluate {evaluator_id}")
            successful += 1
            continue

        try:
            print(f"      Evaluating {evaluator_id}...", end=" ", flush=True)

            # Evaluate with retry logic
            evaluation = await evaluate_single_evaluator(
                evaluator_id=evaluator_id,
                scenario_id=scenario_id,
                layer2_data=layer2_response,
                strategy=strategy,
                parser=parser,
                max_retries=3
            )

            # Merge into existing trial file
            trial_path = layer3_dir / f"{trial_id}.json"
            merge_evaluation_into_trial(trial_path, evaluator_id, evaluation)

            print("✓")
            successful += 1

        except Exception as e:
            print(f"✗ ({str(e)[:50]})")
            failed += 1

    return (successful, failed)


async def backfill_experiment(
    experiment_id: str,
    strategy: str,
    target_evaluators: List[str],
    dry_run: bool = False
) -> None:
    """
    Backfill missing evaluations for an experiment.

    Args:
        experiment_id: Experiment ID
        strategy: Evaluation strategy (likert, binary, ternary)
        target_evaluators: List of expected evaluator IDs
        dry_run: If True, preview without making API calls
    """
    # Load experiment
    exp_mgr = ExperimentManager(experiment_id=experiment_id)

    # Construct experiment directory from base_dir and experiment_id
    exp_dir = exp_mgr.base_dir / "experiments" / exp_mgr.experiment_id

    # Determine layer3 directory based on strategy
    if strategy == "likert":
        layer3_dir = exp_dir / "data" / "layer3"
    else:
        layer3_dir = exp_dir / "data" / f"layer3_{strategy}"

    layer2_dir = exp_dir / "data" / "layer2"

    if not layer3_dir.exists():
        print(f"❌ Layer 3 directory not found: {layer3_dir}")
        return

    if not layer2_dir.exists():
        print(f"❌ Layer 2 directory not found: {layer2_dir}")
        return

    # Scan for incomplete trials
    print(f"\n🔍 Scanning for incomplete trials in {layer3_dir.name}/...")
    incomplete_trials = scan_incomplete_trials(layer3_dir, target_evaluators)

    if not incomplete_trials:
        print("✅ All trials already have complete evaluations!")
        return

    # Report findings
    total_missing = sum(len(missing) for _, missing in incomplete_trials)

    # Aggregate missing evaluators by model
    evaluator_counts = {}
    for _, missing_evals in incomplete_trials:
        for evaluator in missing_evals:
            evaluator_counts[evaluator] = evaluator_counts.get(evaluator, 0) + 1

    print(f"\nFound {len(incomplete_trials)} trials with missing evaluators:")
    for trial_id, missing_evals in incomplete_trials[:10]:  # Show first 10
        missing_list = ", ".join(sorted(missing_evals))
        print(f"  - {trial_id}: Missing {len(missing_evals)} evaluator(s) ({missing_list})")

    if len(incomplete_trials) > 10:
        print(f"  ... and {len(incomplete_trials) - 10} more")

    print(f"\n📊 Total missing evaluations: {total_missing}")
    print(f"\n📊 Missing evaluations by model:")
    for evaluator in sorted(evaluator_counts.keys()):
        count = evaluator_counts[evaluator]
        percentage = (count / total_missing) * 100
        print(f"  - {evaluator}: {count} ({percentage:.1f}%)")

    if dry_run:
        print("\n[DRY-RUN MODE] - No API calls will be made")
        print(f"Estimated time: ~{total_missing * 1.5:.0f}-{total_missing * 2:.0f} minutes")
        return

    # Confirm before proceeding
    print(f"\n⚠️  This will make ~{total_missing} API calls")
    print(f"Estimated time: ~{total_missing * 1.5:.0f}-{total_missing * 2:.0f} minutes")
    response = input("\nProceed? [y/N]: ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    # Backfill trials
    print(f"\n🔄 Starting backfill...")
    total_successful = 0
    total_failed = 0

    # Create parser
    parser = GracefulJsonParser(experiment_id=exp_mgr.experiment_id)

    for i, (trial_id, missing_evals) in enumerate(incomplete_trials, 1):
        print(f"[{i}/{len(incomplete_trials)}] {trial_id} ({len(missing_evals)} missing):")

        successful, failed = await backfill_trial(
            trial_id=trial_id,
            missing_evaluators=missing_evals,
            layer2_dir=layer2_dir,
            layer3_dir=layer3_dir,
            strategy=strategy,
            parser=parser,
            dry_run=False
        )

        total_successful += successful
        total_failed += failed

        # Small delay between trials (rate limiting)
        if i < len(incomplete_trials):
            await asyncio.sleep(2)

    # Report results
    print(f"\n{'='*60}")
    print(f"✅ Backfill complete: {total_successful}/{total_missing} successful")
    if total_failed > 0:
        print(f"⚠️  Failed: {total_failed}/{total_missing}")
        print("   Tip: Re-run this script to retry failed evaluations")


def validate_experiment(
    experiment_id: str,
    strategy: str,
    target_evaluators: List[str]
) -> None:
    """
    Validate that all trials have complete evaluations.

    Args:
        experiment_id: Experiment ID
        strategy: Evaluation strategy
        target_evaluators: List of expected evaluator IDs
    """
    # Load experiment
    exp_mgr = ExperimentManager(experiment_id=experiment_id)

    # Construct experiment directory from base_dir and experiment_id
    exp_dir = exp_mgr.base_dir / "experiments" / exp_mgr.experiment_id

    # Determine layer3 directory
    if strategy == "likert":
        layer3_dir = exp_dir / "data" / "layer3"
    else:
        layer3_dir = exp_dir / "data" / f"layer3_{strategy}"

    if not layer3_dir.exists():
        print(f"❌ Layer 3 directory not found: {layer3_dir}")
        return

    # Scan for incomplete trials
    incomplete_trials = scan_incomplete_trials(layer3_dir, target_evaluators)

    # Count total trials and evaluations
    total_trials = len(list(layer3_dir.glob("trial_*.json")))
    expected_evals = total_trials * len(target_evaluators)

    # Count actual evaluations
    actual_evals = 0
    for trial_file in layer3_dir.glob("trial_*.json"):
        with open(trial_file, 'r') as f:
            data = json.load(f)
        actual_evals += len(data.get('evaluations', {}))

    # Report
    print(f"\n{'='*60}")
    print(f"📊 Validation Report: {strategy.upper()} Rubric")
    print(f"{'='*60}")
    print(f"Total trials: {total_trials}")
    print(f"Expected evaluations: {expected_evals} ({total_trials} trials × {len(target_evaluators)} evaluators)")
    print(f"Actual evaluations: {actual_evals}")
    print(f"Completion rate: {actual_evals}/{expected_evals} ({actual_evals*100/expected_evals:.2f}%)")

    if incomplete_trials:
        print(f"\n⚠️  Incomplete trials: {len(incomplete_trials)}")
        for trial_id, missing_evals in incomplete_trials[:5]:
            missing_list = ", ".join(sorted(missing_evals))
            print(f"  - {trial_id}: Missing {missing_list}")
        if len(incomplete_trials) > 5:
            print(f"  ... and {len(incomplete_trials) - 5} more")
    else:
        print(f"\n✅ All trials complete!")
        print(f"   All {total_trials} trials have {len(target_evaluators)} evaluators")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill missing evaluator evaluations in Layer 3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--experiment",
        required=True,
        help="Experiment ID (e.g., exp_20251028_134615)"
    )

    parser.add_argument(
        "--evaluation-strategy",
        required=True,
        choices=["likert", "binary", "ternary"],
        help="Evaluation strategy to backfill"
    )

    parser.add_argument(
        "--target-evaluators",
        required=True,
        nargs="+",
        help="Space-separated list of expected evaluator IDs"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be backfilled without making API calls"
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate completion, don't backfill"
    )

    args = parser.parse_args()

    # Validation mode
    if args.validate_only:
        validate_experiment(
            experiment_id=args.experiment,
            strategy=args.evaluation_strategy,
            target_evaluators=args.target_evaluators
        )
        return

    # Backfill mode
    asyncio.run(backfill_experiment(
        experiment_id=args.experiment,
        strategy=args.evaluation_strategy,
        target_evaluators=args.target_evaluators,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
