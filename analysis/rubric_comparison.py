#!/usr/bin/env python3
"""
Rubric Comparison Analysis
Week 1, Task 1 of Analysis & Publication Plan

Compares three rubric formats:
- Likert (0-100 continuous scale)
- Binary (PASS/FAIL → 100/0)
- Ternary (PASS/PARTIAL/FAIL → 100/50/0)

Purpose: Identify which rubric format has highest inter-rater reliability
for human validation (Week 2-3).
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from itertools import combinations
from scipy import stats


@dataclass
class RubricScores:
    """Scores from one evaluator under one rubric format."""
    evaluator: str
    epistemic_integrity: float
    value_transparency: float
    overall_score: float


@dataclass
class TrialComparison:
    """Scores for one trial across all evaluators in one rubric format."""
    trial_id: str
    scenario_id: str
    constitution: str
    layer2_model: str
    scores: Dict[str, RubricScores]  # Dict[evaluator_name, scores]


class RubricComparisonAnalyzer:
    """Compare inter-rater reliability across rubric formats."""

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id

        # Find project root (handles running from notebooks/ or root)
        cwd = Path.cwd()
        if cwd.name == "notebooks":
            project_root = cwd.parent
        else:
            project_root = cwd

        self.exp_path = project_root / "results" / "experiments" / experiment_id

        # Three rubric directories
        self.likert_dir = self.exp_path / "data" / "layer3"
        self.binary_dir = self.exp_path / "data" / "layer3_binary"
        self.ternary_dir = self.exp_path / "data" / "layer3_ternary"

        # Verify all directories exist
        for rubric_name, rubric_dir in [
            ("Likert", self.likert_dir),
            ("Binary", self.binary_dir),
            ("Ternary", self.ternary_dir)
        ]:
            if not rubric_dir.exists():
                raise FileNotFoundError(
                    f"{rubric_name} directory not found: {rubric_dir}\n"
                    f"This analysis requires all 3 rubric formats to be present."
                )

    def load_likert_trial(self, trial_id: str) -> TrialComparison:
        """Load trial from Likert rubric (layer3/)."""

        trial_file = self.likert_dir / f"{trial_id}.json"
        if not trial_file.exists():
            raise FileNotFoundError(f"Likert trial not found: {trial_id}")

        with open(trial_file) as f:
            data = json.load(f)

        scores = {}
        for evaluator_name, eval_data in data.get("evaluations", {}).items():
            if eval_data.get("status") == "completed" and eval_data.get("response_parsed"):
                parsed = eval_data["response_parsed"]
                scores[evaluator_name] = RubricScores(
                    evaluator=evaluator_name,
                    epistemic_integrity=parsed["epistemicIntegrity"]["score"],
                    value_transparency=parsed["valueTransparency"]["score"],
                    overall_score=parsed["overallScore"]
                )

        return TrialComparison(
            trial_id=data["trial_id"],
            scenario_id=data["scenario_id"],
            constitution=data["constitution"],
            layer2_model=data["model"],
            scores=scores
        )

    def load_binary_trial(self, trial_id: str) -> TrialComparison:
        """Load trial from Binary rubric (layer3_binary/)."""

        trial_file = self.binary_dir / f"{trial_id}.json"
        if not trial_file.exists():
            raise FileNotFoundError(f"Binary trial not found: {trial_id}")

        with open(trial_file) as f:
            data = json.load(f)

        # Binary/Ternary files don't have constitution/layer2_model metadata
        # Load from corresponding Layer 2 file
        layer2_file = self.exp_path / "data" / "layer2" / f"{trial_id}.json"
        if layer2_file.exists():
            with open(layer2_file) as f:
                layer2_data = json.load(f)
            constitution = layer2_data.get("constitution", "unknown")
            layer2_model = layer2_data.get("model", "unknown")
        else:
            constitution = "unknown"
            layer2_model = "unknown"

        scores = {}
        for evaluator_name, eval_data in data.get("evaluations", {}).items():
            if eval_data.get("status") == "completed" and eval_data.get("response_parsed"):
                parsed = eval_data["response_parsed"]
                scores[evaluator_name] = RubricScores(
                    evaluator=evaluator_name,
                    epistemic_integrity=parsed["epistemicIntegrity"]["score"],
                    value_transparency=parsed["valueTransparency"]["score"],
                    overall_score=parsed["overallScore"]
                )

        return TrialComparison(
            trial_id=data["trialId"],
            scenario_id=data["scenarioId"],
            constitution=constitution,
            layer2_model=layer2_model,
            scores=scores
        )

    def load_ternary_trial(self, trial_id: str) -> TrialComparison:
        """Load trial from Ternary rubric (layer3_ternary/)."""

        trial_file = self.ternary_dir / f"{trial_id}.json"
        if not trial_file.exists():
            raise FileNotFoundError(f"Ternary trial not found: {trial_id}")

        with open(trial_file) as f:
            data = json.load(f)

        # Binary/Ternary files don't have constitution/layer2_model metadata
        # Load from corresponding Layer 2 file
        layer2_file = self.exp_path / "data" / "layer2" / f"{trial_id}.json"
        if layer2_file.exists():
            with open(layer2_file) as f:
                layer2_data = json.load(f)
            constitution = layer2_data.get("constitution", "unknown")
            layer2_model = layer2_data.get("model", "unknown")
        else:
            constitution = "unknown"
            layer2_model = "unknown"

        scores = {}
        for evaluator_name, eval_data in data.get("evaluations", {}).items():
            if eval_data.get("status") == "completed" and eval_data.get("response_parsed"):
                parsed = eval_data["response_parsed"]
                scores[evaluator_name] = RubricScores(
                    evaluator=evaluator_name,
                    epistemic_integrity=parsed["epistemicIntegrity"]["score"],
                    value_transparency=parsed["valueTransparency"]["score"],
                    overall_score=parsed["overallScore"]
                )

        return TrialComparison(
            trial_id=data["trialId"],
            scenario_id=data["scenarioId"],
            constitution=constitution,
            layer2_model=layer2_model,
            scores=scores
        )

    def load_all_trials_for_rubric(self, rubric_format: str) -> List[TrialComparison]:
        """Load all trials for a given rubric format."""

        if rubric_format == "likert":
            directory = self.likert_dir
            load_fn = self.load_likert_trial
        elif rubric_format == "binary":
            directory = self.binary_dir
            load_fn = self.load_binary_trial
        elif rubric_format == "ternary":
            directory = self.ternary_dir
            load_fn = self.load_ternary_trial
        else:
            raise ValueError(f"Unknown rubric format: {rubric_format}")

        trials = []
        trial_files = sorted(directory.glob("trial_*.json"))

        for trial_file in trial_files:
            trial_id = trial_file.stem
            try:
                trial = load_fn(trial_id)
                if trial.scores:  # Only include if has at least 1 evaluation
                    trials.append(trial)
            except Exception as e:
                print(f"Warning: Failed to load {rubric_format} {trial_id}: {e}")
                continue

        return trials

    def calculate_pairwise_correlations(
        self,
        trials: List[TrialComparison],
        dimension: str = "overall_score"
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate Pearson r between all evaluator pairs.

        Args:
            trials: List of trials with scores
            dimension: 'epistemic_integrity', 'value_transparency', or 'overall_score'

        Returns:
            Dict mapping (evaluator1, evaluator2) → correlation coefficient
        """

        # Build matrix: rows=trials, cols=evaluators
        evaluators = set()
        for trial in trials:
            evaluators.update(trial.scores.keys())
        evaluators = sorted(evaluators)

        # Create score matrix
        score_matrix = {}
        for evaluator in evaluators:
            score_matrix[evaluator] = []
            for trial in trials:
                if evaluator in trial.scores:
                    score = getattr(trial.scores[evaluator], dimension)
                    score_matrix[evaluator].append(score)
                else:
                    score_matrix[evaluator].append(np.nan)

        # Calculate pairwise correlations
        correlations = {}
        for eval1, eval2 in combinations(evaluators, 2):
            scores1 = np.array(score_matrix[eval1])
            scores2 = np.array(score_matrix[eval2])

            # Remove pairs with missing data
            mask = ~(np.isnan(scores1) | np.isnan(scores2))
            scores1_clean = scores1[mask]
            scores2_clean = scores2[mask]

            if len(scores1_clean) >= 10:  # Minimum 10 shared trials
                r, p = stats.pearsonr(scores1_clean, scores2_clean)
                correlations[(eval1, eval2)] = r
            else:
                correlations[(eval1, eval2)] = np.nan

        return correlations

    def calculate_icc(
        self,
        trials: List[TrialComparison],
        dimension: str = "overall_score"
    ) -> float:
        """
        Calculate Intraclass Correlation Coefficient (ICC).

        ICC measures absolute agreement between raters (not just rank correlation).
        Formula: ICC(2,1) = (MSR - MSE) / (MSR + (k-1)*MSE)

        Where:
        - MSR = Mean Square for Rows (between-trial variance)
        - MSE = Mean Square Error (within-trial variance)
        - k = number of raters (evaluators)
        """

        # Build matrix: rows=trials, cols=evaluators
        evaluators = set()
        for trial in trials:
            evaluators.update(trial.scores.keys())
        evaluators = sorted(evaluators)
        k = len(evaluators)

        # Create score matrix (n trials × k evaluators)
        scores_list = []
        valid_trials = []

        for trial in trials:
            trial_scores = []
            complete = True
            for evaluator in evaluators:
                if evaluator in trial.scores:
                    score = getattr(trial.scores[evaluator], dimension)
                    trial_scores.append(score)
                else:
                    complete = False
                    break

            if complete:
                scores_list.append(trial_scores)
                valid_trials.append(trial.trial_id)

        if len(scores_list) < 2:
            return np.nan

        scores_matrix = np.array(scores_list)  # Shape: (n_trials, n_evaluators)
        n = len(scores_matrix)

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
        icc = (msr - mse) / (msr + (k - 1) * mse)

        return icc

    def calculate_score_variance(
        self,
        trials: List[TrialComparison],
        dimension: str = "overall_score"
    ) -> Dict[str, float]:
        """
        Calculate score variance (discriminative power).

        Higher variance = rubric uses full range of scale (good discriminative power)
        Lower variance = rubric compresses scores (poor discrimination)
        """

        all_scores = []
        for trial in trials:
            for evaluator, scores in trial.scores.items():
                score = getattr(scores, dimension)
                all_scores.append(score)

        if not all_scores:
            return {
                "mean": np.nan,
                "std": np.nan,
                "variance": np.nan,
                "min": np.nan,
                "max": np.nan
            }

        return {
            "mean": float(np.mean(all_scores)),
            "std": float(np.std(all_scores)),
            "variance": float(np.var(all_scores)),
            "min": float(np.min(all_scores)),
            "max": float(np.max(all_scores))
        }

    def analyze_rubric(self, rubric_format: str) -> Dict:
        """Complete analysis for one rubric format."""

        print(f"\n{'='*60}")
        print(f"Analyzing: {rubric_format.upper()} Rubric")
        print('='*60)

        trials = self.load_all_trials_for_rubric(rubric_format)
        print(f"Loaded {len(trials)} trials")

        results = {
            "rubric_format": rubric_format,
            "n_trials": len(trials),
            "dimensions": {}
        }

        for dimension in ["epistemic_integrity", "value_transparency", "overall_score"]:
            print(f"\n--- {dimension.replace('_', ' ').title()} ---")

            # Pairwise correlations
            correlations = self.calculate_pairwise_correlations(trials, dimension)
            valid_corrs = [r for r in correlations.values() if not np.isnan(r)]

            if valid_corrs:
                mean_r = np.mean(valid_corrs)
                std_r = np.std(valid_corrs)
                min_r = np.min(valid_corrs)
                max_r = np.max(valid_corrs)

                print(f"  Pairwise Correlations (Pearson r):")
                print(f"    Mean r: {mean_r:.3f} (±{std_r:.3f})")
                print(f"    Range:  [{min_r:.3f}, {max_r:.3f}]")
            else:
                mean_r = std_r = min_r = max_r = np.nan
                print(f"  Pairwise Correlations: Insufficient data")

            # ICC
            icc = self.calculate_icc(trials, dimension)
            if not np.isnan(icc):
                print(f"  ICC(2,1): {icc:.3f}")
            else:
                print(f"  ICC(2,1): Insufficient data")

            # Score variance (discriminative power)
            variance_stats = self.calculate_score_variance(trials, dimension)
            print(f"  Score Distribution:")
            if not np.isnan(variance_stats['mean']):
                print(f"    Mean:  {variance_stats['mean']:.1f}")
                print(f"    Std:   {variance_stats['std']:.1f}")
                print(f"    Range: [{variance_stats['min']:.0f}, {variance_stats['max']:.0f}]")
            else:
                print(f"    No data available")

            results["dimensions"][dimension] = {
                "pairwise_correlations": {
                    "mean": mean_r,
                    "std": std_r,
                    "min": min_r,
                    "max": max_r,
                    "all_pairs": {f"{e1}_vs_{e2}": r for (e1, e2), r in correlations.items()}
                },
                "icc": icc,
                "score_distribution": variance_stats
            }

        return results

    def compare_all_rubrics(self) -> Dict:
        """Run complete comparison across all three rubric formats."""

        print("="*60)
        print("RUBRIC COMPARISON ANALYSIS")
        print(f"Experiment: {self.experiment_id}")
        print("="*60)

        results = {
            "experiment_id": self.experiment_id,
            "rubrics": {}
        }

        for rubric_format in ["likert", "binary", "ternary"]:
            results["rubrics"][rubric_format] = self.analyze_rubric(rubric_format)

        # Summary comparison
        print(f"\n{'='*60}")
        print("SUMMARY: Inter-Rater Reliability Comparison")
        print('='*60)

        for dimension in ["epistemic_integrity", "value_transparency", "overall_score"]:
            print(f"\n{dimension.replace('_', ' ').title()}:")
            for rubric_format in ["likert", "binary", "ternary"]:
                mean_r = results["rubrics"][rubric_format]["dimensions"][dimension]["pairwise_correlations"]["mean"]
                icc = results["rubrics"][rubric_format]["dimensions"][dimension]["icc"]
                print(f"  {rubric_format.capitalize():8} → Mean r: {mean_r:.3f}, ICC: {icc:.3f}")

        return results


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analysis/rubric_comparison.py <experiment_id>")
        print("\nExample: python analysis/rubric_comparison.py exp_20251028_134615")
        sys.exit(1)

    experiment_id = sys.argv[1]

    analyzer = RubricComparisonAnalyzer(experiment_id)
    results = analyzer.compare_all_rubrics()

    # Save results
    output_dir = Path("results/experiments") / experiment_id / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "rubric_comparison.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
