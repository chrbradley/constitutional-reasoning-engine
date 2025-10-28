#!/usr/bin/env python3
"""
Outlier Detection (ENSEMBLE SUPPORT)
Phase 0.4 - Step 4: Identify trials with unusual scoring patterns and disagreement

With FIVE evaluators, outliers are defined as:
1. HIGH VARIANCE TRIALS: High inter-evaluator disagreement on same trial
2. EVALUATOR OUTLIERS: Evaluators consistently different from consensus
3. Extreme consensus scores (very high or very low)
4. Inconsistent dimension scores within evaluator
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

from data_loader import ExperimentDataLoader, TrialData

@dataclass
class OutlierTrial:
    """Information about an outlier trial (using consensus scores)."""
    trial_id: str
    scenario_id: str
    constitution: str
    layer2_model: str
    consensus_scores: Dict[str, float]
    outlier_reasons: List[str]
    deviation_from_mean: float

@dataclass
class HighVarianceTrial:
    """Trial with high inter-evaluator disagreement."""
    trial_id: str
    scenario_id: str
    constitution: str
    layer2_model: str
    dimension: str
    evaluator_scores: Dict[str, float]  # {evaluator: score}
    mean_score: float
    std_dev: float
    score_range: float  # max - min
    disagreement_reason: str

class OutlierDetector:
    """Detect trials with unusual scoring patterns and inter-evaluator disagreement."""

    def __init__(self, experiment_id: str = "exp_20251026_193228", exclude_evaluators: Optional[List[str]] = None):
        self.loader = ExperimentDataLoader(experiment_id)
        df_full = self.loader.get_trial_dataframe()  # All evaluations (598 rows)

        # Filter out excluded evaluators (e.g., Gemini outlier)
        if exclude_evaluators:
            df_full = df_full[~df_full["evaluator"].isin(exclude_evaluators)]

        self.df_full = df_full
        self.exclude_evaluators = exclude_evaluators or []

        # Calculate consensus scores (mean across evaluators for each trial)
        dimensions = ["factual_adherence", "value_transparency", "logical_coherence", "overall_score"]
        consensus_data = []

        for trial_id in self.df_full["trial_id"].unique():
            trial_subset = self.df_full[self.df_full["trial_id"] == trial_id]

            consensus_row = {
                "trial_id": trial_id,
                "scenario_id": trial_subset.iloc[0]["scenario_id"],
                "constitution": trial_subset.iloc[0]["constitution"],
                "layer2_model": trial_subset.iloc[0]["layer2_model"],
            }

            # Calculate mean score across evaluators for each dimension
            for dim in dimensions:
                consensus_row[dim] = trial_subset[dim].mean()

            consensus_data.append(consensus_row)

        self.df_consensus = pd.DataFrame(consensus_data)
        self.evaluators = sorted(self.df_full["evaluator"].unique())

    def detect_extreme_scores(
        self,
        dimension: str = "overall_score",
        low_threshold: float = 40,
        high_threshold: float = 95
    ) -> List[OutlierTrial]:
        """
        Detect trials with extremely low or high consensus scores.

        Uses mean score across all evaluators for each trial.

        Args:
            dimension: Score dimension to check (consensus)
            low_threshold: Scores below this are flagged as outliers
            high_threshold: Scores above this are flagged as outliers
        """

        outliers = []

        # Find extreme low scores
        low_df = self.df_consensus[self.df_consensus[dimension] < low_threshold]
        for _, row in low_df.iterrows():
            consensus_scores = {
                "factual_adherence": row["factual_adherence"],
                "value_transparency": row["value_transparency"],
                "logical_coherence": row["logical_coherence"],
                "overall_score": row["overall_score"]
            }

            outliers.append(OutlierTrial(
                trial_id=row["trial_id"],
                scenario_id=row["scenario_id"],
                constitution=row["constitution"],
                layer2_model=row["layer2_model"],
                consensus_scores=consensus_scores,
                outlier_reasons=[f"Extremely low consensus {dimension}: {row[dimension]:.0f}"],
                deviation_from_mean=row[dimension] - self.df_consensus[dimension].mean()
            ))

        # Find extreme high scores
        high_df = self.df_consensus[self.df_consensus[dimension] > high_threshold]
        for _, row in high_df.iterrows():
            consensus_scores = {
                "factual_adherence": row["factual_adherence"],
                "value_transparency": row["value_transparency"],
                "logical_coherence": row["logical_coherence"],
                "overall_score": row["overall_score"]
            }

            outliers.append(OutlierTrial(
                trial_id=row["trial_id"],
                scenario_id=row["scenario_id"],
                constitution=row["constitution"],
                layer2_model=row["layer2_model"],
                consensus_scores=consensus_scores,
                outlier_reasons=[f"Extremely high consensus {dimension}: {row[dimension]:.0f}"],
                deviation_from_mean=row[dimension] - self.df_consensus[dimension].mean()
            ))

        return outliers

    def detect_group_deviants(
        self,
        dimension: str = "overall_score",
        std_threshold: float = 2.0
    ) -> List[OutlierTrial]:
        """
        Detect trials that deviate significantly from their group mean (consensus).

        Groups are defined by (scenario, constitution).
        Trials more than std_threshold standard deviations from group mean are flagged.
        Uses consensus scores (mean across evaluators).
        """

        outliers = []

        # Calculate group statistics using consensus
        group_stats = self.df_consensus.groupby(["scenario_id", "constitution"])[dimension].agg(["mean", "std", "count"])

        for _, row in self.df_consensus.iterrows():
            group_key = (row["scenario_id"], row["constitution"])
            group_mean = group_stats.loc[group_key, "mean"]
            group_std = group_stats.loc[group_key, "std"]

            if pd.notna(group_std) and group_std > 0:
                z_score = (row[dimension] - group_mean) / group_std

                if abs(z_score) > std_threshold:
                    consensus_scores = {
                        "factual_adherence": row["factual_adherence"],
                        "value_transparency": row["value_transparency"],
                        "logical_coherence": row["logical_coherence"],
                        "overall_score": row["overall_score"]
                    }

                    outliers.append(OutlierTrial(
                        trial_id=row["trial_id"],
                        scenario_id=row["scenario_id"],
                        constitution=row["constitution"],
                        layer2_model=row["layer2_model"],
                        consensus_scores=consensus_scores,
                        outlier_reasons=[
                            f"Deviates {z_score:.1f}σ from group mean (consensus)",
                            f"Score: {row[dimension]:.0f}, Group mean: {group_mean:.0f}"
                        ],
                        deviation_from_mean=row[dimension] - group_mean
                    ))

        return outliers

    def detect_dimension_inconsistencies(
        self,
        threshold: float = 30
    ) -> List[OutlierTrial]:
        """
        Detect trials where dimension scores are inconsistent (using consensus).

        E.g., high factual_adherence but low overall_score (or vice versa).
        Uses consensus scores (mean across evaluators).
        """

        outliers = []

        for _, row in self.df_consensus.iterrows():
            # Calculate range of dimension scores
            dims = ["factual_adherence", "value_transparency", "logical_coherence"]
            dim_scores = [row[d] for d in dims]
            score_range = max(dim_scores) - min(dim_scores)

            if score_range > threshold:
                consensus_scores = {
                    "factual_adherence": row["factual_adherence"],
                    "value_transparency": row["value_transparency"],
                    "logical_coherence": row["logical_coherence"],
                    "overall_score": row["overall_score"]
                }

                reasons = [
                    f"Large dimension score spread (consensus): {score_range:.0f} points",
                    f"Factual: {row['factual_adherence']:.0f}, " +
                    f"Transparency: {row['value_transparency']:.0f}, " +
                    f"Coherence: {row['logical_coherence']:.0f}"
                ]

                outliers.append(OutlierTrial(
                    trial_id=row["trial_id"],
                    scenario_id=row["scenario_id"],
                    constitution=row["constitution"],
                    layer2_model=row["layer2_model"],
                    consensus_scores=consensus_scores,
                    outlier_reasons=reasons,
                    deviation_from_mean=0  # Not applicable for this type
                ))

        return outliers

    def detect_high_variance_trials(
        self,
        dimension: str = "overall_score",
        std_threshold: float = 15.0
    ) -> List[HighVarianceTrial]:
        """
        Detect trials with high inter-evaluator disagreement (NEW FOR ENSEMBLE).

        High standard deviation across evaluators indicates disagreement
        about the quality of the reasoning.

        Args:
            dimension: Score dimension to check
            std_threshold: Standard deviation threshold (15 = high disagreement)

        Returns:
            List of trials with high variance across evaluators
        """

        high_variance = []

        for trial_id in self.df_full["trial_id"].unique():
            trial_subset = self.df_full[self.df_full["trial_id"] == trial_id]

            # Get scores from all evaluators for this trial
            scores = trial_subset[dimension].values
            evaluator_scores = dict(zip(trial_subset["evaluator"], scores))

            if len(scores) >= 3:  # Need at least 3 evaluators
                mean_score = scores.mean()
                std_dev = scores.std()
                score_range = scores.max() - scores.min()

                if std_dev >= std_threshold:
                    # Identify reason for disagreement
                    if score_range > 40:
                        reason = f"Wide score range ({score_range:.0f} points) - evaluators strongly disagree"
                    elif std_dev > 20:
                        reason = f"Very high std dev ({std_dev:.1f}) - inconsistent evaluations"
                    else:
                        reason = f"High std dev ({std_dev:.1f}) - moderate disagreement"

                    high_variance.append(HighVarianceTrial(
                        trial_id=trial_id,
                        scenario_id=trial_subset.iloc[0]["scenario_id"],
                        constitution=trial_subset.iloc[0]["constitution"],
                        layer2_model=trial_subset.iloc[0]["layer2_model"],
                        dimension=dimension,
                        evaluator_scores=evaluator_scores,
                        mean_score=mean_score,
                        std_dev=std_dev,
                        score_range=score_range,
                        disagreement_reason=reason
                    ))

        return sorted(high_variance, key=lambda x: x.std_dev, reverse=True)

    def detect_evaluator_outliers(
        self,
        dimension: str = "overall_score",
        deviation_threshold: float = 10.0
    ) -> Dict[str, List[str]]:
        """
        Detect evaluators consistently different from consensus (NEW FOR ENSEMBLE).

        For each evaluator, find trials where their score deviates significantly
        from the mean of the other evaluators.

        Args:
            dimension: Score dimension to check
            deviation_threshold: Absolute deviation from consensus to flag

        Returns:
            Dict[evaluator_name, List[trial_ids_where_outlier]]
        """

        evaluator_outliers = {eval_name: [] for eval_name in self.evaluators}

        for trial_id in self.df_full["trial_id"].unique():
            trial_subset = self.df_full[self.df_full["trial_id"] == trial_id]

            for evaluator in self.evaluators:
                # Get this evaluator's score
                eval_score_row = trial_subset[trial_subset["evaluator"] == evaluator]

                if len(eval_score_row) == 0:
                    continue  # Evaluator didn't score this trial

                eval_score = eval_score_row[dimension].values[0]

                # Calculate consensus WITHOUT this evaluator
                other_scores = trial_subset[trial_subset["evaluator"] != evaluator][dimension]
                if len(other_scores) >= 2:  # Need at least 2 others for consensus
                    consensus = other_scores.mean()
                    deviation = abs(eval_score - consensus)

                    if deviation >= deviation_threshold:
                        evaluator_outliers[evaluator].append(trial_id)

        # Sort by number of outlier trials (descending)
        evaluator_outliers = {
            k: v for k, v in sorted(
                evaluator_outliers.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )
        }

        return evaluator_outliers

    def generate_review_markdown(self, outliers: List[OutlierTrial], output_path: str):
        """Generate markdown file for manual review of outliers."""

        with open(output_path, "w") as f:
            f.write("# Outlier Trials - Manual Review\n\n")
            f.write(f"Total outliers flagged: {len(outliers)}\n\n")
            f.write("---\n\n")

            for outlier in outliers:
                f.write(f"## Trial ID: {outlier.trial_id}\n\n")
                f.write(f"**Metadata:**\n")
                f.write(f"- Scenario: {outlier.scenario_id}\n")
                f.write(f"- Constitution: {outlier.constitution}\n")
                f.write(f"- Layer2 Model: {outlier.layer2_model}\n\n")

                f.write(f"**Consensus Scores:**\n")
                for dim, score in outlier.consensus_scores.items():
                    f.write(f"- {dim}: {score:.0f}\n")
                f.write("\n")

                f.write(f"**Outlier Reasons:**\n")
                for reason in outlier.outlier_reasons:
                    f.write(f"- {reason}\n")
                f.write("\n")

                if outlier.deviation_from_mean != 0:
                    direction = "above" if outlier.deviation_from_mean > 0 else "below"
                    f.write(f"**Deviation:** {abs(outlier.deviation_from_mean):.1f} points {direction} mean\n\n")

                f.write("---\n\n")

        print(f"Review file written to: {output_path}")

    def analyze_patterns(self, outliers: List[OutlierTrial]) -> Dict:
        """Analyze patterns in outliers."""

        if not outliers:
            return {"message": "No outliers found"}

        # Count by scenario
        scenario_counts = {}
        for outlier in outliers:
            scenario_counts[outlier.scenario_id] = scenario_counts.get(outlier.scenario_id, 0) + 1

        # Count by constitution
        constitution_counts = {}
        for outlier in outliers:
            constitution_counts[outlier.constitution] = constitution_counts.get(outlier.constitution, 0) + 1

        # Count by model
        model_counts = {}
        for outlier in outliers:
            model_counts[outlier.layer2_model] = model_counts.get(outlier.layer2_model, 0) + 1

        return {
            "total_outliers": len(outliers),
            "by_scenario": dict(sorted(scenario_counts.items(), key=lambda x: x[1], reverse=True)),
            "by_constitution": dict(sorted(constitution_counts.items(), key=lambda x: x[1], reverse=True)),
            "by_model": dict(sorted(model_counts.items(), key=lambda x: x[1], reverse=True))
        }


if __name__ == "__main__":
    # Test the outlier detector (ENSEMBLE SUPPORT)
    print("=== Testing Outlier Detector (Ensemble Support) ===\n")

    # ===== FULL ENSEMBLE (5 evaluators) =====
    print("--- Full Ensemble (5 evaluators) ---\n")

    detector = OutlierDetector()
    print(f"Loaded {len(detector.df_full)} evaluations from {len(detector.evaluators)} evaluators")
    print(f"Evaluators: {detector.evaluators}")
    print(f"Consensus data: {len(detector.df_consensus)} trials\n")

    # Test 1: Extreme consensus scores
    print("1. Detecting extreme consensus scores (low<40, high>95)...")
    extreme = detector.detect_extreme_scores(low_threshold=40, high_threshold=95)
    print(f"   Found {len(extreme)} trials with extreme consensus scores")
    if extreme:
        print(f"   Example: {extreme[0].trial_id} - {extreme[0].outlier_reasons[0]}")
    print()

    # Test 2: Group deviants (consensus)
    print("2. Detecting group deviants (>2σ from group mean, using consensus)...")
    deviants = detector.detect_group_deviants(std_threshold=2.0)
    print(f"   Found {len(deviants)} trials deviating >2σ from group")
    if deviants:
        print(f"   Example: {deviants[0].trial_id} - {deviants[0].outlier_reasons[0]}")
    print()

    # Test 3: Dimension inconsistencies (consensus)
    print("3. Detecting dimension inconsistencies (>30 point spread in consensus)...")
    inconsistent = detector.detect_dimension_inconsistencies(threshold=30)
    print(f"   Found {len(inconsistent)} trials with inconsistent dimensions")
    if inconsistent:
        print(f"   Example: {inconsistent[0].trial_id} - {inconsistent[0].outlier_reasons[0]}")
    print()

    # Test 4: HIGH VARIANCE TRIALS (NEW - inter-evaluator disagreement)
    print("4. Detecting high variance trials (std dev >15 across evaluators)...")
    high_variance = detector.detect_high_variance_trials(std_threshold=15.0)
    print(f"   Found {len(high_variance)} trials with high inter-evaluator disagreement")
    if high_variance:
        print(f"\n   Top {min(3, len(high_variance))} high-variance trials:")
        for i, trial in enumerate(high_variance[:3], 1):
            print(f"\n   {i}. {trial.trial_id}")
            print(f"      Std dev: {trial.std_dev:.1f}, Range: {trial.score_range:.0f}")
            print(f"      Scores: {', '.join(f'{k}: {v:.0f}' for k, v in trial.evaluator_scores.items())}")
            print(f"      Reason: {trial.disagreement_reason}")
    print()

    # Test 5: EVALUATOR OUTLIERS (NEW - which evaluators are consistently different)
    print("5. Detecting evaluator outliers (deviation >10 from consensus)...")
    eval_outliers = detector.detect_evaluator_outliers(deviation_threshold=10.0)
    print(f"   Evaluators ranked by outlier trial count:")
    for evaluator, trial_ids in eval_outliers.items():
        if len(trial_ids) > 0:
            pct = (len(trial_ids) / 120) * 100
            print(f"     {evaluator}: {len(trial_ids)} outlier trials ({pct:.1f}%)")
    print()

    # ===== WITHOUT GEMINI (4 evaluators) =====
    print("\n" + "="*60)
    print("--- Without Gemini (4 evaluators) ---\n")

    detector_no_gemini = OutlierDetector(exclude_evaluators=["gemini-2-5-pro"])
    print(f"Loaded {len(detector_no_gemini.df_full)} evaluations from {len(detector_no_gemini.evaluators)} evaluators")
    print(f"Evaluators: {detector_no_gemini.evaluators}")
    print(f"Excluded: {detector_no_gemini.exclude_evaluators}")
    print(f"Consensus data: {len(detector_no_gemini.df_consensus)} trials\n")

    # Test 4: HIGH VARIANCE TRIALS (without Gemini)
    print("4. Detecting high variance trials (std dev >15 across evaluators, NO GEMINI)...")
    high_variance_no_gemini = detector_no_gemini.detect_high_variance_trials(std_threshold=15.0)
    print(f"   Found {len(high_variance_no_gemini)} trials with high inter-evaluator disagreement")
    if high_variance_no_gemini:
        print(f"\n   Top {min(3, len(high_variance_no_gemini))} high-variance trials:")
        for i, trial in enumerate(high_variance_no_gemini[:3], 1):
            print(f"\n   {i}. {trial.trial_id}")
            print(f"      Std dev: {trial.std_dev:.1f}, Range: {trial.score_range:.0f}")
            print(f"      Scores: {', '.join(f'{k}: {v:.0f}' for k, v in trial.evaluator_scores.items())}")
            print(f"      Reason: {trial.disagreement_reason}")
    print()

    # Test 5: EVALUATOR OUTLIERS (without Gemini)
    print("5. Detecting evaluator outliers (deviation >10 from consensus, NO GEMINI)...")
    eval_outliers_no_gemini = detector_no_gemini.detect_evaluator_outliers(deviation_threshold=10.0)
    print(f"   Evaluators ranked by outlier trial count:")
    for evaluator, trial_ids in eval_outliers_no_gemini.items():
        if len(trial_ids) > 0:
            pct = (len(trial_ids) / 120) * 100
            print(f"     {evaluator}: {len(trial_ids)} outlier trials ({pct:.1f}%)")
    print()

    # ===== COMPARISON =====
    print("="*60)
    print("=== Comparison: Full Ensemble vs Without Gemini ===\n")

    print(f"High-variance trials (std dev >15):")
    print(f"  Full ensemble: {len(high_variance)} trials")
    print(f"  Without Gemini: {len(high_variance_no_gemini)} trials")
    print(f"  Reduction: {len(high_variance) - len(high_variance_no_gemini)} trials")
    print()

    print("✅ Outlier detector test complete!")
