#!/usr/bin/env python3
"""
Re-Evaluate Experiment with Different Rubric Format

This script takes an existing experiment's Layer 2 reasoning outputs and re-evaluates
them using a different rubric format (Likert, binary, or ternary). This allows comparing
different evaluation strategies without re-running expensive Layer 2 reasoning.

Usage:
    poetry run python scripts/reeval_with_rubric.py \
        --experiment exp_20251028_095612 \
        --evaluation-strategy binary \
        --evaluators claude-sonnet-4-5 gpt-4o

Features:
    - Modular: Apply any rubric to any experiment
    - Efficient: No Layer 2 data duplication
    - Resumable: Tracks completion, skips already-evaluated trials
    - Multi-evaluator: Supports 1+ evaluators per trial

Directory Structure (within same experiment):
    exp_20251028_095612/
        ├── data/
        │   ├── layer2/           (original reasoning - shared)
        │   ├── layer3/           (Likert evaluations - default)
        │   ├── layer3_binary/    (Binary evaluations)
        │   └── layer3_ternary/   (Ternary evaluations)
        └── state/
            └── trial_registry.json
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import shutil

# Add project root to Python path (fixes ModuleNotFoundError)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.experiment_state import ExperimentManager
from src.core.scenarios import load_scenarios
from src.core.prompts import (
    build_integrity_evaluation_prompt_likert,
    build_integrity_evaluation_prompt_binary,
    build_integrity_evaluation_prompt_ternary
)
from src.core.layer3_evaluator import evaluate_layer3
from src.core.graceful_parser import GracefulJsonParser


EVALUATION_STRATEGIES = {
    'likert': build_integrity_evaluation_prompt_likert,
    'binary': build_integrity_evaluation_prompt_binary,
    'ternary': build_integrity_evaluation_prompt_ternary
}


def load_layer2_trial(trial_file: Path) -> Dict[str, Any]:
    """Load Layer 2 reasoning from a trial file."""
    with open(trial_file, 'r') as f:
        data = json.load(f)

    # Extract constitutional response - support multiple formats
    if 'response_parsed' in data:
        # New format from recent experiments
        return data['response_parsed']
    elif 'constitutionalReasoning' in data:
        # Legacy format
        return data['constitutionalReasoning']
    elif 'reasoning' in data:
        # Already in extracted format
        return data
    else:
        raise ValueError(f"Unexpected Layer 2 format in {trial_file.name}")


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


async def reeval_trial(
    trial_id: str,
    layer2_file: Path,
    scenario_id: str,
    evaluators: List[str],
    evaluation_strategy: str,
    layer3_dir: Path,
    parser: GracefulJsonParser
) -> Dict[str, Any]:
    """
    Re-evaluate a single trial with specified rubric format.

    Returns:
        {
            'trial_id': str,
            'successful_evaluators': List[str],
            'failed_evaluators': List[str]
        }
    """
    print(f"  Re-evaluating {trial_id} with {evaluation_strategy} rubric...")

    # Load Layer 2 reasoning
    layer2_response = load_layer2_trial(layer2_file)

    # Get scenario facts
    facts = get_scenario_facts(scenario_id)

    # Select prompt builder based on strategy
    prompt_builder = EVALUATION_STRATEGIES[evaluation_strategy]

    # Build evaluation prompt
    eval_prompt = prompt_builder(
        established_facts=facts['establishedFacts'],
        ambiguous_elements=facts['ambiguousElements'],
        constitutional_response=layer2_response
    )

    # Evaluate with each evaluator
    successful = []
    failed = []
    layer3_file_path = layer3_dir / f"{trial_id}.json"

    for idx, evaluator_id in enumerate(evaluators):
        is_primary = (idx == 0)

        try:
            # Note: We can't use experiment_manager here since layer3_dir is custom
            # So we'll call the API and save manually
            from src.core.models import get_model_response
            from src.core.truncation_detector import TruncationDetector

            truncation_detector = TruncationDetector()
            max_tokens = 4000
            max_retries = 3

            for attempt in range(max_retries):
                integrity_response = await get_model_response(
                    model_id=evaluator_id,
                    prompt=eval_prompt,
                    temperature=0.3,
                    max_tokens=max_tokens
                )

                # Parse response
                integrity_data, status = parser.parse_integrity_response(
                    integrity_response,
                    f"{trial_id}_integrity_{evaluator_id}"
                )

                # Check truncation
                from src.core.graceful_parser import ParseStatus
                is_truncated, trunc_reason = truncation_detector.is_truncated(
                    integrity_response,
                    parse_success=(status == ParseStatus.SUCCESS)
                )

                if not is_truncated or status == ParseStatus.SUCCESS:
                    break

                if attempt < max_retries - 1:
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

            # Load existing Layer 3 file or create new
            if layer3_file_path.exists():
                with open(layer3_file_path, 'r') as f:
                    layer3_data = json.load(f)
            else:
                layer3_data = {
                    'trialId': trial_id,
                    'scenarioId': scenario_id,
                    'evaluationStrategy': evaluation_strategy,
                    'evaluations': {}
                }

            # Add this evaluator's result
            layer3_data['evaluations'][evaluator_id] = {
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

            # Save incrementally (fault tolerance)
            with open(layer3_file_path, 'w') as f:
                json.dump(layer3_data, f, indent=2)

            successful.append(evaluator_id)
            print(f"    ✓ {evaluator_id}")

        except Exception as e:
            failed.append(evaluator_id)
            print(f"    ✗ {evaluator_id}: {str(e)}")

    return {
        'trial_id': trial_id,
        'successful_evaluators': successful,
        'failed_evaluators': failed
    }


async def reeval_experiment(
    experiment_id: str,
    evaluation_strategy: str,
    evaluators: List[str],
    resume: bool = True,
    batch_size: int = 12
) -> Dict[str, Any]:
    """
    Re-evaluate entire experiment with specified rubric format.

    Args:
        experiment_id: Experiment to re-evaluate
        evaluation_strategy: 'likert', 'binary', or 'ternary'
        evaluators: List of evaluator model IDs
        resume: Resume from partial run
        batch_size: Number of trials per batch

    Returns:
        {
            'experiment_id': str,
            'evaluation_strategy': str,
            'total_trials': int,
            'successful_trials': int,
            'failed_trials': int,
            'evaluators_used': List[str]
        }
    """
    # Validate strategy
    if evaluation_strategy not in EVALUATION_STRATEGIES:
        raise ValueError(f"Invalid strategy: {evaluation_strategy}. Must be one of: {list(EVALUATION_STRATEGIES.keys())}")

    # Load experiment
    experiment_manager = ExperimentManager(experiment_id=experiment_id)
    if not experiment_manager.experiment_state:
        raise FileNotFoundError(f"Experiment not found: {experiment_id}")

    experiment_dir = Path("results/experiments") / experiment_id

    print(f"\n=== Re-Evaluation with {evaluation_strategy.upper()} Rubric ===")
    print(f"Experiment: {experiment_id}")
    print(f"Evaluators: {', '.join(evaluators)}\n")

    # Create layer3_{strategy} directory in same experiment
    if evaluation_strategy == 'likert':
        layer3_dir = experiment_dir / "data" / "layer3"  # Default
    else:
        layer3_dir = experiment_dir / "data" / f"layer3_{evaluation_strategy}"

    layer3_dir.mkdir(parents=True, exist_ok=True)

    # Initialize parser
    parser = GracefulJsonParser(experiment_dir / "data" / "raw")

    # Get list of Layer 2 trials from source experiment
    layer2_dir = experiment_dir / "data" / "layer2"
    layer2_files = sorted(layer2_dir.glob("trial_*.json"))

    if not layer2_files:
        raise FileNotFoundError(f"No Layer 2 trials found in {layer2_dir}")

    print(f"Found {len(layer2_files)} trials to re-evaluate\n")

    # Check which trials are already complete (if resuming)
    completed_trials = set()
    if resume:
        for layer3_file in layer3_dir.glob("trial_*.json"):
            with open(layer3_file, 'r') as f:
                data = json.load(f)
            # Check if all evaluators have completed
            if len(data.get('evaluations', {})) == len(evaluators):
                completed_trials.add(layer3_file.stem)  # trial_001, etc.

        if completed_trials:
            print(f"Resuming: {len(completed_trials)} trials already completed\n")

    # Process trials
    successful_trials = 0
    failed_trials = 0

    for i, layer2_file in enumerate(layer2_files, 1):
        trial_id = layer2_file.stem  # e.g., trial_001

        if trial_id in completed_trials:
            print(f"[{i}/{len(layer2_files)}] Skipping {trial_id} (already complete)")
            successful_trials += 1
            continue

        # Extract scenario_id from Layer 2 file
        with open(layer2_file, 'r') as f:
            layer2_data = json.load(f)
        scenario_id = layer2_data.get('scenario_id', '')

        if not scenario_id:
            print(f"[{i}/{len(layer2_files)}] ✗ {trial_id}: Missing scenario_id")
            failed_trials += 1
            continue

        print(f"[{i}/{len(layer2_files)}] {trial_id}")

        # Re-evaluate
        result = await reeval_trial(
            trial_id=trial_id,
            layer2_file=layer2_file,
            scenario_id=scenario_id,
            evaluators=evaluators,
            evaluation_strategy=evaluation_strategy,
            layer3_dir=layer3_dir,
            parser=parser
        )

        if result['successful_evaluators']:
            successful_trials += 1
        if result['failed_evaluators']:
            failed_trials += 1

        # Batch delay (API rate limiting)
        if i % batch_size == 0 and i < len(layer2_files):
            print(f"\n  Batch complete. Waiting 20 seconds...\n")
            await asyncio.sleep(20)

    results = {
        'experiment_id': experiment_id,
        'evaluation_strategy': evaluation_strategy,
        'layer3_directory': str(layer3_dir.relative_to(Path("results/experiments"))),
        'total_trials': len(layer2_files),
        'successful_trials': successful_trials,
        'failed_trials': failed_trials,
        'evaluators_used': evaluators
    }

    print(f"\n=== Re-Evaluation Complete ===")
    print(f"Total trials: {results['total_trials']}")
    print(f"Successful: {results['successful_trials']}")
    print(f"Failed: {results['failed_trials']}")
    print(f"Output directory: {layer3_dir}\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Re-evaluate experiment with different rubric format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Re-evaluate with binary rubric
  poetry run python scripts/reeval_with_rubric.py \\
      --experiment exp_20251028_095612 \\
      --evaluation-strategy binary \\
      --evaluators claude-sonnet-4-5 gpt-4o

  # Re-evaluate with ternary rubric (all 5 evaluators)
  poetry run python scripts/reeval_with_rubric.py \\
      --experiment exp_20251028_095612 \\
      --evaluation-strategy ternary \\
      --evaluators claude-sonnet-4-5 gpt-4o gemini-2-5-pro grok-3 deepseek-chat
        """
    )

    parser.add_argument(
        '--experiment', '-e',
        type=str,
        required=True,
        help='Experiment ID to re-evaluate'
    )

    parser.add_argument(
        '--evaluation-strategy',
        type=str,
        required=True,
        choices=['likert', 'binary', 'ternary'],
        help='Rubric format: likert (0-100), binary (PASS/FAIL), or ternary (STRONG/PARTIAL/WEAK)'
    )

    parser.add_argument(
        '--evaluators',
        type=str,
        nargs='+',
        required=True,
        help='Evaluator model IDs (space-separated)'
    )

    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Start fresh (do not resume partial run)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=12,
        help='Number of trials per batch (default: 12)'
    )

    args = parser.parse_args()

    try:
        results = asyncio.run(reeval_experiment(
            experiment_id=args.experiment,
            evaluation_strategy=args.evaluation_strategy,
            evaluators=args.evaluators,
            resume=not args.no_resume,
            batch_size=args.batch_size
        ))

        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
