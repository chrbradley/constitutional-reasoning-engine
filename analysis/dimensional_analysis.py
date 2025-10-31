#!/usr/bin/env python3
"""
Dimensional Structure Validation Analysis
Week 1, Task 4 (Analysis 1.4) of Analysis & Publication Plan

Tests whether Epistemic Integrity and Value Transparency are independent dimensions
or if they're redundant (highly correlated).

Research Question: Is the 2-dimensional rubric design justified?

Target: r < 0.60 (dimensions should be relatively independent)
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
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class TrialScores:
    """Scores for one trial with both dimensions."""
    trial_id: str
    epistemic_integrity: float
    value_transparency: float
    overall_score: float


class DimensionalAnalyzer:
    """Analyze independence of scoring dimensions."""

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id

        # Find project root
        cwd = Path.cwd()
        if cwd.name == "notebooks":
            project_root = cwd.parent
        else:
            project_root = cwd

        self.exp_path = project_root / "results" / "experiments" / experiment_id
        self.likert_dir = self.exp_path / "data" / "layer3"

        if not self.likert_dir.exists():
            raise FileNotFoundError(
                f"Likert directory not found: {self.likert_dir}\n"
                f"This analysis requires Likert rubric data (layer3/)."
            )

        self.evaluators = [
            "claude-sonnet-4-5",
            "gpt-4o",
            "gemini-2-5-pro",
            "grok-3",
            "deepseek-chat"
        ]

    def load_trial(self, trial_id: str) -> Dict:
        """Load trial with all evaluator scores."""
        trial_file = self.likert_dir / f"{trial_id}.json"

        if not trial_file.exists():
            raise FileNotFoundError(f"Trial not found: {trial_id}")

        with open(trial_file) as f:
            data = json.load(f)

        return data

    def build_dataframe(self) -> pd.DataFrame:
        """
        Build dataframe with trial scores from all evaluators.

        Returns:
            DataFrame with columns: trial_id, evaluator, epistemic_integrity,
                                   value_transparency, overall_score
        """

        trials = []
        trial_files = sorted(self.likert_dir.glob("trial_*.json"))

        for trial_file in trial_files:
            trial_id = trial_file.stem

            try:
                data = self.load_trial(trial_id)

                for evaluator_name, eval_data in data.get("evaluations", {}).items():
                    if eval_data.get("status") == "completed" and eval_data.get("response_parsed"):
                        parsed = eval_data["response_parsed"]

                        trials.append({
                            "trial_id": trial_id,
                            "evaluator": evaluator_name,
                            "epistemic_integrity": parsed["epistemicIntegrity"]["score"],
                            "value_transparency": parsed["valueTransparency"]["score"],
                            "overall_score": parsed["overallScore"]
                        })

            except Exception as e:
                print(f"Warning: Failed to load {trial_id}: {e}")
                continue

        df = pd.DataFrame(trials)
        df = df.dropna(subset=["epistemic_integrity", "value_transparency", "overall_score"])

        print(f"Loaded {len(df)} evaluations from {df['trial_id'].nunique()} trials")

        return df

    def calculate_dimensional_correlation(
        self,
        df: pd.DataFrame,
        evaluator: str = None
    ) -> Dict:
        """
        Calculate correlation between Epistemic Integrity and Value Transparency.

        Args:
            df: DataFrame with scores
            evaluator: If specified, calculate for specific evaluator only

        Returns:
            Dict with correlation statistics
        """

        if evaluator:
            df_subset = df[df["evaluator"] == evaluator].copy()
        else:
            df_subset = df.copy()

        if len(df_subset) < 10:
            return {
                "n": len(df_subset),
                "r": np.nan,
                "p": np.nan,
                "ci_lower": np.nan,
                "ci_upper": np.nan
            }

        # Calculate Pearson correlation
        r, p = stats.pearsonr(
            df_subset["epistemic_integrity"],
            df_subset["value_transparency"]
        )

        # Calculate 95% confidence interval using Fisher z-transformation
        n = len(df_subset)
        z = np.arctanh(r)
        se = 1 / np.sqrt(n - 3)
        ci_lower_z = z - 1.96 * se
        ci_upper_z = z + 1.96 * se
        ci_lower = np.tanh(ci_lower_z)
        ci_upper = np.tanh(ci_upper_z)

        return {
            "n": n,
            "r": float(r),
            "p": float(p),
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper)
        }

    def calculate_per_evaluator_correlations(self, df: pd.DataFrame) -> Dict:
        """Calculate dimensional correlations for each evaluator."""

        results = {}

        for evaluator in self.evaluators:
            eval_df = df[df["evaluator"] == evaluator]

            if len(eval_df) < 10:
                print(f"Warning: Insufficient data for {evaluator}")
                continue

            corr_stats = self.calculate_dimensional_correlation(df, evaluator)
            results[evaluator] = corr_stats

        return results

    def perform_pca(self, df: pd.DataFrame) -> Dict:
        """
        Perform PCA to test if 2 dimensions capture variance.

        Returns:
            Dict with PCA results including variance explained
        """

        # Prepare data: Use mean scores per trial (aggregate across evaluators)
        trial_means = df.groupby("trial_id")[["epistemic_integrity", "value_transparency"]].mean()

        # Standardize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(trial_means)

        # Fit PCA
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        # Calculate variance explained
        variance_explained = pca.explained_variance_ratio_
        cumulative_variance = np.cumsum(variance_explained)

        # Loadings (how much each original dimension contributes to each PC)
        loadings = pca.components_

        return {
            "n_trials": len(trial_means),
            "variance_explained": {
                "PC1": float(variance_explained[0]),
                "PC2": float(variance_explained[1]),
                "cumulative": float(cumulative_variance[1])
            },
            "loadings": {
                "PC1": {
                    "epistemic_integrity": float(loadings[0, 0]),
                    "value_transparency": float(loadings[0, 1])
                },
                "PC2": {
                    "epistemic_integrity": float(loadings[1, 0]),
                    "value_transparency": float(loadings[1, 1])
                }
            },
            "interpretation": self._interpret_pca(variance_explained, loadings)
        }

    def _interpret_pca(self, variance_explained: np.ndarray, loadings: np.ndarray) -> Dict:
        """Interpret PCA results."""

        pc1_var = variance_explained[0]
        pc2_var = variance_explained[1]
        cumulative = np.sum(variance_explained)

        # Check if PC1 dominates (suggests dimensions are redundant)
        pc1_dominant = pc1_var > 0.80

        # Check loadings to see if dimensions separate
        pc1_loadings = np.abs(loadings[0])
        dimensions_separate = (np.max(pc1_loadings) - np.min(pc1_loadings)) > 0.3

        return {
            "pc1_dominant": bool(pc1_dominant),
            "dimensions_separate": bool(dimensions_separate),
            "cumulative_variance_captured": float(cumulative),
            "interpretation": self._generate_interpretation(pc1_var, cumulative, dimensions_separate)
        }

    def _generate_interpretation(self, pc1_var: float, cumulative: float, dimensions_separate: bool) -> str:
        """Generate text interpretation of PCA."""

        if pc1_var > 0.80 and not dimensions_separate:
            return "Dimensions are highly correlated (redundant). PC1 captures most variance."
        elif pc1_var > 0.70 and dimensions_separate:
            return "Dimensions are correlated but distinguishable. PC1 dominant but PC2 contributes."
        elif cumulative > 0.90:
            return "Two dimensions capture >90% variance. 2D structure justified."
        else:
            return "Dimensions appear independent. More than 2 factors may be present."

    def test_dimensional_independence(self, df: pd.DataFrame) -> Dict:
        """
        Test if dimensions are sufficiently independent.

        Target: r < 0.60 (Cohen's threshold for "not redundant")

        Returns:
            Dict with independence test results
        """

        # Overall correlation
        overall_corr = self.calculate_dimensional_correlation(df)

        # Per-evaluator correlations
        per_evaluator = self.calculate_per_evaluator_correlations(df)

        # Average correlation across evaluators
        valid_corrs = [stats["r"] for stats in per_evaluator.values() if not np.isnan(stats["r"])]
        mean_r = np.mean(valid_corrs) if valid_corrs else np.nan

        # Independence test
        threshold = 0.60
        independent = overall_corr["r"] < threshold

        return {
            "threshold": threshold,
            "overall_correlation": overall_corr,
            "mean_evaluator_correlation": float(mean_r),
            "per_evaluator": per_evaluator,
            "dimensions_independent": independent,
            "interpretation": self._interpret_independence(overall_corr["r"], threshold)
        }

    def _interpret_independence(self, r: float, threshold: float) -> str:
        """Interpret dimensional independence."""

        if np.isnan(r):
            return "Insufficient data to assess independence"
        elif r < 0.30:
            return "Dimensions are weakly correlated (highly independent)"
        elif r < threshold:
            return "Dimensions are moderately correlated but sufficiently independent"
        elif r < 0.80:
            return "Dimensions are highly correlated (some redundancy)"
        else:
            return "Dimensions are very highly correlated (likely redundant)"

    def identify_dimension_conflaters(self, df: pd.DataFrame) -> List[str]:
        """
        Identify evaluators who conflate dimensions (r > 0.70).

        Returns:
            List of evaluator names who show high dimensional correlation
        """

        per_evaluator = self.calculate_per_evaluator_correlations(df)

        conflaters = []
        for evaluator, stats in per_evaluator.items():
            if not np.isnan(stats["r"]) and stats["r"] > 0.70:
                conflaters.append(evaluator)

        return conflaters

    def analyze(self) -> Dict:
        """
        Run complete dimensional structure validation analysis.

        Returns:
            Dict with all analysis results
        """

        print("="*70)
        print("DIMENSIONAL STRUCTURE VALIDATION ANALYSIS")
        print(f"Experiment: {self.experiment_id}")
        print("="*70)

        # Load data
        print("\nLoading data...")
        df = self.build_dataframe()

        results = {
            "experiment_id": self.experiment_id,
            "n_evaluations": len(df),
            "n_trials": df["trial_id"].nunique(),
            "n_evaluators": df["evaluator"].nunique()
        }

        # Test dimensional independence
        print("\n" + "="*70)
        print("DIMENSIONAL INDEPENDENCE TEST")
        print("="*70)

        independence = self.test_dimensional_independence(df)

        print(f"\nOverall Correlation (Epistemic Integrity × Value Transparency):")
        print(f"  Pearson r: {independence['overall_correlation']['r']:.3f}")
        print(f"  95% CI: [{independence['overall_correlation']['ci_lower']:.3f}, "
              f"{independence['overall_correlation']['ci_upper']:.3f}]")
        print(f"  p-value: {independence['overall_correlation']['p']:.6f}")
        print(f"  n: {independence['overall_correlation']['n']}")

        print(f"\nIndependence Threshold: r < {independence['threshold']:.2f}")
        if independence['dimensions_independent']:
            print(f"  ✅ PASS: Dimensions are sufficiently independent (r={independence['overall_correlation']['r']:.3f})")
        else:
            print(f"  ❌ FAIL: Dimensions are too correlated (r={independence['overall_correlation']['r']:.3f})")

        print(f"\nInterpretation: {independence['interpretation']}")

        results["independence_test"] = independence

        # Per-evaluator correlations
        print("\n" + "="*70)
        print("PER-EVALUATOR DIMENSIONAL CORRELATIONS")
        print("="*70)

        print("\nEvaluator-specific correlations:")
        for evaluator, stats in sorted(independence["per_evaluator"].items(),
                                      key=lambda x: x[1]["r"], reverse=True):
            if not np.isnan(stats["r"]):
                warning = " ⚠️ HIGH" if stats["r"] > 0.70 else ""
                print(f"  {evaluator:25} r={stats['r']:5.3f} (95% CI: [{stats['ci_lower']:5.3f}, {stats['ci_upper']:5.3f}]){warning}")

        # Identify conflaters
        conflaters = self.identify_dimension_conflaters(df)
        print(f"\nEvaluators conflating dimensions (r > 0.70): {len(conflaters)}")
        if conflaters:
            for evaluator in conflaters:
                print(f"  ⚠️ {evaluator}")
        else:
            print("  ✅ None - all evaluators distinguish dimensions adequately")

        results["dimension_conflaters"] = conflaters

        # PCA Analysis
        print("\n" + "="*70)
        print("PRINCIPAL COMPONENT ANALYSIS")
        print("="*70)

        pca_results = self.perform_pca(df)

        print(f"\nVariance Explained:")
        print(f"  PC1: {pca_results['variance_explained']['PC1']*100:.1f}%")
        print(f"  PC2: {pca_results['variance_explained']['PC2']*100:.1f}%")
        print(f"  Cumulative: {pca_results['variance_explained']['cumulative']*100:.1f}%")

        print(f"\nPC1 Loadings:")
        print(f"  Epistemic Integrity: {pca_results['loadings']['PC1']['epistemic_integrity']:+.3f}")
        print(f"  Value Transparency:  {pca_results['loadings']['PC1']['value_transparency']:+.3f}")

        print(f"\nPC2 Loadings:")
        print(f"  Epistemic Integrity: {pca_results['loadings']['PC2']['epistemic_integrity']:+.3f}")
        print(f"  Value Transparency:  {pca_results['loadings']['PC2']['value_transparency']:+.3f}")

        print(f"\nInterpretation: {pca_results['interpretation']['interpretation']}")

        if pca_results['variance_explained']['cumulative'] > 0.90:
            print(f"  ✅ Two dimensions capture {pca_results['variance_explained']['cumulative']*100:.1f}% variance")
            print(f"     2D rubric design is justified")
        else:
            print(f"  ⚠️ Two dimensions capture only {pca_results['variance_explained']['cumulative']*100:.1f}% variance")
            print(f"     Additional dimensions may be present")

        results["pca"] = pca_results

        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)

        print("\n1. DIMENSIONAL INDEPENDENCE:")
        if independence['dimensions_independent']:
            print("   ✅ Dimensions are sufficiently independent (2D rubric justified)")
        else:
            print("   ⚠️ Dimensions show moderate-to-high correlation (some redundancy)")

        print(f"\n2. PCA VALIDATION:")
        if pca_results['variance_explained']['cumulative'] > 0.90:
            print("   ✅ Two dimensions capture >90% variance (2D structure confirmed)")
        else:
            print("   ⚠️ Two dimensions explain less variance (consider additional factors)")

        print(f"\n3. EVALUATOR CONSISTENCY:")
        if len(conflaters) == 0:
            print("   ✅ All evaluators distinguish dimensions adequately (no conflation)")
        else:
            print(f"   ⚠️ {len(conflaters)} evaluator(s) conflate dimensions (r > 0.70)")

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
        print("Usage: python analysis/dimensional_analysis.py <experiment_id>")
        print("\nExample: python analysis/dimensional_analysis.py exp_20251028_134615")
        sys.exit(1)

    experiment_id = sys.argv[1]

    analyzer = DimensionalAnalyzer(experiment_id)
    results = analyzer.analyze()

    # Convert numpy types
    results = convert_numpy_types(results)

    # Save results
    output_dir = Path("results/experiments") / experiment_id / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "dimensional_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
