"""
Re-evaluate Layer 3 on Existing Experiments

This tool re-runs Layer 3 integrity evaluation on existing Layer 2 constitutional
reasoning outputs using a different evaluator model. This allows comparing different
evaluators without re-running the expensive Layer 2 reasoning step.

Usage:
    poetry run python -m src.tools.re_evaluate_layer3 \\
        --experiment exp_20251026_123456 \\
        --evaluator claude-3-5-haiku-20241022

Directory Structure:
    - Primary evaluator (from original run): layer3/raw/, layer3/parsed/
    - Re-evaluation runs: layer3/{evaluator_id}/raw/, layer3/{evaluator_id}/parsed/
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List

from src.core.experiment_state import ExperimentManager
from src.core.graceful_parser import GracefulJsonParser
from src.core.prompts import build_integrity_evaluation_prompt
from src.core.layer3_evaluator import evaluate_layer3


async def re_evaluate_experiment(experiment_id: str, evaluator_id: str) -> Dict[str, int]:
    """
    Re-evaluate all trials in an experiment with a different Layer 3 evaluator

    Args:
        experiment_id: Experiment ID to re-evaluate
        evaluator_id: Model ID for the new evaluator

    Returns:
        {
            "total_trials": int,
            "successful": int,
            "failed": int,
            "skipped": int
        }
    """
    # Load experiment
    experiment_manager = ExperimentManager(experiment_id=experiment_id)

    if not experiment_manager.experiment_state:
        print(f"❌ Error: Experiment {experiment_id} not found")
        sys.exit(1)

    # Get Layer 2 output directory
    layer2_parsed_dir = experiment_manager.layer2_dir / "parsed"

    if not layer2_parsed_dir.exists():
        print(f"❌ Error: No Layer 2 outputs found for experiment {experiment_id}")
        print(f"   Expected directory: {layer2_parsed_dir}")
        sys.exit(1)

    # Load all Layer 2 outputs
    layer2_files = list(layer2_parsed_dir.glob("*.json"))

    if not layer2_files:
        print(f"❌ Error: No Layer 2 JSON files found in {layer2_parsed_dir}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"Re-evaluating Experiment: {experiment_id}")
    print(f"New Evaluator: {evaluator_id}")
    print(f"Total trials to re-evaluate: {len(layer2_files)}")
    print(f"{'='*80}\n")

    # Check if this evaluator already ran
    evaluator_dir = experiment_manager.layer3_dir / evaluator_id
    if evaluator_dir.exists():
        existing_files = list((evaluator_dir / "parsed").glob("*.json")) if (evaluator_dir / "parsed").exists() else []
        if existing_files:
            print(f"⚠️  Warning: {len(existing_files)} evaluations already exist for {evaluator_id}")
            response = input("Continue and overwrite? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                return {"total_trials": 0, "successful": 0, "failed": 0, "skipped": len(layer2_files)}

    # Initialize parser
    parser = GracefulJsonParser(experiment_id=experiment_id)

    # Track results
    successful = 0
    failed = 0

    # Process each trial
    for i, layer2_file in enumerate(layer2_files, 1):
        with open(layer2_file) as f:
            layer2_data = json.load(f)

        trial_id = layer2_data.get("testId")

        if not trial_id:
            print(f"⚠️  Skipping {layer2_file.name}: No testId found")
            continue

        # Load scenario data from Layer 2 output
        scenario_id = layer2_data.get("scenario")
        constitution_id = layer2_data.get("constitution")
        model_id = layer2_data.get("model")
        constitutional_response = layer2_data.get("response")

        if not all([scenario_id, constitution_id, model_id, constitutional_response]):
            print(f"⚠️  Skipping {trial_id}: Missing required Layer 2 data")
            failed += 1
            continue

        # Load facts from Layer 1 (or scenario JSON in Phase 1)
        # We need to reconstruct the eval prompt
        # For Phase 1, facts are embedded in the scenario
        from src.core.scenarios import load_scenarios
        scenarios = {s.id: s for s in load_scenarios()}
        scenario = scenarios.get(scenario_id)

        if not scenario:
            print(f"⚠️  Skipping {trial_id}: Scenario {scenario_id} not found")
            failed += 1
            continue

        # Build evaluation prompt
        # For Phase 1, we use the scenario's facts directly
        facts = {
            "establishedFacts": scenario.established_facts,
            "ambiguousElements": scenario.ambiguous_elements
        }

        eval_prompt = build_integrity_evaluation_prompt(
            established_facts=facts['establishedFacts'],
            ambiguous_elements=facts['ambiguousElements'],
            constitutional_response=constitutional_response
        )

        # Run evaluation
        print(f"[{i}/{len(layer2_files)}] Evaluating {trial_id}...")

        eval_result = await evaluate_layer3(
            trial_id=trial_id,
            eval_prompt=eval_prompt,
            evaluator_id=evaluator_id,
            is_primary=False,  # Re-evaluation, save to subdirectory
            experiment_manager=experiment_manager,
            parser=parser
        )

        if eval_result["success"]:
            successful += 1
            score = eval_result["integrity_data"]["overallScore"]
            print(f"   ✓ Score: {score}/100 ({eval_result['elapsed_ms']/1000:.1f}s)")
        else:
            failed += 1
            print(f"   ❌ {eval_result['error']}")

    # Summary
    print(f"\n{'='*80}")
    print(f"Re-evaluation Complete")
    print(f"{'='*80}")
    print(f"Total trials: {len(layer2_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"\nResults saved to:")
    print(f"  Raw: {experiment_manager.layer3_dir / evaluator_id / 'raw'}")
    print(f"  Parsed: {experiment_manager.layer3_dir / evaluator_id / 'parsed'}")
    print(f"\nTo compare evaluators, run:")
    print(f"  poetry run python -m analysis.compare_evaluators --experiment {experiment_id}")
    print()

    return {
        "total_trials": len(layer2_files),
        "successful": successful,
        "failed": failed,
        "skipped": 0
    }


def main():
    parser = argparse.ArgumentParser(
        description="Re-evaluate Layer 3 on existing experiment with a different evaluator"
    )
    parser.add_argument(
        "--experiment", "-e",
        required=True,
        help="Experiment ID to re-evaluate (e.g., exp_20251026_123456)"
    )
    parser.add_argument(
        "--evaluator",
        required=True,
        help="Evaluator model ID (e.g., claude-3-5-haiku-20241022, gemini-2-5-flash)"
    )

    args = parser.parse_args()

    # Run re-evaluation
    results = asyncio.run(re_evaluate_experiment(args.experiment, args.evaluator))

    # Exit with error code if all failed
    if results["failed"] == results["total_trials"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
