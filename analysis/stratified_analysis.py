#!/usr/bin/env python3
"""
Stratified Correlation Analysis (ENSEMBLE SUPPORT)
Phase 0.4 - Step 3: Calculate inter-evaluator score correlations within subgroups

Analyzes how consistently different evaluator models agree on scores across:
- Different constitutions
- Different scenarios
- Different scoring dimensions
- Different score ranges

Key Understanding:
- We have FIVE evaluators (claude, gpt-4o, deepseek, grok-3, gemini-2-5-pro)
- "Inter-evaluator correlation" measures: Do different judge models agree
  on the same Layer 2 reasoning?
- High correlation = evaluators agree on what constitutes good reasoning
"""

import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from scipy import stats
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import argparse
import sys

from data_loader import ExperimentDataLoader

@dataclass
class CorrelationResult:
    """Result of correlation analysis for a stratum."""
    stratum_name: str
    n_trials: int
    mean_correlation: float
    ci_lower: float
    ci_upper: float
    pairwise_correlations: Dict[str, float]
    evaluator_pairs_count: int

class StratifiedAnalyzer:
    """Analyze inter-evaluator score correlations within subgroups."""

    def __init__(self, experiment_id: str, exclude_evaluators: Optional[List[str]] = None):
        self.loader = ExperimentDataLoader(experiment_id)
        self.df = self.loader.get_trial_dataframe()

        # Filter out excluded evaluators (e.g., Gemini outlier)
        if exclude_evaluators:
            self.df = self.df[~self.df["evaluator"].isin(exclude_evaluators)]

        self.evaluators = sorted(self.df["evaluator"].unique())
        self.exclude_evaluators = exclude_evaluators or []

    def _calculate_pairwise_correlations(
        self,
        subset_df: pd.DataFrame,
        dimension: str = "overall_score"
    ) -> Dict[str, Tuple[float, int]]:
        """
        Calculate pairwise correlations between evaluators for a subset of trials.

        For each pair of evaluators, find trials where both evaluated the same
        Layer 2 reasoning and calculate correlation of their scores.

        Returns: {evaluator_pair: (correlation, n_pairs)}
        """

        correlations = {}

        for i, eval1 in enumerate(self.evaluators):
            for eval2 in self.evaluators[i+1:]:
                # Get scores from evaluator 1
                eval1_df = subset_df[subset_df["evaluator"] == eval1].copy()
                # Get scores from evaluator 2
                eval2_df = subset_df[subset_df["evaluator"] == eval2].copy()

                # Merge on trial_id to get paired scores (same trial, different evaluators)
                merged = eval1_df.merge(
                    eval2_df,
                    on=["trial_id"],
                    suffixes=("_e1", "_e2")
                )

                if len(merged) >= 10:  # Need at least 10 pairs for meaningful correlation
                    scores1 = merged[f"{dimension}_e1"]
                    scores2 = merged[f"{dimension}_e2"]

                    r, p = pearsonr(scores1, scores2)
                    pair_name = f"{eval1} vs {eval2}"
                    correlations[pair_name] = (r, len(merged))

        return correlations

    def _calculate_ci(self, r: float, n: int, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval for correlation using Fisher z-transform."""

        if n < 4:
            return (np.nan, np.nan)

        # Fisher z-transform
        z = np.arctanh(r)
        se = 1 / np.sqrt(n - 3)

        # Get critical value
        z_crit = stats.norm.ppf((1 + confidence) / 2)

        # Calculate CI in z-space
        ci_lower_z = z - z_crit * se
        ci_upper_z = z + z_crit * se

        # Transform back to r-space
        ci_lower = np.tanh(ci_lower_z)
        ci_upper = np.tanh(ci_upper_z)

        return (ci_lower, ci_upper)

    def analyze_by_constitution(self, dimension: str = "overall_score") -> Dict[str, CorrelationResult]:
        """
        Calculate inter-evaluator correlations separately for each constitution.

        Purpose: Identify if certain value systems cause more evaluator disagreement.
        Example: Does "bad-faith" constitution lead to lower inter-evaluator agreement?
        """

        results = {}

        for constitution in sorted(self.df["constitution"].unique()):
            subset = self.df[self.df["constitution"] == constitution]

            pairwise = self._calculate_pairwise_correlations(subset, dimension)

            if pairwise:
                correlations = [r for r, n in pairwise.values()]
                mean_r = np.mean(correlations)

                # Calculate CI for mean correlation (approximate)
                mean_n = np.mean([n for r, n in pairwise.values()])
                ci_lower, ci_upper = self._calculate_ci(mean_r, int(mean_n))

                results[constitution] = CorrelationResult(
                    stratum_name=constitution,
                    n_trials=len(subset),
                    mean_correlation=mean_r,
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
                    pairwise_correlations={k: v[0] for k, v in pairwise.items()},
                    evaluator_pairs_count=len(pairwise)
                )

        return results

    def analyze_by_scenario(self, dimension: str = "overall_score") -> Dict[str, CorrelationResult]:
        """
        Calculate inter-evaluator correlations separately for each scenario.

        Purpose: Identify if certain topics cause more evaluator disagreement.
        Example: Does "asylum-claim" scenario lead to lower agreement than "vaccine-mandate"?
        """

        results = {}

        for scenario in sorted(self.df["scenario_id"].unique()):
            subset = self.df[self.df["scenario_id"] == scenario]

            pairwise = self._calculate_pairwise_correlations(subset, dimension)

            if pairwise:
                correlations = [r for r, n in pairwise.values()]
                mean_r = np.mean(correlations)

                mean_n = np.mean([n for r, n in pairwise.values()])
                ci_lower, ci_upper = self._calculate_ci(mean_r, int(mean_n))

                results[scenario] = CorrelationResult(
                    stratum_name=scenario,
                    n_trials=len(subset),
                    mean_correlation=mean_r,
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
                    pairwise_correlations={k: v[0] for k, v in pairwise.items()},
                    evaluator_pairs_count=len(pairwise)
                )

        return results

    def analyze_by_dimension(self) -> Dict[str, CorrelationResult]:
        """
        Calculate inter-evaluator correlations separately for each scoring dimension.

        Purpose: Identify which dimensions show best evaluator agreement.
        Example: Do evaluators agree more on "epistemic_integrity" than "value_transparency"?
        """

        dimensions = ["epistemic_integrity", "value_transparency", "overall_score"]
        results = {}

        for dimension in dimensions:
            pairwise = self._calculate_pairwise_correlations(self.df, dimension)

            if pairwise:
                correlations = [r for r, n in pairwise.values()]
                mean_r = np.mean(correlations)

                mean_n = np.mean([n for r, n in pairwise.values()])
                ci_lower, ci_upper = self._calculate_ci(mean_r, int(mean_n))

                results[dimension] = CorrelationResult(
                    stratum_name=dimension,
                    n_trials=len(self.df),
                    mean_correlation=mean_r,
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
                    pairwise_correlations={k: v[0] for k, v in pairwise.items()},
                    evaluator_pairs_count=len(pairwise)
                )

        return results

    def analyze_by_score_range(self, dimension: str = "overall_score") -> Dict[str, CorrelationResult]:
        """
        Calculate inter-evaluator correlations separately for different score ranges.

        Purpose: Test if evaluator agreement is higher for clear cases (high/low scores).
        Hypothesis: Evaluators might agree more on obviously good/bad reasoning.
        """

        # Define ranges
        ranges = {
            "high (>90)": self.df[self.df[dimension] > 90],
            "mid (75-90)": self.df[(self.df[dimension] >= 75) & (self.df[dimension] <= 90)],
            "low (<75)": self.df[self.df[dimension] < 75]
        }

        results = {}

        for range_name, subset in ranges.items():
            if len(subset) < 20:  # Skip ranges with too few evaluations
                continue

            pairwise = self._calculate_pairwise_correlations(subset, dimension)

            if pairwise:
                correlations = [r for r, n in pairwise.values()]
                mean_r = np.mean(correlations)

                mean_n = np.mean([n for r, n in pairwise.values()])
                ci_lower, ci_upper = self._calculate_ci(mean_r, int(mean_n))

                results[range_name] = CorrelationResult(
                    stratum_name=range_name,
                    n_trials=len(subset),
                    mean_correlation=mean_r,
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
                    pairwise_correlations={k: v[0] for k, v in pairwise.items()},
                    evaluator_pairs_count=len(pairwise)
                )

        return results

    def print_results(self, results: Dict[str, CorrelationResult], title: str):
        """Pretty print correlation results."""

        print(f"\n=== {title} ===\n")

        for stratum, result in results.items():
            print(f"{result.stratum_name}:")
            print(f"  Evaluations: {result.n_trials}")
            print(f"  Mean correlation: r={result.mean_correlation:.3f}")
            print(f"  95% CI: [{result.ci_lower:.3f}, {result.ci_upper:.3f}]")
            print(f"  Evaluator pairs analyzed: {result.evaluator_pairs_count}")

            # Show top and bottom pairwise correlations
            sorted_pairs = sorted(result.pairwise_correlations.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_pairs) > 0:
                print(f"  Highest agreement: {sorted_pairs[0][0]}: r={sorted_pairs[0][1]:.3f}")
                print(f"  Lowest agreement: {sorted_pairs[-1][0]}: r={sorted_pairs[-1][1]:.3f}")
            print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stratified Correlation Analysis - Analyze inter-evaluator score correlations"
    )
    parser.add_argument(
        'experiment_id',
        type=str,
        help='Experiment ID to analyze (e.g., exp_20251028_095612)'
    )
    parser.add_argument(
        '--exclude-evaluators',
        type=str,
        nargs='+',
        help='Evaluator(s) to exclude from analysis (e.g., gemini-2-5-pro)'
    )

    args = parser.parse_args()

    # Test the stratified analyzer (ENSEMBLE SUPPORT)
    print("=== Stratified Analyzer (Inter-Evaluator Correlation) ===\n")

    try:
        # Test with specified evaluators
        analyzer = StratifiedAnalyzer(args.experiment_id, exclude_evaluators=args.exclude_evaluators)
        print(f"Experiment: {args.experiment_id}")
        print(f"Loaded {len(analyzer.df)} evaluations from {len(analyzer.evaluators)} evaluators")
        print(f"Evaluators: {analyzer.evaluators}")
        if args.exclude_evaluators:
            print(f"Excluded: {args.exclude_evaluators}")
        print()

        # Run all analyses
        print("Analyzing by constitution...")
        const_results = analyzer.analyze_by_constitution()
        analyzer.print_results(const_results, "Inter-Evaluator Correlation by Constitution")

        print("\nAnalyzing by scenario...")
        scenario_results = analyzer.analyze_by_scenario()
        analyzer.print_results(scenario_results, "Inter-Evaluator Correlation by Scenario")

        print("\nAnalyzing by dimension...")
        dimension_results = analyzer.analyze_by_dimension()
        analyzer.print_results(dimension_results, "Inter-Evaluator Correlation by Dimension")

        print("\nAnalyzing by score range...")
        range_results = analyzer.analyze_by_score_range()
        analyzer.print_results(range_results, "Inter-Evaluator Correlation by Score Range")

        print("\n✅ Stratified analysis complete!")

    except (FileNotFoundError, ValueError) as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        print(f"\nUsage: python3 analysis/stratified_analysis.py <experiment_id>", file=sys.stderr)
        print(f"Example: python3 analysis/stratified_analysis.py exp_20251028_095612", file=sys.stderr)
        sys.exit(1)
