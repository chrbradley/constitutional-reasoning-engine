"""
Layer 3 Evaluator Comparison Analysis

Compares multiple Layer 3 evaluators on identical Layer 2 outputs to assess:
- Inter-rater reliability (Pearson correlation, Intraclass correlation)
- Ranking consistency (Kendall's Tau, Spearman's rho)
- Systematic bias detection
- Agreement on extreme cases (best/worst trials)

Usage:
    python -m analysis.compare_evaluators --experiment exp_20251026_123456
"""
import argparse
import json
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import sys

# Statistical functions
try:
    from scipy.stats import pearsonr, spearmanr, kendalltau
    from scipy.stats import f_oneway
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("Warning: scipy not installed. Using basic correlation only.")
    print("Install with: pip install scipy")


@dataclass
class EvaluatorScore:
    """Single evaluator's scores for a trial"""
    evaluator_id: str
    trial_id: str
    scenario_id: str
    constitution_id: str
    model_id: str

    factual_adherence: float
    value_transparency: float
    logical_coherence: float
    overall_score: float


class EvaluatorComparison:
    """Compare multiple Layer 3 evaluators on the same trials"""

    def __init__(self, experiment_dir: Path):
        self.experiment_dir = experiment_dir
        self.data_dir = experiment_dir / "data"
        self.layer3_dir = self.data_dir / "layer3" / "parsed"

        # Storage for results grouped by evaluator
        self.evaluator_scores: Dict[str, List[EvaluatorScore]] = defaultdict(list)

    def load_evaluator_results(self) -> None:
        """
        Load all Layer 3 results, grouped by evaluator

        Directory structure:
            - Primary evaluator: layer3/parsed/*.json
            - Additional evaluators: layer3/{evaluator_id}/parsed/*.json
        """
        layer3_base = self.data_dir / "layer3"
        if not layer3_base.exists():
            raise ValueError(f"Layer 3 directory not found: {layer3_base}")

        # Load primary evaluator results from layer3/parsed/
        primary_parsed = layer3_base / "parsed"
        if primary_parsed.exists():
            for result_file in primary_parsed.glob("*.json"):
                self._load_result_file(result_file)

        # Load additional evaluator results from layer3/{evaluator_id}/parsed/
        for evaluator_dir in layer3_base.iterdir():
            if evaluator_dir.is_dir() and evaluator_dir.name not in ["raw", "parsed"]:
                # This is an evaluator subdirectory
                eval_parsed = evaluator_dir / "parsed"
                if eval_parsed.exists():
                    for result_file in eval_parsed.glob("*.json"):
                        self._load_result_file(result_file)

        print(f"Loaded results from {len(self.evaluator_scores)} evaluators:")
        for evaluator_id, scores in self.evaluator_scores.items():
            print(f"  - {evaluator_id}: {len(scores)} trials")

    def _load_result_file(self, result_file: Path) -> None:
        """Load a single result JSON file"""
        with open(result_file) as f:
            data = json.load(f)

        trial_id = data.get("testId")
        evaluator_id = data.get("evaluationModel")

        if not evaluator_id:
            print(f"Warning: No evaluator ID in {result_file.name}, skipping")
            return

        integrity = data.get("integrityEvaluation", {})

        # Extract scores
        score = EvaluatorScore(
            evaluator_id=evaluator_id,
            trial_id=trial_id,
            scenario_id=data.get("scenario_id", "unknown"),
            constitution_id=data.get("constitution_id", "unknown"),
            model_id=data.get("model_id", "unknown"),
            factual_adherence=integrity.get("factualAdherence", {}).get("score", -1),
            value_transparency=integrity.get("valueTransparency", {}).get("score", -1),
            logical_coherence=integrity.get("logicalCoherence", {}).get("score", -1),
            overall_score=integrity.get("overallScore", -1)
        )

        self.evaluator_scores[evaluator_id].append(score)

    def get_common_trials(self) -> Dict[str, Dict[str, EvaluatorScore]]:
        """
        Get trials that were evaluated by ALL evaluators

        Returns:
            Dict[trial_id, Dict[evaluator_id, EvaluatorScore]]
        """
        # Find trials present in all evaluators
        evaluator_ids = list(self.evaluator_scores.keys())
        if len(evaluator_ids) < 2:
            raise ValueError("Need at least 2 evaluators to compare")

        # Get trial IDs for each evaluator
        evaluator_trials = {
            eval_id: {score.trial_id for score in scores}
            for eval_id, scores in self.evaluator_scores.items()
        }

        # Find intersection (trials evaluated by ALL evaluators)
        common_trial_ids = set.intersection(*evaluator_trials.values())

        print(f"\nCommon trials evaluated by all {len(evaluator_ids)} evaluators: {len(common_trial_ids)}")

        # Build lookup: trial_id -> {evaluator_id -> EvaluatorScore}
        common_trials = {}
        for trial_id in common_trial_ids:
            common_trials[trial_id] = {}
            for eval_id, scores in self.evaluator_scores.items():
                matching_scores = [s for s in scores if s.trial_id == trial_id]
                if matching_scores:
                    common_trials[trial_id][eval_id] = matching_scores[0]

        return common_trials

    def calculate_pairwise_correlation(
        self,
        common_trials: Dict[str, Dict[str, EvaluatorScore]],
        score_dimension: str = "overall_score"
    ) -> Dict[Tuple[str, str], float]:
        """
        Calculate Pearson correlation between all pairs of evaluators

        Args:
            common_trials: Output from get_common_trials()
            score_dimension: Which score to compare (overall_score, factual_adherence, etc.)

        Returns:
            Dict[(evaluator1, evaluator2), correlation_coefficient]
        """
        evaluator_ids = list(self.evaluator_scores.keys())
        correlations = {}

        for i, eval1 in enumerate(evaluator_ids):
            for eval2 in evaluator_ids[i+1:]:
                # Extract paired scores
                eval1_scores = []
                eval2_scores = []

                for trial_id, evaluators in common_trials.items():
                    if eval1 in evaluators and eval2 in evaluators:
                        score1 = getattr(evaluators[eval1], score_dimension)
                        score2 = getattr(evaluators[eval2], score_dimension)

                        # Skip invalid scores (-1)
                        if score1 >= 0 and score2 >= 0:
                            eval1_scores.append(score1)
                            eval2_scores.append(score2)

                # Calculate correlation
                if len(eval1_scores) > 1:
                    if HAS_SCIPY:
                        r, p_value = pearsonr(eval1_scores, eval2_scores)
                        correlations[(eval1, eval2)] = {"r": r, "p_value": p_value, "n": len(eval1_scores)}
                    else:
                        # Simple correlation without p-value
                        r = self._simple_correlation(eval1_scores, eval2_scores)
                        correlations[(eval1, eval2)] = {"r": r, "p_value": None, "n": len(eval1_scores)}

        return correlations

    def _simple_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation without scipy"""
        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denom_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
        denom_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5

        if denom_x == 0 or denom_y == 0:
            return 0.0

        return numerator / (denom_x * denom_y)

    def calculate_mean_absolute_error(
        self,
        common_trials: Dict[str, Dict[str, EvaluatorScore]],
        score_dimension: str = "overall_score"
    ) -> Dict[Tuple[str, str], float]:
        """Calculate mean absolute error between evaluator pairs"""
        evaluator_ids = list(self.evaluator_scores.keys())
        mae_results = {}

        for i, eval1 in enumerate(evaluator_ids):
            for eval2 in evaluator_ids[i+1:]:
                errors = []

                for trial_id, evaluators in common_trials.items():
                    if eval1 in evaluators and eval2 in evaluators:
                        score1 = getattr(evaluators[eval1], score_dimension)
                        score2 = getattr(evaluators[eval2], score_dimension)

                        if score1 >= 0 and score2 >= 0:
                            errors.append(abs(score1 - score2))

                if errors:
                    mae_results[(eval1, eval2)] = {
                        "mae": statistics.mean(errors),
                        "stdev": statistics.stdev(errors) if len(errors) > 1 else 0,
                        "n": len(errors)
                    }

        return mae_results

    def detect_systematic_bias(
        self,
        common_trials: Dict[str, Dict[str, EvaluatorScore]],
        score_dimension: str = "overall_score"
    ) -> Dict[str, Dict]:
        """
        Detect if an evaluator systematically scores higher/lower than others

        Returns:
            Dict[evaluator_id, {mean_score, mean_difference_from_others, bias_direction}]
        """
        evaluator_ids = list(self.evaluator_scores.keys())
        bias_analysis = {}

        for eval_id in evaluator_ids:
            eval_scores = []
            other_scores = []

            for trial_id, evaluators in common_trials.items():
                if eval_id in evaluators:
                    eval_score = getattr(evaluators[eval_id], score_dimension)

                    # Get average of other evaluators for this trial
                    other_eval_scores = [
                        getattr(evaluators[other_id], score_dimension)
                        for other_id in evaluator_ids
                        if other_id != eval_id and other_id in evaluators
                    ]
                    other_eval_scores = [s for s in other_eval_scores if s >= 0]

                    if eval_score >= 0 and other_eval_scores:
                        eval_scores.append(eval_score)
                        other_scores.append(statistics.mean(other_eval_scores))

            if eval_scores:
                mean_eval = statistics.mean(eval_scores)
                mean_others = statistics.mean(other_scores)
                difference = mean_eval - mean_others

                bias_analysis[eval_id] = {
                    "mean_score": round(mean_eval, 2),
                    "mean_others": round(mean_others, 2),
                    "difference": round(difference, 2),
                    "bias_direction": "higher" if difference > 0 else "lower" if difference < 0 else "neutral",
                    "n_trials": len(eval_scores)
                }

        return bias_analysis

    def generate_comparison_report(self, output_path: Optional[Path] = None) -> Dict:
        """Generate comprehensive comparison report"""
        common_trials = self.get_common_trials()

        if not common_trials:
            return {"error": "No common trials found across evaluators"}

        # Calculate metrics for each score dimension
        dimensions = ["overall_score", "factual_adherence", "value_transparency", "logical_coherence"]

        report = {
            "experiment_dir": str(self.experiment_dir),
            "evaluators": list(self.evaluator_scores.keys()),
            "common_trial_count": len(common_trials),
            "dimensions": {}
        }

        for dimension in dimensions:
            correlations = self.calculate_pairwise_correlation(common_trials, dimension)
            mae = self.calculate_mean_absolute_error(common_trials, dimension)
            bias = self.detect_systematic_bias(common_trials, dimension)

            report["dimensions"][dimension] = {
                "pairwise_correlations": {
                    f"{e1} vs {e2}": corr for (e1, e2), corr in correlations.items()
                },
                "mean_absolute_error": {
                    f"{e1} vs {e2}": mae_stats for (e1, e2), mae_stats in mae.items()
                },
                "systematic_bias": bias
            }

        # Add recommendation
        overall_correlations = report["dimensions"]["overall_score"]["pairwise_correlations"]
        min_correlation = min(stats["r"] for stats in overall_correlations.values())
        mean_correlation = statistics.mean(stats["r"] for stats in overall_correlations.values())

        if mean_correlation >= 0.90:
            recommendation = "HIGH AGREEMENT: Evaluators show strong consistency. Cheaper alternatives are likely valid."
        elif mean_correlation >= 0.75:
            recommendation = "MODERATE AGREEMENT: Consider full-scale validation (Phase 2) before switching evaluators."
        else:
            recommendation = "LOW AGREEMENT: Evaluators show significant divergence. Recommend sticking with trusted evaluator."

        report["summary"] = {
            "min_correlation": round(min_correlation, 3),
            "mean_correlation": round(mean_correlation, 3),
            "recommendation": recommendation
        }

        # Save report
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n✅ Report saved to: {output_path}")

        return report

    def print_summary(self, report: Dict) -> None:
        """Print human-readable summary"""
        print("\n" + "="*80)
        print("LAYER 3 EVALUATOR COMPARISON REPORT")
        print("="*80)

        print(f"\nEvaluators: {', '.join(report['evaluators'])}")
        print(f"Common trials analyzed: {report['common_trial_count']}")

        print("\n" + "-"*80)
        print("OVERALL SCORE CORRELATIONS")
        print("-"*80)

        overall = report["dimensions"]["overall_score"]
        for pair, stats in overall["pairwise_correlations"].items():
            r = stats["r"]
            n = stats["n"]
            print(f"{pair:50s} r={r:.3f} (n={n})")

        print("\n" + "-"*80)
        print("MEAN ABSOLUTE ERROR (Overall Score)")
        print("-"*80)

        for pair, stats in overall["mean_absolute_error"].items():
            mae = stats["mae"]
            stdev = stats["stdev"]
            print(f"{pair:50s} MAE={mae:.2f} ± {stdev:.2f}")

        print("\n" + "-"*80)
        print("SYSTEMATIC BIAS DETECTION (Overall Score)")
        print("-"*80)

        for eval_id, bias_stats in overall["systematic_bias"].items():
            direction = bias_stats["bias_direction"]
            diff = bias_stats["difference"]
            mean = bias_stats["mean_score"]
            print(f"{eval_id:30s} Mean={mean:.1f}, Bias={diff:+.2f} ({direction})")

        print("\n" + "="*80)
        print("RECOMMENDATION")
        print("="*80)
        print(f"\n{report['summary']['recommendation']}")
        print(f"\nMean correlation: {report['summary']['mean_correlation']:.3f}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Compare multiple Layer 3 evaluators on the same trials"
    )
    parser.add_argument("--experiment", "-e", required=True, help="Experiment ID to analyze")
    parser.add_argument("--output", "-o", help="Output JSON file path")

    args = parser.parse_args()

    # Find experiment directory
    experiment_dir = Path("results/experiments") / args.experiment
    if not experiment_dir.exists():
        print(f"❌ Error: Experiment directory not found: {experiment_dir}")
        sys.exit(1)

    # Run comparison
    comparison = EvaluatorComparison(experiment_dir)
    comparison.load_evaluator_results()

    # Generate output path
    output_path = None
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = experiment_dir / "analysis" / "evaluator_comparison.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate and print report
    report = comparison.generate_comparison_report(output_path)
    comparison.print_summary(report)


if __name__ == "__main__":
    main()
