#!/usr/bin/env python3
"""
Dimensionality Analysis (ENSEMBLE SUPPORT)
Phase 0.4 - Step 5: Check if 3 scoring dimensions are distinct or redundant

Analyzes whether factual_adherence, value_transparency, and logical_coherence
are measuring different constructs or are highly correlated (redundant).

Uses CONSENSUS SCORES (mean across evaluators for each trial) to avoid
artificial inflation of correlations due to evaluator-specific patterns.

Methods:
1. Inter-dimension correlation matrix
2. Principal Component Analysis (PCA)
3. Assessment of dimensionality
"""

import pandas as pd
import numpy as np
from scipy.stats import pearsonr
from scipy import linalg
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass

from data_loader import ExperimentDataLoader

@dataclass
class PCAResult:
    """Results from Principal Component Analysis."""
    n_components: int
    variance_explained: np.ndarray  # % variance per component
    cumulative_variance: np.ndarray
    loadings: np.ndarray  # Component loadings on original dimensions
    components_for_90pct: int  # How many components needed for 90% variance

@dataclass
class DimensionalityAssessment:
    """Overall assessment of dimensionality."""
    status: str  # "DISTINCT", "PARTIALLY_REDUNDANT", or "REDUNDANT"
    dimension_correlations: pd.DataFrame
    pca_result: PCAResult
    interpretation: str

class DimensionalityAnalyzer:
    """Analyze whether scoring dimensions are distinct or redundant (using consensus)."""

    def __init__(self, experiment_id: str = "exp_20251026_193228", exclude_evaluators: Optional[List[str]] = None):
        self.loader = ExperimentDataLoader(experiment_id)
        df_full = self.loader.get_trial_dataframe()

        # Filter out excluded evaluators (e.g., Gemini outlier)
        if exclude_evaluators:
            df_full = df_full[~df_full["evaluator"].isin(exclude_evaluators)]

        self.exclude_evaluators = exclude_evaluators or []

        # Calculate consensus scores (mean across evaluators for each trial)
        self.dimensions = ["factual_adherence", "value_transparency", "logical_coherence"]
        consensus_data = []

        for trial_id in df_full["trial_id"].unique():
            trial_subset = df_full[df_full["trial_id"] == trial_id]

            consensus_row = {
                "trial_id": trial_id,
                "scenario_id": trial_subset.iloc[0]["scenario_id"],
                "constitution": trial_subset.iloc[0]["constitution"],
                "layer2_model": trial_subset.iloc[0]["layer2_model"],
            }

            # Calculate mean score across evaluators for each dimension
            for dim in self.dimensions + ["overall_score"]:
                consensus_row[dim] = trial_subset[dim].mean()

            consensus_data.append(consensus_row)

        self.df = pd.DataFrame(consensus_data)  # Use consensus for analysis (120 trials)

    def calculate_dimension_correlations(self) -> pd.DataFrame:
        """
        Calculate correlation matrix between dimensions.

        Returns DataFrame with pairwise correlations and p-values.
        """

        # Create correlation matrix
        corr_matrix = pd.DataFrame(
            index=self.dimensions,
            columns=self.dimensions,
            dtype=float
        )

        # Calculate pairwise correlations
        for i, dim1 in enumerate(self.dimensions):
            for j, dim2 in enumerate(self.dimensions):
                if i == j:
                    corr_matrix.loc[dim1, dim2] = 1.0
                elif i < j:
                    r, p = pearsonr(self.df[dim1], self.df[dim2])
                    corr_matrix.loc[dim1, dim2] = r
                    corr_matrix.loc[dim2, dim1] = r  # Symmetric

        return corr_matrix

    def run_pca(self) -> PCAResult:
        """
        Run Principal Component Analysis on the 3 dimensions.

        Returns: PCAResult with variance explained and loadings.

        Implementation: Manual PCA using numpy/scipy (no sklearn dependency)
        """

        # Extract dimension scores and standardize
        X = self.df[self.dimensions].values
        X_centered = X - X.mean(axis=0)
        X_std = X_centered / X_centered.std(axis=0)

        # Compute covariance matrix
        cov_matrix = np.cov(X_std.T)

        # Eigendecomposition
        eigenvalues, eigenvectors = linalg.eigh(cov_matrix)

        # Sort by eigenvalues (descending)
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Calculate variance explained
        total_variance = eigenvalues.sum()
        variance_explained = eigenvalues / total_variance
        cumulative_variance = np.cumsum(variance_explained)

        # Determine components needed for 90% variance
        components_for_90 = np.argmax(cumulative_variance >= 0.90) + 1

        return PCAResult(
            n_components=3,
            variance_explained=variance_explained,
            cumulative_variance=cumulative_variance,
            loadings=eigenvectors.T,  # Transpose to match sklearn convention
            components_for_90pct=components_for_90
        )

    def assess_dimensionality(self) -> DimensionalityAssessment:
        """
        Assess whether dimensions are distinct, partially redundant, or redundant.

        Criteria:
        - DISTINCT: r < 0.60 between dimensions, need 3 components for 90% variance
        - PARTIALLY_REDUNDANT: r = 0.60-0.80, need 2 components for 85%+ variance
        - REDUNDANT: r > 0.85, 1 component explains >80% variance
        """

        corr_matrix = self.calculate_dimension_correlations()
        pca_result = self.run_pca()

        # Get off-diagonal correlations (ignore diagonal 1.0s)
        off_diagonal = []
        for i in range(len(self.dimensions)):
            for j in range(i+1, len(self.dimensions)):
                off_diagonal.append(corr_matrix.iloc[i, j])

        max_corr = max(off_diagonal)
        mean_corr = np.mean(off_diagonal)

        # Assess status
        if max_corr > 0.85 and pca_result.components_for_90pct == 1:
            status = "REDUNDANT"
            interpretation = (
                f"Dimensions are highly redundant. Maximum correlation: {max_corr:.3f}. "
                f"Only 1 component needed for 90% variance. "
                f"Consider collapsing to a single dimension or redesigning rubric."
            )
        elif max_corr > 0.60 and pca_result.components_for_90pct <= 2:
            status = "PARTIALLY_REDUNDANT"
            interpretation = (
                f"Dimensions are partially redundant. Maximum correlation: {max_corr:.3f}. "
                f"{pca_result.components_for_90pct} components needed for 90% variance. "
                f"Dimensions capture related but distinct aspects. May combine 2 of 3 dimensions."
            )
        else:
            status = "DISTINCT"
            interpretation = (
                f"Dimensions are distinct. Maximum correlation: {max_corr:.3f} (below 0.60). "
                f"{pca_result.components_for_90pct} components needed for 90% variance. "
                f"All 3 dimensions are justified and capture different aspects."
            )

        return DimensionalityAssessment(
            status=status,
            dimension_correlations=corr_matrix,
            pca_result=pca_result,
            interpretation=interpretation
        )

    def print_results(self, assessment: DimensionalityAssessment):
        """Pretty print dimensionality assessment results."""

        print("\n=== Dimensionality Analysis ===\n")

        # Correlation matrix
        print("Inter-Dimension Correlation Matrix:")
        print(assessment.dimension_correlations.to_string())
        print()

        # Get off-diagonal correlations
        print("Pairwise Correlations:")
        dims = self.dimensions
        for i in range(len(dims)):
            for j in range(i+1, len(dims)):
                r = assessment.dimension_correlations.iloc[i, j]
                print(f"  {dims[i]} vs {dims[j]}: r={r:.3f}")
        print()

        # PCA results
        print("Principal Component Analysis:")
        for i, var in enumerate(assessment.pca_result.variance_explained):
            cum_var = assessment.pca_result.cumulative_variance[i]
            print(f"  Component {i+1}: {var*100:.1f}% variance (cumulative: {cum_var*100:.1f}%)")
        print()
        print(f"Components needed for 90% variance: {assessment.pca_result.components_for_90pct}")
        print()

        # Component loadings
        print("Component Loadings (how dimensions load on components):")
        loadings_df = pd.DataFrame(
            assessment.pca_result.loadings.T,
            index=self.dimensions,
            columns=[f"PC{i+1}" for i in range(3)]
        )
        print(loadings_df.to_string())
        print()

        # Assessment
        print(f"Assessment: {assessment.status}")
        print(f"\n{assessment.interpretation}")
        print()


if __name__ == "__main__":
    # Test the dimensionality analyzer (ENSEMBLE SUPPORT)
    print("=== Testing Dimensionality Analyzer (Ensemble Support) ===\n")

    # Test 1: Full ensemble (5 evaluators)
    print("--- Full Ensemble (5 evaluators) ---")
    analyzer = DimensionalityAnalyzer()
    print(f"Loaded {len(analyzer.df)} trials with consensus scores")
    print(f"Excluded evaluators: {analyzer.exclude_evaluators if analyzer.exclude_evaluators else 'None'}\n")

    assessment = analyzer.assess_dimensionality()
    analyzer.print_results(assessment)

    # Verify PCA math
    print("=== Verification ===")
    print(f"Total variance explained by 3 components: {assessment.pca_result.cumulative_variance[-1]*100:.1f}%")
    print("(Should be ~100% for 3 components on 3 dimensions)")
    print()

    # Test 2: Without Gemini (4 evaluators)
    print("\n" + "="*60)
    print("--- Without Gemini (4 evaluators) ---")
    analyzer_no_gemini = DimensionalityAnalyzer(exclude_evaluators=["gemini-2-5-pro"])
    print(f"Loaded {len(analyzer_no_gemini.df)} trials with consensus scores")
    print(f"Excluded evaluators: {analyzer_no_gemini.exclude_evaluators}\n")

    assessment_no_gemini = analyzer_no_gemini.assess_dimensionality()
    analyzer_no_gemini.print_results(assessment_no_gemini)

    # Compare results
    print("\n" + "="*60)
    print("=== Comparison: Full Ensemble vs Without Gemini ===\n")

    print("Dimensionality Status:")
    print(f"  Full ensemble: {assessment.status}")
    print(f"  Without Gemini: {assessment_no_gemini.status}")
    print()

    print("Components needed for 90% variance:")
    print(f"  Full ensemble: {assessment.pca_result.components_for_90pct}")
    print(f"  Without Gemini: {assessment_no_gemini.pca_result.components_for_90pct}")
    print()

    print("✅ Dimensionality analyzer test complete!")
