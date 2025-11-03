"""
Baseline Analysis: Constitutional Effect Sizes

This script analyzes the "no-constitution" control trials to measure absolute
constitutional effects rather than just relative comparisons.

Key Questions:
1. What are baseline scores for each model without constitutional framing?
2. Do constitutions actually change model behavior (deltas from baseline)?
3. Which models are most/least sensitive to constitutional steering?
4. Which constitutions have strongest positive/negative effects?

Outputs:
- baseline_analysis.json: Detailed statistical results
- baseline_comparison_figure.json: Visualization data for web app
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
from scipy import stats

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_experiment_data(experiment_id: str = "exp_20251028_134615") -> Dict[str, Any]:
    """Load trial registry and consensus scores for the experiment."""
    exp_path = project_root / "results" / "experiments" / experiment_id

    # Load trial registry
    with open(exp_path / "state" / "trial_registry.json", "r") as f:
        trial_registry = json.load(f)

    # Load consensus scores
    with open(exp_path / "analysis" / "consensus_scores.json", "r") as f:
        consensus_data = json.load(f)

    return {
        "trial_registry": trial_registry,
        "consensus_scores": consensus_data["consensus_scores"],
        "experiment_id": experiment_id
    }


def join_metadata_with_scores(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Join trial metadata with consensus scores."""
    trials_metadata = data["trial_registry"]["trials"]
    consensus_scores = data["consensus_scores"]

    # Create lookup dict for quick access
    scores_by_trial = {item["trial_id"]: item for item in consensus_scores}

    joined_data = []
    for trial_id, metadata in trials_metadata.items():
        if trial_id in scores_by_trial:
            joined_data.append({
                "trial_id": trial_id,
                "scenario_id": metadata["scenario_id"],
                "constitution": metadata["constitution"],
                "model": metadata["model"],
                "scores": scores_by_trial[trial_id]["mean_all"]  # Using mean_all consensus
            })

    return joined_data


def calculate_baseline_scores(joined_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Calculate baseline scores (no-constitution) per model."""
    baseline_trials = [t for t in joined_data if t["constitution"] == "no-constitution"]

    baselines_by_model = {}
    for model in set(t["model"] for t in baseline_trials):
        model_trials = [t for t in baseline_trials if t["model"] == model]

        # Calculate mean scores across all no-constitution trials for this model
        epistemic = np.mean([t["scores"]["epistemic_integrity"] for t in model_trials])
        value_trans = np.mean([t["scores"]["value_transparency"] for t in model_trials])
        overall = np.mean([t["scores"]["overall_score"] for t in model_trials])

        baselines_by_model[model] = {
            "epistemic_integrity": epistemic,
            "value_transparency": value_trans,
            "overall_score": overall,
            "n_trials": len(model_trials)
        }

    return baselines_by_model


def calculate_constitutional_deltas(
    joined_data: List[Dict[str, Any]],
    baselines: Dict[str, Dict[str, float]]
) -> List[Dict[str, Any]]:
    """Calculate delta from baseline for each constitutional trial."""
    constitutional_trials = [t for t in joined_data if t["constitution"] != "no-constitution"]

    deltas = []
    for trial in constitutional_trials:
        model = trial["model"]
        baseline = baselines[model]

        delta = {
            "trial_id": trial["trial_id"],
            "scenario_id": trial["scenario_id"],
            "constitution": trial["constitution"],
            "model": model,
            "raw_scores": trial["scores"],
            "baseline_scores": baseline,
            "deltas": {
                "epistemic_integrity": trial["scores"]["epistemic_integrity"] - baseline["epistemic_integrity"],
                "value_transparency": trial["scores"]["value_transparency"] - baseline["value_transparency"],
                "overall_score": trial["scores"]["overall_score"] - baseline["overall_score"]
            }
        }
        deltas.append(delta)

    return deltas


def analyze_constitutional_effects(deltas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze constitutional effect sizes across models and constitutions."""

    # Get unique models and constitutions
    models = sorted(set(d["model"] for d in deltas))
    constitutions = sorted(set(d["constitution"] for d in deltas))

    # Calculate mean deltas by constitution
    effects_by_constitution = {}
    for const in constitutions:
        const_deltas = [d["deltas"] for d in deltas if d["constitution"] == const]

        effects_by_constitution[const] = {
            "epistemic_integrity": {
                "mean": float(np.mean([d["epistemic_integrity"] for d in const_deltas])),
                "std": float(np.std([d["epistemic_integrity"] for d in const_deltas])),
                "n": len(const_deltas)
            },
            "value_transparency": {
                "mean": float(np.mean([d["value_transparency"] for d in const_deltas])),
                "std": float(np.std([d["value_transparency"] for d in const_deltas])),
                "n": len(const_deltas)
            },
            "overall_score": {
                "mean": float(np.mean([d["overall_score"] for d in const_deltas])),
                "std": float(np.std([d["overall_score"] for d in const_deltas])),
                "n": len(const_deltas)
            }
        }

    # Calculate mean deltas by model (constitutional sensitivity)
    sensitivity_by_model = {}
    for model in models:
        model_deltas = [d["deltas"] for d in deltas if d["model"] == model]

        # Calculate absolute mean deviation from baseline
        abs_deltas = [abs(d["overall_score"]) for d in model_deltas]

        sensitivity_by_model[model] = {
            "mean_absolute_delta": float(np.mean(abs_deltas)),
            "std_absolute_delta": float(np.std(abs_deltas)),
            "mean_delta": float(np.mean([d["overall_score"] for d in model_deltas])),
            "n": len(model_deltas)
        }

    # Test if deltas are significantly different from zero (one-sample t-test)
    # This tests: "Do constitutions actually change behavior?"
    all_overall_deltas = [d["deltas"]["overall_score"] for d in deltas]
    t_stat, p_value = stats.ttest_1samp(all_overall_deltas, 0)

    return {
        "effects_by_constitution": effects_by_constitution,
        "sensitivity_by_model": sensitivity_by_model,
        "global_test": {
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "mean_delta": float(np.mean(all_overall_deltas)),
            "interpretation": "Constitutions significantly change behavior" if p_value < 0.05 else "No significant constitutional effect"
        }
    }


def generate_figure_data(
    baselines: Dict[str, Dict[str, float]],
    deltas: List[Dict[str, Any]],
    effects_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate data for baseline comparison visualization."""

    # Figure 1: Baseline scores by model
    baseline_fig = {
        "models": list(baselines.keys()),
        "epistemic_integrity": [baselines[m]["epistemic_integrity"] for m in baselines.keys()],
        "value_transparency": [baselines[m]["value_transparency"] for m in baselines.keys()],
        "overall_score": [baselines[m]["overall_score"] for m in baselines.keys()]
    }

    # Figure 2: Constitutional effect sizes (mean deltas from baseline)
    const_effects = effects_analysis["effects_by_constitution"]
    effect_size_fig = {
        "constitutions": list(const_effects.keys()),
        "epistemic_integrity_delta": [const_effects[c]["epistemic_integrity"]["mean"] for c in const_effects.keys()],
        "value_transparency_delta": [const_effects[c]["value_transparency"]["mean"] for c in const_effects.keys()],
        "overall_score_delta": [const_effects[c]["overall_score"]["mean"] for c in const_effects.keys()]
    }

    # Figure 3: Model constitutional sensitivity (absolute mean deltas)
    sensitivity = effects_analysis["sensitivity_by_model"]
    sensitivity_fig = {
        "models": list(sensitivity.keys()),
        "mean_absolute_delta": [sensitivity[m]["mean_absolute_delta"] for m in sensitivity.keys()],
        "std_absolute_delta": [sensitivity[m]["std_absolute_delta"] for m in sensitivity.keys()]
    }

    return {
        "baseline_scores_by_model": baseline_fig,
        "constitutional_effect_sizes": effect_size_fig,
        "model_constitutional_sensitivity": sensitivity_fig
    }


def main():
    """Run baseline analysis pipeline."""
    print("Loading experiment data...")
    data = load_experiment_data()

    print("Joining metadata with consensus scores...")
    joined_data = join_metadata_with_scores(data)
    print(f"  Total trials: {len(joined_data)}")

    print("\nCalculating baseline scores (no-constitution)...")
    baselines = calculate_baseline_scores(joined_data)
    print("  Baseline scores by model:")
    for model, scores in baselines.items():
        print(f"    {model}: Overall = {scores['overall_score']:.1f} (n={scores['n_trials']})")

    print("\nCalculating constitutional deltas...")
    deltas = calculate_constitutional_deltas(joined_data, baselines)
    print(f"  Constitutional trials: {len(deltas)}")

    print("\nAnalyzing constitutional effects...")
    effects = analyze_constitutional_effects(deltas)
    print(f"  Global test: p={effects['global_test']['p_value']:.4f}")
    print(f"  Mean delta from baseline: {effects['global_test']['mean_delta']:.2f} points")
    print(f"  {effects['global_test']['interpretation']}")

    print("\nConstitutional effect sizes:")
    for const, effect in effects["effects_by_constitution"].items():
        print(f"  {const}: {effect['overall_score']['mean']:+.2f} ± {effect['overall_score']['std']:.2f}")

    print("\nModel constitutional sensitivity:")
    for model, sens in effects["sensitivity_by_model"].items():
        print(f"  {model}: {sens['mean_absolute_delta']:.2f} ± {sens['std_absolute_delta']:.2f}")

    print("\nGenerating figure data...")
    figure_data = generate_figure_data(baselines, deltas, effects)

    # Export results
    output_dir = project_root / "results" / "experiments" / data["experiment_id"] / "analysis"

    print("\nExporting baseline_analysis.json...")
    baseline_output = {
        "experiment_id": data["experiment_id"],
        "baseline_scores": baselines,
        "constitutional_deltas": deltas,
        "effects_analysis": effects,
        "figure_data": figure_data
    }

    with open(output_dir / "baseline_analysis.json", "w") as f:
        json.dump(baseline_output, f, indent=2)

    print(f"✓ Saved to {output_dir / 'baseline_analysis.json'}")
    print("\nBaseline analysis complete!")


if __name__ == "__main__":
    main()
