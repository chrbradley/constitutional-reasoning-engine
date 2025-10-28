#!/usr/bin/env python3
"""
Data Structure Inspector
Phase 0.4 - Step 1: Understand actual data format before writing analysis code

This script inspects the migrated data structure to document:
1. File organization and naming
2. JSON field structure (Layer 2 and Layer 3)
3. Trial metadata distribution (scenarios, constitutions, models, evaluators)
4. Data completeness check
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

EXPERIMENT_DIR = Path("results/experiments/exp_20251026_193228")

def inspect_trials():
    """Inspect trial files and document structure."""

    layer2_dir = EXPERIMENT_DIR / "data" / "layer2"
    layer3_dir = EXPERIMENT_DIR / "data" / "layer3"

    # Count files
    layer2_files = sorted(layer2_dir.glob("trial_*.json"))
    layer3_files = sorted(layer3_dir.glob("trial_*.json"))

    print(f"=== File Counts ===")
    print(f"Layer 2 files: {len(layer2_files)}")
    print(f"Layer 3 files: {len(layer3_files)}")
    print()

    # Sample trial structure
    print(f"=== Sample Trial Structure (trial_001) ===")
    with open(layer2_dir / "trial_001.json") as f:
        layer2_sample = json.load(f)

    print("Layer 2 fields:")
    for key in layer2_sample.keys():
        print(f"  - {key}")
    print()

    with open(layer3_dir / "trial_001.json") as f:
        layer3_sample = json.load(f)

    print("Layer 3 fields:")
    for key in layer3_sample.keys():
        print(f"  - {key}")
    print()

    print("Layer 3 response_parsed structure:")
    if "response_parsed" in layer3_sample:
        for dim_key in layer3_sample["response_parsed"].keys():
            print(f"  - {dim_key}")
            if isinstance(layer3_sample["response_parsed"][dim_key], dict):
                for subkey in layer3_sample["response_parsed"][dim_key].keys():
                    print(f"      - {subkey}")
    print()

    # Collect metadata distributions
    scenarios = defaultdict(int)
    constitutions = defaultdict(int)
    layer2_models = defaultdict(int)
    evaluators = defaultdict(int)

    for trial_file in layer3_files:
        with open(trial_file) as f:
            trial = json.load(f)

        scenarios[trial.get("scenario_id", "unknown")] += 1
        constitutions[trial.get("constitution", "unknown")] += 1
        layer2_models[trial.get("model", "unknown")] += 1
        evaluators[trial.get("evaluator", "unknown")] += 1

    print(f"=== Metadata Distributions ===")
    print(f"Scenarios ({len(scenarios)}):")
    for scenario, count in sorted(scenarios.items()):
        print(f"  - {scenario}: {count} trials")
    print()

    print(f"Constitutions ({len(constitutions)}):")
    for constitution, count in sorted(constitutions.items()):
        print(f"  - {constitution}: {count} trials")
    print()

    print(f"Layer 2 Models ({len(layer2_models)}):")
    for model, count in sorted(layer2_models.items()):
        print(f"  - {model}: {count} trials")
    print()

    print(f"Evaluators ({len(evaluators)}):")
    for evaluator, count in sorted(evaluators.items()):
        print(f"  - {evaluator}: {count} trials")
    print()

    # Check score ranges
    print(f"=== Score Range Checks ===")
    dimensions = ["factual_adherence", "value_transparency", "logical_coherence", "overall_score"]

    for dim in dimensions:
        scores = []
        for trial_file in layer3_files:
            with open(trial_file) as f:
                trial = json.load(f)

            if "response_parsed" in trial:
                if dim == "overall_score":
                    score = trial["response_parsed"].get(dim)
                else:
                    dim_data = trial["response_parsed"].get(dim, {})
                    score = dim_data.get("score") if isinstance(dim_data, dict) else None

                if score is not None:
                    scores.append(score)

        if scores:
            print(f"{dim}:")
            print(f"  Min: {min(scores)}")
            print(f"  Max: {max(scores)}")
            print(f"  Mean: {sum(scores) / len(scores):.1f}")
            print(f"  Count: {len(scores)}")
    print()

    # Data completeness
    print(f"=== Data Completeness ===")
    complete_trials = 0
    missing_evaluations = []

    for trial_file in layer2_files:
        trial_id = trial_file.stem
        layer3_file = layer3_dir / f"{trial_id}.json"

        if layer3_file.exists():
            with open(layer3_file) as f:
                trial = json.load(f)

            # Check if evaluation is complete
            if trial.get("status") == "completed" and "response_parsed" in trial:
                complete_trials += 1
            else:
                missing_evaluations.append(trial_id)
        else:
            missing_evaluations.append(trial_id)

    print(f"Complete trials (Layer 2 + Layer 3): {complete_trials}")
    print(f"Missing/incomplete evaluations: {len(missing_evaluations)}")
    if missing_evaluations:
        print(f"  Trial IDs: {', '.join(missing_evaluations[:10])}")
        if len(missing_evaluations) > 10:
            print(f"  ... and {len(missing_evaluations) - 10} more")
    print()

    # Document exact JSON paths for analysis
    print(f"=== JSON Paths for Analysis Code ===")
    print("Layer 2:")
    print("  trial_id: trial['trial_id']")
    print("  scenario: trial['scenario_id']")
    print("  model: trial['model']")
    print("  constitution: trial['constitution']")
    print("  reasoning: trial['response_parsed']")
    print()
    print("Layer 3:")
    print("  trial_id: trial['trial_id']")
    print("  scenario: trial['scenario_id']")
    print("  layer2_model: trial['model']")
    print("  constitution: trial['constitution']")
    print("  evaluator: trial['evaluator']")
    print("  factual_score: trial['response_parsed']['factual_adherence']['score']")
    print("  transparency_score: trial['response_parsed']['value_transparency']['score']")
    print("  coherence_score: trial['response_parsed']['logical_coherence']['score']")
    print("  overall_score: trial['response_parsed']['overall_score']")
    print("  explanations: trial['response_parsed']['factual_adherence']['explanation']")
    print("  examples: trial['response_parsed']['factual_adherence']['examples']")
    print()

if __name__ == "__main__":
    inspect_trials()
