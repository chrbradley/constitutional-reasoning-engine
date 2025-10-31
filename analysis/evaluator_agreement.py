#!/usr/bin/env python3
"""
Evaluator Agreement Analysis
Week 1, Task 2 (Analysis 1.3) of Analysis & Publication Plan

Analyzes inter-rater reliability among 5 evaluators using Likert rubric.
Identifies outlier evaluators, creates consensus scores, performs stratified
reliability analysis.

Purpose: Determine which evaluator scores to trust for downstream analyses
(1.2 Model×Constitution, 1.4 Dimensional Structure) and human validation.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from itertools import combinations
from scipy import stats


@dataclass
class EvaluatorScores:
    """Scores from one evaluator for one trial."""
    evaluator: str
    epistemic_integrity: float
    value_transparency: float
    overall_score: float


@dataclass
class TrialEvaluations:
    """All evaluator scores for one trial."""
    trial_id: str
    scenario_id: str
    constitution: str
    layer2_model: str
    evaluations: Dict[str, EvaluatorScores]  # Dict[evaluator_name, scores]

    def get_score_vector(self, dimension: str) -> Dict[str, float]:
        """Get scores from all evaluators for a specific dimension."""
        return {
            evaluator: getattr(scores, dimension)
            for evaluator, scores in self.evaluations.items()
        }

    def has_complete_evaluations(self, required_evaluators: List[str]) -> bool:
        """Check if trial has scores from all required evaluators."""
        return all(evaluator in self.evaluations for evaluator in required_evaluators)


@dataclass
class ConsensusScores:
    """Consensus scores across evaluators for one trial."""
    trial_id: str
    mean_all: Dict[str, float]  # Mean across all evaluators
    median_all: Dict[str, float]  # Median across all evaluators
    trimmed_mean: Dict[str, float]  # Mean after removing highest/lowest
    mean_excluding_outlier: Optional[Dict[str, float]]  # Mean if outlier excluded
    standard_deviation: Dict[str, float]  # SD across evaluators
    max_disagreement: float  # Max SD across any dimension


class EvaluatorAgreementAnalyzer:
    """Analyze inter-rater reliability among evaluators."""

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id

        # Find project root (handles running from notebooks/ or root)
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

    def load_trial(self, trial_id: str) -> TrialEvaluations:
        """Load all evaluator scores for one trial."""

        trial_file = self.likert_dir / f"{trial_id}.json"
        if not trial_file.exists():
            raise FileNotFoundError(f"Trial not found: {trial_id}")

        with open(trial_file) as f:
            data = json.load(f)

        evaluations = {}
        for evaluator_name, eval_data in data.get("evaluations", {}).items():
            if eval_data.get("status") == "completed" and eval_data.get("response_parsed"):
                parsed = eval_data["response_parsed"]
                evaluations[evaluator_name] = EvaluatorScores(
                    evaluator=evaluator_name,
                    epistemic_integrity=parsed["epistemicIntegrity"]["score"],
                    value_transparency=parsed["valueTransparency"]["score"],
                    overall_score=parsed["overallScore"]
                )

        return TrialEvaluations(
            trial_id=data["trial_id"],
            scenario_id=data["scenario_id"],
            constitution=data["constitution"],
            layer2_model=data["model"],
            evaluations=evaluations
        )

    def load_all_trials(self) -> List[TrialEvaluations]:
        """Load all trials from Likert rubric."""

        trials = []
        trial_files = sorted(self.likert_dir.glob("trial_*.json"))

        for trial_file in trial_files:
            trial_id = trial_file.stem
            try:
                trial = self.load_trial(trial_id)
                if trial.evaluations:  # Only include if has at least 1 evaluation
                    trials.append(trial)
            except Exception as e:
                print(f"Warning: Failed to load {trial_id}: {e}")
                continue

        return trials

    def calculate_pairwise_correlations(
        self,
        trials: List[TrialEvaluations],
        dimension: str = "overall_score"
    ) -> Dict[Tuple[str, str], Dict]:
        """
        Calculate Pearson r between all evaluator pairs.

        Returns:
            Dict mapping (evaluator1, evaluator2) → {r, p, n, ci_lower, ci_upper}
        """

        # Build score matrix: rows=trials, cols=evaluators
        score_matrix = {evaluator: [] for evaluator in self.evaluators}
        trial_ids = []

        for trial in trials:
            scores = trial.get_score_vector(dimension)
            # Only include trial if all evaluators scored it
            if len(scores) == len(self.evaluators):
                trial_ids.append(trial.trial_id)
                for evaluator in self.evaluators:
                    score_matrix[evaluator].append(scores.get(evaluator, np.nan))

        # Calculate pairwise correlations
        correlations = {}
        for eval1, eval2 in combinations(self.evaluators, 2):
            scores1 = np.array(score_matrix[eval1])
            scores2 = np.array(score_matrix[eval2])

            # Remove pairs with missing data
            mask = ~(np.isnan(scores1) | np.isnan(scores2))
            scores1_clean = scores1[mask]
            scores2_clean = scores2[mask]

            n = len(scores1_clean)

            if n >= 10:  # Minimum 10 shared trials
                r, p = stats.pearsonr(scores1_clean, scores2_clean)

                # Calculate 95% confidence interval using Fisher z-transformation
                z = np.arctanh(r)
                se = 1 / np.sqrt(n - 3)
                ci_lower_z = z - 1.96 * se
                ci_upper_z = z + 1.96 * se
                ci_lower = np.tanh(ci_lower_z)
                ci_upper = np.tanh(ci_upper_z)

                correlations[(eval1, eval2)] = {
                    "r": r,
                    "p": p,
                    "n": n,
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper
                }
            else:
                correlations[(eval1, eval2)] = {
                    "r": np.nan,
                    "p": np.nan,
                    "n": n,
                    "ci_lower": np.nan,
                    "ci_upper": np.nan
                }

        return correlations

    def calculate_icc(
        self,
        trials: List[TrialEvaluations],
        dimension: str = "overall_score"
    ) -> Dict[str, float]:
        """
        Calculate Intraclass Correlation Coefficient (ICC).

        Returns ICC(2,1) for single-rater consistency and ICC(2,k) for average-rater.
        """

        # Build matrix: rows=trials, cols=evaluators (only complete trials)
        scores_list = []
        valid_trial_ids = []

        for trial in trials:
            if trial.has_complete_evaluations(self.evaluators):
                trial_scores = [
                    getattr(trial.evaluations[evaluator], dimension)
                    for evaluator in self.evaluators
                ]
                scores_list.append(trial_scores)
                valid_trial_ids.append(trial.trial_id)

        if len(scores_list) < 2:
            return {"icc_single": np.nan, "icc_average": np.nan, "n_trials": 0}

        scores_matrix = np.array(scores_list)  # Shape: (n_trials, n_evaluators)
        n = len(scores_matrix)
        k = len(self.evaluators)

        # Calculate mean squares
        grand_mean = np.mean(scores_matrix)
        row_means = np.mean(scores_matrix, axis=1)
        col_means = np.mean(scores_matrix, axis=0)

        # Mean Square for Rows (between-trial variance)
        msr = k * np.sum((row_means - grand_mean) ** 2) / (n - 1)

        # Mean Square for Columns (between-evaluator variance)
        msc = n * np.sum((col_means - grand_mean) ** 2) / (k - 1)

        # Mean Square Error (residual variance)
        mse = 0
        for i in range(n):
            for j in range(k):
                residual = scores_matrix[i, j] - row_means[i] - col_means[j] + grand_mean
                mse += residual ** 2
        mse /= (n - 1) * (k - 1)

        # ICC(2,1) - Two-way random effects, single rater
        icc_single = (msr - mse) / (msr + (k - 1) * mse)

        # ICC(2,k) - Two-way random effects, average of k raters
        icc_average = (msr - mse) / msr

        return {
            "icc_single": icc_single,
            "icc_average": icc_average,
            "n_trials": n
        }

    def detect_outlier_evaluators(
        self,
        trials: List[TrialEvaluations],
        dimension: str = "overall_score",
        threshold: float = 0.50
    ) -> Dict[str, Dict]:
        """
        Detect outlier evaluators based on mean correlation with others.

        An evaluator is considered an outlier if their mean correlation with
        other evaluators is below the threshold.

        Args:
            threshold: Minimum acceptable mean correlation (default: 0.50)

        Returns:
            Dict mapping evaluator → {mean_r, is_outlier}
        """

        correlations = self.calculate_pairwise_correlations(trials, dimension)

        # Calculate mean correlation for each evaluator
        evaluator_stats = {}
        for evaluator in self.evaluators:
            # Get all correlations involving this evaluator
            relevant_corrs = []
            for (eval1, eval2), corr_data in correlations.items():
                if evaluator in (eval1, eval2) and not np.isnan(corr_data["r"]):
                    relevant_corrs.append(corr_data["r"])

            if relevant_corrs:
                mean_r = np.mean(relevant_corrs)
                std_r = np.std(relevant_corrs)
                is_outlier = mean_r < threshold

                evaluator_stats[evaluator] = {
                    "mean_r": mean_r,
                    "std_r": std_r,
                    "n_pairs": len(relevant_corrs),
                    "is_outlier": is_outlier,
                    "z_score": None  # Will calculate if needed
                }
            else:
                evaluator_stats[evaluator] = {
                    "mean_r": np.nan,
                    "std_r": np.nan,
                    "n_pairs": 0,
                    "is_outlier": False,
                    "z_score": None
                }

        # Calculate z-scores (how many SDs from mean)
        all_mean_rs = [stats["mean_r"] for stats in evaluator_stats.values() if not np.isnan(stats["mean_r"])]
        if len(all_mean_rs) > 1:
            overall_mean = np.mean(all_mean_rs)
            overall_std = np.std(all_mean_rs)

            for evaluator in evaluator_stats:
                if not np.isnan(evaluator_stats[evaluator]["mean_r"]):
                    z = (evaluator_stats[evaluator]["mean_r"] - overall_mean) / overall_std if overall_std > 0 else 0
                    evaluator_stats[evaluator]["z_score"] = z

        return evaluator_stats

    def create_consensus_scores(
        self,
        trials: List[TrialEvaluations],
        outlier_evaluator: Optional[str] = None
    ) -> List[ConsensusScores]:
        """
        Generate consensus scores using multiple aggregation methods.

        Args:
            outlier_evaluator: If specified, also calculate consensus excluding this evaluator

        Returns:
            List of ConsensusScores, one per trial
        """

        consensus_list = []

        for trial in trials:
            dimensions = ["epistemic_integrity", "value_transparency", "overall_score"]

            # Calculate consensus for each dimension
            mean_all = {}
            median_all = {}
            trimmed_mean = {}
            mean_excluding = {} if outlier_evaluator else None
            std_devs = {}

            for dimension in dimensions:
                scores = trial.get_score_vector(dimension)
                score_values = list(scores.values())

                if len(score_values) >= 2:
                    mean_all[dimension] = np.mean(score_values)
                    median_all[dimension] = np.median(score_values)
                    std_devs[dimension] = np.std(score_values)

                    # Trimmed mean: remove highest and lowest, average remaining
                    if len(score_values) >= 3:
                        sorted_scores = sorted(score_values)
                        trimmed = sorted_scores[1:-1] if len(sorted_scores) > 2 else sorted_scores
                        trimmed_mean[dimension] = np.mean(trimmed)
                    else:
                        trimmed_mean[dimension] = mean_all[dimension]

                    # Mean excluding outlier
                    if outlier_evaluator and outlier_evaluator in scores:
                        filtered_scores = [
                            score for eval, score in scores.items()
                            if eval != outlier_evaluator
                        ]
                        if filtered_scores:
                            mean_excluding[dimension] = np.mean(filtered_scores)
                        else:
                            mean_excluding[dimension] = np.nan
                    elif outlier_evaluator:
                        mean_excluding[dimension] = mean_all[dimension]
                else:
                    # Insufficient data
                    mean_all[dimension] = np.nan
                    median_all[dimension] = np.nan
                    trimmed_mean[dimension] = np.nan
                    std_devs[dimension] = np.nan
                    if outlier_evaluator:
                        mean_excluding[dimension] = np.nan

            # Maximum disagreement across any dimension
            valid_stds = [std for std in std_devs.values() if not np.isnan(std)]
            max_disagreement = max(valid_stds) if valid_stds else np.nan

            consensus_list.append(ConsensusScores(
                trial_id=trial.trial_id,
                mean_all=mean_all,
                median_all=median_all,
                trimmed_mean=trimmed_mean,
                mean_excluding_outlier=mean_excluding,
                standard_deviation=std_devs,
                max_disagreement=max_disagreement
            ))

        return consensus_list

    def stratified_reliability(
        self,
        trials: List[TrialEvaluations],
        dimension: str = "overall_score"
    ) -> Dict:
        """
        Calculate inter-rater reliability stratified by constitution and scenario.

        Returns:
            Dict with reliability metrics per constitution and per scenario
        """

        results = {
            "by_constitution": {},
            "by_scenario": {}
        }

        # Stratify by constitution
        constitutions = set(trial.constitution for trial in trials)
        for constitution in sorted(constitutions):
            const_trials = [t for t in trials if t.constitution == constitution]

            if len(const_trials) >= 10:  # Minimum sample size
                correlations = self.calculate_pairwise_correlations(const_trials, dimension)
                valid_corrs = [c["r"] for c in correlations.values() if not np.isnan(c["r"])]

                icc_stats = self.calculate_icc(const_trials, dimension)

                results["by_constitution"][constitution] = {
                    "n_trials": len(const_trials),
                    "mean_r": float(np.mean(valid_corrs)) if valid_corrs else np.nan,
                    "std_r": float(np.std(valid_corrs)) if valid_corrs else np.nan,
                    "icc_single": icc_stats["icc_single"],
                    "icc_average": icc_stats["icc_average"]
                }

        # Stratify by scenario
        scenarios = set(trial.scenario_id for trial in trials)
        for scenario in sorted(scenarios):
            scenario_trials = [t for t in trials if t.scenario_id == scenario]

            if len(scenario_trials) >= 10:  # Minimum sample size
                correlations = self.calculate_pairwise_correlations(scenario_trials, dimension)
                valid_corrs = [c["r"] for c in correlations.values() if not np.isnan(c["r"])]

                icc_stats = self.calculate_icc(scenario_trials, dimension)

                results["by_scenario"][scenario] = {
                    "n_trials": len(scenario_trials),
                    "mean_r": float(np.mean(valid_corrs)) if valid_corrs else np.nan,
                    "std_r": float(np.std(valid_corrs)) if valid_corrs else np.nan,
                    "icc_single": icc_stats["icc_single"],
                    "icc_average": icc_stats["icc_average"]
                }

        return results

    def identify_high_disagreement_trials(
        self,
        consensus_scores: List[ConsensusScores],
        threshold_percentile: float = 90
    ) -> List[Dict]:
        """
        Identify trials with high evaluator disagreement.

        Args:
            threshold_percentile: Trials above this percentile of max_disagreement

        Returns:
            List of high-disagreement trials sorted by disagreement (descending)
        """

        # Calculate threshold
        valid_disagreements = [
            cs.max_disagreement for cs in consensus_scores
            if not np.isnan(cs.max_disagreement)
        ]

        if not valid_disagreements:
            return []

        threshold = np.percentile(valid_disagreements, threshold_percentile)

        # Identify high-disagreement trials
        high_disagreement = []
        for cs in consensus_scores:
            if not np.isnan(cs.max_disagreement) and cs.max_disagreement >= threshold:
                high_disagreement.append({
                    "trial_id": cs.trial_id,
                    "max_disagreement": cs.max_disagreement,
                    "std_epistemic_integrity": cs.standard_deviation.get("epistemic_integrity", np.nan),
                    "std_value_transparency": cs.standard_deviation.get("value_transparency", np.nan),
                    "std_overall_score": cs.standard_deviation.get("overall_score", np.nan)
                })

        # Sort by disagreement (descending)
        high_disagreement.sort(key=lambda x: x["max_disagreement"], reverse=True)

        return high_disagreement

    def analyze(self) -> Dict:
        """
        Run complete inter-rater reliability analysis.

        Returns:
            Dict with all analysis results
        """

        print("="*70)
        print("EVALUATOR AGREEMENT ANALYSIS")
        print(f"Experiment: {self.experiment_id}")
        print("="*70)

        # Load data
        print("\nLoading trials...")
        trials = self.load_all_trials()
        print(f"Loaded {len(trials)} trials")

        # Check data completeness
        complete_trials = sum(1 for t in trials if t.has_complete_evaluations(self.evaluators))
        print(f"Complete evaluations (all 5 evaluators): {complete_trials}/{len(trials)} trials")

        results = {
            "experiment_id": self.experiment_id,
            "n_trials": len(trials),
            "n_complete_trials": complete_trials,
            "evaluators": self.evaluators,
            "dimensions": {}
        }

        # Analyze each dimension
        for dimension in ["epistemic_integrity", "value_transparency", "overall_score"]:
            print(f"\n{'='*70}")
            print(f"Dimension: {dimension.replace('_', ' ').title()}")
            print('='*70)

            dim_results = {}

            # Pairwise correlations
            print("\n--- Pairwise Correlations ---")
            correlations = self.calculate_pairwise_correlations(trials, dimension)
            valid_corrs = [c["r"] for c in correlations.values() if not np.isnan(c["r"])]

            if valid_corrs:
                mean_r = np.mean(valid_corrs)
                std_r = np.std(valid_corrs)
                print(f"  Mean r: {mean_r:.3f} (±{std_r:.3f})")
                print(f"  Range:  [{min(valid_corrs):.3f}, {max(valid_corrs):.3f}]")
                print(f"  n_pairs: {len(valid_corrs)}")

                # Show all pairs
                print("\n  All pairs:")
                for (eval1, eval2), corr_data in sorted(correlations.items(), key=lambda x: x[1]["r"], reverse=True):
                    if not np.isnan(corr_data["r"]):
                        print(f"    {eval1:20} × {eval2:20} → r={corr_data['r']:6.3f} "
                              f"(95% CI: [{corr_data['ci_lower']:5.3f}, {corr_data['ci_upper']:5.3f}])")

                dim_results["pairwise_correlations"] = {
                    "mean_r": mean_r,
                    "std_r": std_r,
                    "min_r": min(valid_corrs),
                    "max_r": max(valid_corrs),
                    "all_pairs": {
                        f"{e1}_vs_{e2}": {
                            "r": corr_data["r"],
                            "p": corr_data["p"],
                            "n": corr_data["n"],
                            "ci_lower": corr_data["ci_lower"],
                            "ci_upper": corr_data["ci_upper"]
                        }
                        for (e1, e2), corr_data in correlations.items()
                    }
                }

            # ICC
            print("\n--- Intraclass Correlation Coefficient ---")
            icc_stats = self.calculate_icc(trials, dimension)
            print(f"  ICC(2,1) [single rater]: {icc_stats['icc_single']:.3f}")
            print(f"  ICC(2,k) [average rater]: {icc_stats['icc_average']:.3f}")
            print(f"  n_complete_trials: {icc_stats['n_trials']}")

            dim_results["icc"] = icc_stats

            # Outlier detection
            print("\n--- Outlier Evaluator Detection ---")
            outlier_stats = self.detect_outlier_evaluators(trials, dimension, threshold=0.50)
            for evaluator, stats_dict in sorted(outlier_stats.items(), key=lambda x: x[1]["mean_r"] if not np.isnan(x[1]["mean_r"]) else -999):
                if not np.isnan(stats_dict["mean_r"]):
                    outlier_flag = " ⚠️ OUTLIER" if stats_dict["is_outlier"] else ""
                    print(f"  {evaluator:20} → mean r: {stats_dict['mean_r']:.3f} "
                          f"(z={stats_dict['z_score']:+5.2f}){outlier_flag}")

            dim_results["outlier_detection"] = outlier_stats

            # Stratified reliability
            print("\n--- Stratified Reliability ---")
            stratified = self.stratified_reliability(trials, dimension)

            print("\n  By Constitution:")
            for constitution, stats_dict in sorted(stratified["by_constitution"].items()):
                print(f"    {constitution:25} → n={stats_dict['n_trials']:3}, "
                      f"r̄={stats_dict['mean_r']:5.3f}, ICC={stats_dict['icc_single']:5.3f}")

            print("\n  By Scenario:")
            for scenario, stats_dict in sorted(stratified["by_scenario"].items()):
                print(f"    {scenario:30} → n={stats_dict['n_trials']:3}, "
                      f"r̄={stats_dict['mean_r']:5.3f}, ICC={stats_dict['icc_single']:5.3f}")

            dim_results["stratified_reliability"] = stratified

            results["dimensions"][dimension] = dim_results

        # Generate consensus scores
        print(f"\n{'='*70}")
        print("CONSENSUS SCORE GENERATION")
        print('='*70)

        # Check if there's an outlier evaluator (based on overall_score)
        outlier_stats = results["dimensions"]["overall_score"]["outlier_detection"]
        outlier_evaluator = None
        for evaluator, stats_dict in outlier_stats.items():
            if stats_dict["is_outlier"]:
                outlier_evaluator = evaluator
                print(f"\n⚠️ Outlier detected: {outlier_evaluator}")
                print(f"   Mean r with others: {stats_dict['mean_r']:.3f} (threshold: 0.50)")
                break

        if not outlier_evaluator:
            print("\n✅ No outlier evaluators detected")

        consensus_scores = self.create_consensus_scores(trials, outlier_evaluator)
        print(f"\nGenerated consensus scores for {len(consensus_scores)} trials")

        # High-disagreement trials
        print(f"\n{'='*70}")
        print("HIGH-DISAGREEMENT TRIALS (Top 10%)")
        print('='*70)

        high_disagreement = self.identify_high_disagreement_trials(consensus_scores, threshold_percentile=90)
        print(f"\nIdentified {len(high_disagreement)} trials with high evaluator disagreement")
        print("\nTop 10:")
        for i, trial_info in enumerate(high_disagreement[:10], 1):
            print(f"  {i:2}. {trial_info['trial_id']:20} → max SD: {trial_info['max_disagreement']:5.2f}")

        results["consensus_scores"] = [asdict(cs) for cs in consensus_scores]
        results["high_disagreement_trials"] = high_disagreement

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
        print("Usage: python analysis/evaluator_agreement.py <experiment_id>")
        print("\nExample: python analysis/evaluator_agreement.py exp_20251028_134615")
        sys.exit(1)

    experiment_id = sys.argv[1]

    analyzer = EvaluatorAgreementAnalyzer(experiment_id)
    results = analyzer.analyze()

    # Convert numpy types to native Python types
    results = convert_numpy_types(results)

    # Save results
    output_dir = Path("results/experiments") / experiment_id / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "evaluator_agreement.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")

    # Also save consensus scores separately for downstream use
    consensus_file = output_dir / "consensus_scores.json"
    consensus_data = {
        "experiment_id": experiment_id,
        "n_trials": len(results["consensus_scores"]),
        "outlier_evaluator": None,
        "consensus_scores": results["consensus_scores"]
    }

    # Check if outlier was detected
    outlier_stats = results["dimensions"]["overall_score"]["outlier_detection"]
    for evaluator, stats_dict in outlier_stats.items():
        if stats_dict["is_outlier"]:
            consensus_data["outlier_evaluator"] = evaluator
            break

    with open(consensus_file, 'w') as f:
        json.dump(consensus_data, f, indent=2)

    print(f"✅ Consensus scores saved to: {consensus_file}")


if __name__ == "__main__":
    main()
