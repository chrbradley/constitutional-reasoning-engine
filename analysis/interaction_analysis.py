#!/usr/bin/env python3
"""
Model × Constitution Interaction Analysis
Week 1, Task 3 (Analysis 1.2) of Analysis & Publication Plan

Tests whether certain models perform differently with certain constitutional frameworks.

Research Question: Do certain models excel with some value systems but struggle with others?

Answers Q3 from research roadmap directly.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import warnings

# Statistical packages
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.anova import anova_lm

warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class TrialData:
    """Data for one trial with consensus scores and metadata."""
    trial_id: str
    scenario_id: str
    constitution: str
    layer2_model: str
    epistemic_integrity: float
    value_transparency: float
    overall_score: float


class InteractionAnalyzer:
    """Analyze Model × Constitution interaction effects."""

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id

        # Find project root (handles running from notebooks/ or root)
        cwd = Path.cwd()
        if cwd.name == "notebooks":
            project_root = cwd.parent
        else:
            project_root = cwd

        self.exp_path = project_root / "results" / "experiments" / experiment_id
        self.consensus_file = self.exp_path / "analysis" / "consensus_scores.json"
        self.layer2_dir = self.exp_path / "data" / "layer2"

        if not self.consensus_file.exists():
            raise FileNotFoundError(
                f"Consensus scores not found: {self.consensus_file}\n"
                f"Run evaluator_agreement.py first to generate consensus scores."
            )

        if not self.layer2_dir.exists():
            raise FileNotFoundError(
                f"Layer 2 directory not found: {self.layer2_dir}\n"
                f"This analysis requires Layer 2 trial data for metadata."
            )

    def load_consensus_scores(self) -> Dict:
        """Load consensus scores from Analysis 1.3."""
        with open(self.consensus_file) as f:
            return json.load(f)

    def load_trial_metadata(self, trial_id: str) -> Tuple[str, str, str]:
        """Load trial metadata from Layer 2 file."""
        layer2_file = self.layer2_dir / f"{trial_id}.json"

        if not layer2_file.exists():
            return None, None, None

        with open(layer2_file) as f:
            data = json.load(f)

        return (
            data.get("scenario_id", "unknown"),
            data.get("constitution", "unknown"),
            data.get("model", "unknown")
        )

    def build_dataframe(self, consensus_method: str = "mean_all") -> pd.DataFrame:
        """
        Build dataframe with trial data and consensus scores.

        Args:
            consensus_method: Which consensus method to use (mean_all, median_all, etc.)

        Returns:
            DataFrame with columns: trial_id, scenario_id, constitution, layer2_model,
                                   epistemic_integrity, value_transparency, overall_score
        """

        consensus_data = self.load_consensus_scores()
        trials = []

        for trial_consensus in consensus_data["consensus_scores"]:
            trial_id = trial_consensus["trial_id"]

            # Load metadata
            scenario_id, constitution, layer2_model = self.load_trial_metadata(trial_id)

            if constitution == "unknown" or layer2_model == "unknown":
                print(f"Warning: Missing metadata for {trial_id}, skipping")
                continue

            # Get consensus scores
            scores = trial_consensus[consensus_method]

            trials.append(TrialData(
                trial_id=trial_id,
                scenario_id=scenario_id,
                constitution=constitution,
                layer2_model=layer2_model,
                epistemic_integrity=scores.get("epistemic_integrity", np.nan),
                value_transparency=scores.get("value_transparency", np.nan),
                overall_score=scores.get("overall_score", np.nan)
            ))

        df = pd.DataFrame([vars(t) for t in trials])

        # Remove trials with missing scores
        df = df.dropna(subset=["epistemic_integrity", "value_transparency", "overall_score"])

        print(f"Loaded {len(df)} trials with complete data")
        print(f"  Constitutions: {sorted(df['constitution'].unique())}")
        print(f"  Models: {sorted(df['layer2_model'].unique())}")

        return df

    def calculate_cell_means(
        self,
        df: pd.DataFrame,
        dimension: str = "overall_score"
    ) -> pd.DataFrame:
        """
        Calculate mean scores for each Model × Constitution cell.

        Returns:
            Pivot table with models as rows, constitutions as columns
        """

        pivot = df.pivot_table(
            values=dimension,
            index="layer2_model",
            columns="constitution",
            aggfunc="mean"
        )

        return pivot

    def two_way_anova(
        self,
        df: pd.DataFrame,
        dimension: str = "overall_score"
    ) -> Dict:
        """
        Run two-way ANOVA to test Model × Constitution interaction.

        Returns:
            Dict with ANOVA results, effect sizes, and interpretation
        """

        # Prepare data for ANOVA
        anova_df = df[["layer2_model", "constitution", dimension]].copy()
        anova_df = anova_df.dropna()

        # Build formula
        formula = f'{dimension} ~ C(layer2_model) + C(constitution) + C(layer2_model):C(constitution)'

        # Fit model
        model = ols(formula, data=anova_df).fit()

        # Run ANOVA
        anova_table = anova_lm(model, typ=2)

        # Calculate effect sizes (eta-squared)
        anova_table['eta_sq'] = anova_table['sum_sq'] / anova_table['sum_sq'].sum()

        # Extract key statistics
        results = {
            "n_observations": len(anova_df),
            "n_models": anova_df["layer2_model"].nunique(),
            "n_constitutions": anova_df["constitution"].nunique(),
            "dimension": dimension,
            "anova_table": {
                "model_effect": {
                    "F": float(anova_table.loc["C(layer2_model)", "F"]),
                    "p": float(anova_table.loc["C(layer2_model)", "PR(>F)"]),
                    "eta_sq": float(anova_table.loc["C(layer2_model)", "eta_sq"]),
                    "df": int(anova_table.loc["C(layer2_model)", "df"])
                },
                "constitution_effect": {
                    "F": float(anova_table.loc["C(constitution)", "F"]),
                    "p": float(anova_table.loc["C(constitution)", "PR(>F)"]),
                    "eta_sq": float(anova_table.loc["C(constitution)", "eta_sq"]),
                    "df": int(anova_table.loc["C(constitution)", "df"])
                },
                "interaction_effect": {
                    "F": float(anova_table.loc["C(layer2_model):C(constitution)", "F"]),
                    "p": float(anova_table.loc["C(layer2_model):C(constitution)", "PR(>F)"]),
                    "eta_sq": float(anova_table.loc["C(layer2_model):C(constitution)", "eta_sq"]),
                    "df": int(anova_table.loc["C(layer2_model):C(constitution)", "df"])
                },
                "residual": {
                    "df": int(anova_table.loc["Residual", "df"])
                }
            },
            "model_r_squared": float(model.rsquared),
            "adjusted_r_squared": float(model.rsquared_adj)
        }

        # Interpretation
        interaction_p = results["anova_table"]["interaction_effect"]["p"]
        model_p = results["anova_table"]["model_effect"]["p"]
        constitution_p = results["anova_table"]["constitution_effect"]["p"]

        results["interpretation"] = {
            "interaction_significant": interaction_p < 0.05,
            "model_effect_significant": model_p < 0.05,
            "constitution_effect_significant": constitution_p < 0.05,
            "interaction_strength": self._interpret_eta_squared(
                results["anova_table"]["interaction_effect"]["eta_sq"]
            ),
            "model_strength": self._interpret_eta_squared(
                results["anova_table"]["model_effect"]["eta_sq"]
            ),
            "constitution_strength": self._interpret_eta_squared(
                results["anova_table"]["constitution_effect"]["eta_sq"]
            )
        }

        return results

    def _interpret_eta_squared(self, eta_sq: float) -> str:
        """Interpret eta-squared effect size (Cohen's guidelines)."""
        if eta_sq < 0.01:
            return "negligible"
        elif eta_sq < 0.06:
            return "small"
        elif eta_sq < 0.14:
            return "medium"
        else:
            return "large"

    def post_hoc_tukey(
        self,
        df: pd.DataFrame,
        dimension: str = "overall_score"
    ) -> Dict:
        """
        Run Tukey HSD post-hoc tests for pairwise comparisons.

        Returns:
            Dict with Tukey results for models and constitutions
        """

        results = {}

        # Tukey HSD for models
        tukey_models = pairwise_tukeyhsd(
            endog=df[dimension],
            groups=df["layer2_model"],
            alpha=0.05
        )

        results["models"] = {
            "summary": str(tukey_models),
            "significant_pairs": []
        }

        for i, (group1, group2, meandiff, p_adj, lower, upper, reject) in enumerate(tukey_models.summary().data[1:]):
            if reject:
                results["models"]["significant_pairs"].append({
                    "group1": group1,
                    "group2": group2,
                    "mean_diff": float(meandiff),
                    "p_adj": float(p_adj),
                    "ci_lower": float(lower),
                    "ci_upper": float(upper)
                })

        # Tukey HSD for constitutions
        tukey_constitutions = pairwise_tukeyhsd(
            endog=df[dimension],
            groups=df["constitution"],
            alpha=0.05
        )

        results["constitutions"] = {
            "summary": str(tukey_constitutions),
            "significant_pairs": []
        }

        for i, (group1, group2, meandiff, p_adj, lower, upper, reject) in enumerate(tukey_constitutions.summary().data[1:]):
            if reject:
                results["constitutions"]["significant_pairs"].append({
                    "group1": group1,
                    "group2": group2,
                    "mean_diff": float(meandiff),
                    "p_adj": float(p_adj),
                    "ci_lower": float(lower),
                    "ci_upper": float(upper)
                })

        return results

    def simple_effects_analysis(
        self,
        df: pd.DataFrame,
        dimension: str = "overall_score"
    ) -> Dict:
        """
        Analyze simple effects: How does each model perform across constitutions?

        Returns:
            Dict with per-model statistics across constitutions
        """

        results = {}

        for model in sorted(df["layer2_model"].unique()):
            model_df = df[df["layer2_model"] == model]

            # Calculate mean score per constitution
            const_means = model_df.groupby("constitution")[dimension].agg(["mean", "std", "count"])

            # One-way ANOVA: Do constitutions differ for this model?
            groups = [model_df[model_df["constitution"] == const][dimension].values
                     for const in model_df["constitution"].unique()]

            if len(groups) > 1 and all(len(g) > 0 for g in groups):
                f_stat, p_value = stats.f_oneway(*groups)

                results[model] = {
                    "constitution_means": const_means.to_dict(),
                    "anova_F": float(f_stat),
                    "anova_p": float(p_value),
                    "range": float(const_means["mean"].max() - const_means["mean"].min()),
                    "best_constitution": const_means["mean"].idxmax(),
                    "worst_constitution": const_means["mean"].idxmin(),
                    "constitutions_differ": p_value < 0.05
                }

        return results

    def analyze(self, consensus_method: str = "mean_all") -> Dict:
        """
        Run complete Model × Constitution interaction analysis.

        Returns:
            Dict with all analysis results
        """

        print("="*70)
        print("MODEL × CONSTITUTION INTERACTION ANALYSIS")
        print(f"Experiment: {self.experiment_id}")
        print(f"Consensus Method: {consensus_method}")
        print("="*70)

        # Load data
        print("\nLoading data...")
        df = self.build_dataframe(consensus_method)

        results = {
            "experiment_id": self.experiment_id,
            "consensus_method": consensus_method,
            "n_trials": len(df),
            "n_models": df["layer2_model"].nunique(),
            "n_constitutions": df["constitution"].nunique(),
            "dimensions": {}
        }

        # Analyze each dimension
        for dimension in ["epistemic_integrity", "value_transparency", "overall_score"]:
            print(f"\n{'='*70}")
            print(f"Dimension: {dimension.replace('_', ' ').title()}")
            print('='*70)

            dim_results = {}

            # Cell means
            print("\n--- Cell Means (Model × Constitution) ---")
            cell_means = self.calculate_cell_means(df, dimension)
            print(cell_means.round(2))

            dim_results["cell_means"] = cell_means.to_dict()

            # Two-way ANOVA
            print("\n--- Two-Way ANOVA ---")
            anova_results = self.two_way_anova(df, dimension)

            print(f"\nMain Effect: Model")
            print(f"  F({anova_results['anova_table']['model_effect']['df']}, "
                  f"{anova_results['anova_table']['residual']['df']}) = "
                  f"{anova_results['anova_table']['model_effect']['F']:.3f}, "
                  f"p = {anova_results['anova_table']['model_effect']['p']:.6f}")
            print(f"  η² = {anova_results['anova_table']['model_effect']['eta_sq']:.3f} "
                  f"({anova_results['interpretation']['model_strength']} effect)")

            print(f"\nMain Effect: Constitution")
            print(f"  F({anova_results['anova_table']['constitution_effect']['df']}, "
                  f"{anova_results['anova_table']['residual']['df']}) = "
                  f"{anova_results['anova_table']['constitution_effect']['F']:.3f}, "
                  f"p = {anova_results['anova_table']['constitution_effect']['p']:.6f}")
            print(f"  η² = {anova_results['anova_table']['constitution_effect']['eta_sq']:.3f} "
                  f"({anova_results['interpretation']['constitution_strength']} effect)")

            print(f"\nInteraction Effect: Model × Constitution")
            print(f"  F({anova_results['anova_table']['interaction_effect']['df']}, "
                  f"{anova_results['anova_table']['residual']['df']}) = "
                  f"{anova_results['anova_table']['interaction_effect']['F']:.3f}, "
                  f"p = {anova_results['anova_table']['interaction_effect']['p']:.6f}")
            print(f"  η² = {anova_results['anova_table']['interaction_effect']['eta_sq']:.3f} "
                  f"({anova_results['interpretation']['interaction_strength']} effect)")

            if anova_results['interpretation']['interaction_significant']:
                print("\n  ✅ SIGNIFICANT INTERACTION DETECTED")
                print("     Different models perform differently across constitutions!")
            else:
                print("\n  ❌ No significant interaction")
                print("     Models perform consistently across constitutions")

            dim_results["anova"] = anova_results

            # Post-hoc tests
            print("\n--- Post-Hoc Tests (Tukey HSD) ---")
            tukey_results = self.post_hoc_tukey(df, dimension)

            print(f"\nSignificant Model Differences: {len(tukey_results['models']['significant_pairs'])}")
            for pair in tukey_results['models']['significant_pairs'][:5]:  # Show top 5
                print(f"  {pair['group1']:20} vs {pair['group2']:20}: "
                      f"Δ={pair['mean_diff']:+6.2f}, p={pair['p_adj']:.4f}")

            print(f"\nSignificant Constitution Differences: {len(tukey_results['constitutions']['significant_pairs'])}")
            for pair in tukey_results['constitutions']['significant_pairs'][:5]:  # Show top 5
                print(f"  {pair['group1']:20} vs {pair['group2']:20}: "
                      f"Δ={pair['mean_diff']:+6.2f}, p={pair['p_adj']:.4f}")

            dim_results["post_hoc"] = tukey_results

            # Simple effects
            print("\n--- Simple Effects Analysis (Per-Model) ---")
            simple_effects = self.simple_effects_analysis(df, dimension)

            for model, stats_dict in sorted(simple_effects.items()):
                print(f"\n{model}:")
                print(f"  Range: {stats_dict['range']:.2f} points "
                      f"({stats_dict['worst_constitution']} → {stats_dict['best_constitution']})")
                print(f"  Constitution effect: F={stats_dict['anova_F']:.2f}, p={stats_dict['anova_p']:.4f}")
                if stats_dict['constitutions_differ']:
                    print(f"  ✅ Constitutions significantly differ for this model")
                else:
                    print(f"  ❌ Constitutions do not differ significantly")

            dim_results["simple_effects"] = simple_effects

            results["dimensions"][dimension] = dim_results

        return results


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analysis/interaction_analysis.py <experiment_id>")
        print("\nExample: python analysis/interaction_analysis.py exp_20251028_134615")
        sys.exit(1)

    experiment_id = sys.argv[1]

    analyzer = InteractionAnalyzer(experiment_id)
    results = analyzer.analyze(consensus_method="mean_all")

    # Convert numpy types to native Python types
    results = convert_numpy_types(results)

    # Save results
    output_dir = Path("results/experiments") / experiment_id / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "interaction_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
