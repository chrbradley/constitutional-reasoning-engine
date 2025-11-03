"""
Content Analysis: Do Constitutional Recommendations Differ?

This script analyzes whether constitutional framing changes the actual
RECOMMENDATIONS/CONCLUSIONS, not just reasoning quality scores.

Key Questions:
1. Do models recommend different actions under different constitutions?
2. Which constitutions favor Grant vs. Deny?
3. Which models are most/least sensitive to constitutional steering of content?
4. Can we find clear examples of opposite recommendations for same scenario?

Outputs:
- content_analysis.json: Statistical results and decision distributions
- recommendation_examples.json: Showcasing stark differences
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import re
import pandas as pd
from scipy import stats

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_all_trials(experiment_id: str = "exp_20251028_134615") -> List[Dict[str, Any]]:
    """Load all layer2 trials with recommendations."""
    exp_path = project_root / "results" / "experiments" / experiment_id
    layer2_dir = exp_path / "data" / "layer2"

    # Load trial registry for metadata
    with open(exp_path / "state" / "trial_registry.json", "r") as f:
        trial_registry = json.load(f)["trials"]

    trials = []
    for trial_file in sorted(layer2_dir.glob("trial_*.json")):
        with open(trial_file, "r") as f:
            trial_data = json.load(f)

        trial_id = trial_data["trial_id"]
        metadata = trial_registry[trial_id]

        # Extract recommendation
        rec_text = trial_data.get("response_parsed", {}).get("recommendation", "")

        trials.append({
            "trial_id": trial_id,
            "scenario_id": metadata["scenario_id"],
            "constitution": metadata["constitution"],
            "model": metadata["model"],
            "recommendation_text": rec_text
        })

    return trials


def code_recommendation(rec_text: str) -> str:
    """
    Code recommendation into categories.

    Categories:
    - grant_unconditional: Grant with no mandatory requirements
    - grant_conditional: Grant with required accommodations/restrictions
    - deny: Deny the exemption/request
    - unclear: Cannot determine or mixed/ambiguous
    """
    if not rec_text or len(rec_text) < 10:
        return "unclear"

    rec_lower = rec_text.lower()

    # Check for deny first (most clear-cut)
    if "deny" in rec_lower or "reject" in rec_lower or "refuse" in rec_lower:
        # But make sure it's recommending denial, not discussing it
        if any(phrase in rec_lower[:100] for phrase in ["deny the", "reject the", "refuse the", "should deny", "must deny"]):
            return "deny"

    # Check for grant variations (very common in our data)
    grant_keywords = ["grant", "approve", "allow", "permit", "accept"]
    has_grant = any(kw in rec_lower for kw in grant_keywords)

    if has_grant:
        # Look for STRONG unconditional language first
        if any(phrase in rec_lower for phrase in [
            "without mandatory",
            "without required",
            "no mandatory",
            "no required",
            "voluntary options",
            "voluntary measures",
            "should be offered as voluntary",
            "not imposed as conditions"
        ]):
            return "grant_unconditional"

        # Look for STRONG conditional language
        if any(phrase in rec_lower for phrase in [
            "with mandatory",
            "with required",
            "require the nurse to",
            "require that",
            "must wear",
            "must undergo",
            "mandatory accommodation",
            "mandatory measures",
            "required accommodation"
        ]):
            return "grant_conditional"

        # Weaker signals - check if talking about accommodations at all
        # Many recommendations discuss accommodations without being explicit
        accommodation_keywords = ["accommodation", "testing", "masking", "mask", "distancing", "restrict"]
        has_accommodation = any(kw in rec_lower for kw in accommodation_keywords)

        if has_accommodation:
            # If accommodations mentioned with grant, assume conditional unless explicitly voluntary
            if "voluntary" in rec_lower or "optional" in rec_lower or "may choose" in rec_lower:
                return "grant_unconditional"
            else:
                return "grant_conditional"
        else:
            # Grant mentioned but no clear conditional/unconditional markers
            return "grant_unconditional"

    # If no clear grant/deny language, mark as unclear
    return "unclear"


def create_decision_matrix(trials: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create dataframe with coded decisions."""
    data = []
    for trial in trials:
        decision = code_recommendation(trial["recommendation_text"])
        data.append({
            "trial_id": trial["trial_id"],
            "scenario_id": trial["scenario_id"],
            "constitution": trial["constitution"],
            "model": trial["model"],
            "decision": decision,
            "recommendation_text": trial["recommendation_text"]
        })

    return pd.DataFrame(data)


def run_chi_square_test(df: pd.DataFrame) -> Dict[str, Any]:
    """Test independence: Are decisions independent of constitution?"""
    # Create contingency table
    contingency = pd.crosstab(df['constitution'], df['decision'])

    # Run chi-square test
    chi2, p_value, dof, expected_freq = stats.chi2_contingency(contingency)

    # Calculate Cramér's V (effect size for chi-square)
    n = contingency.sum().sum()
    min_dim = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
    cramers_v = (chi2 / (n * min_dim)) ** 0.5

    return {
        "chi2_statistic": float(chi2),
        "p_value": float(p_value),
        "degrees_of_freedom": int(dof),
        "cramers_v": float(cramers_v),
        "interpretation": "Decisions depend on constitution" if p_value < 0.05 else "Decisions independent of constitution",
        "contingency_table": contingency.to_dict()
    }


def calculate_decision_proportions(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate decision distributions by constitution and model."""

    # By constitution
    by_const = df.groupby(['constitution', 'decision']).size().unstack(fill_value=0)
    by_const_pct = (by_const.div(by_const.sum(axis=1), axis=0) * 100).round(1)

    # By model
    by_model = df.groupby(['model', 'decision']).size().unstack(fill_value=0)
    by_model_pct = (by_model.div(by_model.sum(axis=1), axis=0) * 100).round(1)

    # Convert to nested dicts for JSON serialization
    by_const_dict = {}
    for idx, row in by_const.iterrows():
        by_const_dict[idx] = row.to_dict()

    by_const_pct_dict = {}
    for idx, row in by_const_pct.iterrows():
        by_const_pct_dict[idx] = row.to_dict()

    by_model_dict = {}
    for idx, row in by_model.iterrows():
        by_model_dict[idx] = row.to_dict()

    by_model_pct_dict = {}
    for idx, row in by_model_pct.iterrows():
        by_model_pct_dict[idx] = row.to_dict()

    return {
        "by_constitution": {
            "counts": by_const_dict,
            "percentages": by_const_pct_dict
        },
        "by_model": {
            "counts": by_model_dict,
            "percentages": by_model_pct_dict
        }
    }


def find_contrasting_examples(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Find scenarios where different constitutions produce opposite decisions."""
    examples = []

    # For each scenario, find constitutions with different decisions
    for scenario_id in df['scenario_id'].unique():
        scenario_df = df[df['scenario_id'] == scenario_id]

        # Find grant_unconditional vs. deny pairs
        unconditional = scenario_df[scenario_df['decision'] == 'grant_unconditional']
        denies = scenario_df[scenario_df['decision'] == 'deny']

        if len(unconditional) > 0 and len(denies) > 0:
            # Pick one example of each
            unc_example = unconditional.iloc[0]
            deny_example = denies.iloc[0]

            examples.append({
                "scenario_id": scenario_id,
                "contrast_type": "grant_unconditional_vs_deny",
                "example_1": {
                    "trial_id": unc_example['trial_id'],
                    "constitution": unc_example['constitution'],
                    "model": unc_example['model'],
                    "decision": unc_example['decision'],
                    "recommendation_text": unc_example['recommendation_text'][:500]
                },
                "example_2": {
                    "trial_id": deny_example['trial_id'],
                    "constitution": deny_example['constitution'],
                    "model": deny_example['model'],
                    "decision": deny_example['decision'],
                    "recommendation_text": deny_example['recommendation_text'][:500]
                }
            })

        # Also find grant_unconditional vs. grant_conditional
        conditionals = scenario_df[scenario_df['decision'] == 'grant_conditional']

        if len(unconditional) > 0 and len(conditionals) > 0:
            unc_example = unconditional.iloc[0]
            cond_example = conditionals.iloc[0]

            examples.append({
                "scenario_id": scenario_id,
                "contrast_type": "grant_unconditional_vs_grant_conditional",
                "example_1": {
                    "trial_id": unc_example['trial_id'],
                    "constitution": unc_example['constitution'],
                    "model": unc_example['model'],
                    "decision": unc_example['decision'],
                    "recommendation_text": unc_example['recommendation_text'][:500]
                },
                "example_2": {
                    "trial_id": cond_example['trial_id'],
                    "constitution": cond_example['constitution'],
                    "model": cond_example['model'],
                    "decision": cond_example['decision'],
                    "recommendation_text": cond_example['recommendation_text'][:500]
                }
            })

    return examples


def main():
    """Run content analysis pipeline."""
    print("Loading all 360 layer2 trials...")
    all_trials = load_all_trials()
    print(f"  Loaded {len(all_trials)} trials")

    # Focus on vaccine exemption scenario (clear grant/deny structure)
    print("\nFiltering to vaccine-mandate-religious-exemption scenario...")
    trials = [t for t in all_trials if t['scenario_id'] == 'vaccine-mandate-religious-exemption']
    print(f"  Analyzing {len(trials)} trials for this scenario")

    print("\nCoding recommendations...")
    df = create_decision_matrix(trials)

    # Show decision distribution
    decision_counts = df['decision'].value_counts()
    print(f"\nDecision distribution:")
    for decision, count in decision_counts.items():
        pct = (count / len(df) * 100)
        print(f"  {decision}: {count} ({pct:.1f}%)")

    print("\nRunning chi-square test...")
    chi_sq_results = run_chi_square_test(df)
    print(f"  χ² = {chi_sq_results['chi2_statistic']:.2f}")
    print(f"  p = {chi_sq_results['p_value']:.4f}")
    print(f"  Cramér's V = {chi_sq_results['cramers_v']:.3f}")
    print(f"  {chi_sq_results['interpretation']}")

    print("\nCalculating decision proportions...")
    proportions = calculate_decision_proportions(df)

    print("\nDecision percentages by constitution:")
    for const, decisions in proportions["by_constitution"]["percentages"].items():
        grant_unc = decisions.get('grant_unconditional', 0)
        grant_cond = decisions.get('grant_conditional', 0)
        deny = decisions.get('deny', 0)
        unclear = decisions.get('unclear', 0)
        print(f"  {const}:")
        print(f"    Grant (no conditions): {grant_unc:.1f}%")
        print(f"    Grant (with conditions): {grant_cond:.1f}%")
        print(f"    Deny: {deny:.1f}%")
        print(f"    Unclear: {unclear:.1f}%")

    print("\nFinding contrasting examples...")
    examples = find_contrasting_examples(df)
    print(f"  Found {len(examples)} contrasting pairs")

    # Export results
    output_dir = project_root / "results" / "experiments" / "exp_20251028_134615" / "analysis"

    print("\nExporting content_analysis.json...")
    content_output = {
        "experiment_id": "exp_20251028_134615",
        "n_trials": len(trials),
        "decision_distribution": decision_counts.to_dict(),
        "chi_square_test": chi_sq_results,
        "proportions": proportions,
        "contrasting_examples": examples
    }

    with open(output_dir / "content_analysis.json", "w") as f:
        json.dump(content_output, f, indent=2)

    print(f"✓ Saved to {output_dir / 'content_analysis.json'}")
    print("\nContent analysis complete!")


if __name__ == "__main__":
    main()
