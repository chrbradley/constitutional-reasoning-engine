"""
Multi-Experiment Analysis System

Supports both single-experiment and multi-experiment aggregation:
- Analyze individual experiment runs in isolation
- Aggregate statistics across multiple runs
- Generate visualizations and summary reports
- Export data for web viewer
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import statistics

from src.core.scenarios import load_scenarios

@dataclass
class TestResult:
    """Single test result with all metadata"""
    trial_id: str
    experiment_id: str
    scenario_id: str
    constitution_id: str
    model_id: str
    timestamp: str

    # Integrity scores
    factual_adherence: float
    value_transparency: float
    logical_coherence: float
    overall_score: float

    # Metadata
    parse_statuses: Dict[str, str]

    # Dimensional metadata (from scenario)
    scale: str  # personal, community, societal
    directionality: str  # internal, external, mixed
    severity: str  # low, medium, medium-high, high


class ExperimentAnalyzer:
    """Analyze single or multiple experiment runs"""

    def __init__(self, results_dir: Path = Path("results")):
        self.results_dir = results_dir
        self.experiments_dir = results_dir / "experiments"
        self.aggregate_dir = results_dir / "aggregate"

        # Create directories
        self.aggregate_dir.mkdir(parents=True, exist_ok=True)

        # Load scenario metadata once
        self.scenarios = {s.id: s for s in load_scenarios()}

    def discover_experiments(self) -> List[str]:
        """Discover all experiment IDs in results/experiments/"""
        if not self.experiments_dir.exists():
            return []

        experiments = []
        for exp_dir in self.experiments_dir.iterdir():
            if exp_dir.is_dir() and exp_dir.name.startswith("exp_"):
                experiments.append(exp_dir.name)

        return sorted(experiments)

    def load_experiment_results(self, experiment_id: str) -> List[TestResult]:
        """Load all test results from a single experiment"""
        registry_path = self.experiments_dir / experiment_id / "data" / "tests"

        if not registry_path.exists():
            raise ValueError(f"Experiment {experiment_id} not found")

        results = []

        # Load all raw JSON files
        for result_file in registry_path.glob("*.json"):
            try:
                with open(result_file) as f:
                    data = json.load(f)

                # Extract test metadata
                trial_id = data.get("testId")
                scenario_id = data["scenario"]["id"]
                constitution_id = data["constitution"]
                model_id = data["model"]

                # Get scenario for dimensional data
                scenario = self.scenarios.get(scenario_id)

                # Extract integrity scores
                integrity = data["integrityEvaluation"]

                result = TestResult(
                    trial_id=trial_id,
                    experiment_id=experiment_id,
                    scenario_id=scenario_id,
                    constitution_id=constitution_id,
                    model_id=model_id,
                    timestamp=data.get("timestamp", ""),
                    factual_adherence=integrity["factualAdherence"]["score"],
                    value_transparency=integrity["valueTransparency"]["score"],
                    logical_coherence=integrity["logicalCoherence"]["score"],
                    overall_score=integrity.get("overallScore",
                        (integrity["factualAdherence"]["score"] +
                         integrity["valueTransparency"]["score"] +
                         integrity["logicalCoherence"]["score"]) / 3),
                    parse_statuses=data.get("parseStatuses", {}),
                    scale=scenario.category if scenario else "unknown",
                    directionality="unknown",  # Not in current scenario schema
                    severity="unknown"  # Not in current scenario schema
                )

                results.append(result)

            except Exception as e:
                print(f"Warning: Failed to load {result_file}: {e}")
                continue

        return results

    def analyze_single_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Complete statistical analysis for single experiment"""

        results = self.load_experiment_results(experiment_id)

        if not results:
            return {"error": "No results found", "experiment_id": experiment_id}

        analysis = {
            "experiment_id": experiment_id,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "summary": self._calculate_summary_stats(results),
            "by_model": self._aggregate_by_model(results),
            "by_constitution": self._aggregate_by_constitution(results),
            "by_scenario": self._aggregate_by_scenario(results),
            "by_scale": self._aggregate_by_dimension(results, "scale"),
            "model_constitution_matrix": self._create_interaction_matrix(results),
            "top_scores": self._get_top_scores(results, n=10),
            "bottom_scores": self._get_bottom_scores(results, n=10)
        }

        return analysis

    def analyze_multiple_experiments(self, experiment_ids: List[str]) -> Dict[str, Any]:
        """Aggregate analysis across multiple experiments"""

        all_results = []
        experiment_summaries = []

        for exp_id in experiment_ids:
            try:
                results = self.load_experiment_results(exp_id)
                all_results.extend(results)

                # Store per-experiment summary
                experiment_summaries.append({
                    "experiment_id": exp_id,
                    "test_count": len(results),
                    "mean_overall_score": statistics.mean([r.overall_score for r in results])
                })
            except Exception as e:
                print(f"Warning: Skipping experiment {exp_id}: {e}")
                continue

        if not all_results:
            return {"error": "No results found across experiments"}

        analysis = {
            "analysis_type": "multi_experiment",
            "experiment_ids": experiment_ids,
            "experiment_count": len(experiment_ids),
            "analysis_timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results),
            "per_experiment_summaries": experiment_summaries,
            "aggregated_summary": self._calculate_summary_stats(all_results),
            "by_model": self._aggregate_by_model(all_results),
            "by_constitution": self._aggregate_by_constitution(all_results),
            "by_scenario": self._aggregate_by_scenario(all_results),
            "by_scale": self._aggregate_by_dimension(all_results, "scale"),
            "model_constitution_matrix": self._create_interaction_matrix(all_results),
            "variance_analysis": self._calculate_variance_across_experiments(experiment_ids)
        }

        return analysis

    def _calculate_summary_stats(self, results: List[TestResult]) -> Dict[str, Any]:
        """Calculate overall summary statistics"""

        overall_scores = [r.overall_score for r in results]
        factual_scores = [r.factual_adherence for r in results]
        value_scores = [r.value_transparency for r in results]
        logic_scores = [r.logical_coherence for r in results]

        return {
            "overall_score": {
                "mean": round(statistics.mean(overall_scores), 2),
                "median": round(statistics.median(overall_scores), 2),
                "stdev": round(statistics.stdev(overall_scores), 2) if len(overall_scores) > 1 else 0,
                "min": round(min(overall_scores), 2),
                "max": round(max(overall_scores), 2)
            },
            "factual_adherence": {
                "mean": round(statistics.mean(factual_scores), 2),
                "median": round(statistics.median(factual_scores), 2),
                "stdev": round(statistics.stdev(factual_scores), 2) if len(factual_scores) > 1 else 0
            },
            "value_transparency": {
                "mean": round(statistics.mean(value_scores), 2),
                "median": round(statistics.median(value_scores), 2),
                "stdev": round(statistics.stdev(value_scores), 2) if len(value_scores) > 1 else 0
            },
            "logical_coherence": {
                "mean": round(statistics.mean(logic_scores), 2),
                "median": round(statistics.median(logic_scores), 2),
                "stdev": round(statistics.stdev(logic_scores), 2) if len(logic_scores) > 1 else 0
            }
        }

    def _aggregate_by_model(self, results: List[TestResult]) -> Dict[str, Any]:
        """Aggregate statistics by model"""

        model_groups = {}
        for result in results:
            if result.model_id not in model_groups:
                model_groups[result.model_id] = []
            model_groups[result.model_id].append(result)

        model_stats = {}
        for model_id, model_results in model_groups.items():
            overall_scores = [r.overall_score for r in model_results]
            factual_scores = [r.factual_adherence for r in model_results]
            value_scores = [r.value_transparency for r in model_results]
            logic_scores = [r.logical_coherence for r in model_results]

            model_stats[model_id] = {
                "test_count": len(model_results),
                "overall_score": {
                    "mean": round(statistics.mean(overall_scores), 2),
                    "median": round(statistics.median(overall_scores), 2),
                    "stdev": round(statistics.stdev(overall_scores), 2) if len(overall_scores) > 1 else 0,
                    "min": round(min(overall_scores), 2),
                    "max": round(max(overall_scores), 2)
                },
                "factual_adherence": round(statistics.mean(factual_scores), 2),
                "value_transparency": round(statistics.mean(value_scores), 2),
                "logical_coherence": round(statistics.mean(logic_scores), 2)
            }

        # Sort by mean overall score
        sorted_models = sorted(model_stats.items(),
                              key=lambda x: x[1]["overall_score"]["mean"],
                              reverse=True)

        return {"models": dict(sorted_models), "ranking": [m[0] for m in sorted_models]}

    def _aggregate_by_constitution(self, results: List[TestResult]) -> Dict[str, Any]:
        """Aggregate statistics by constitution"""

        const_groups = {}
        for result in results:
            if result.constitution_id not in const_groups:
                const_groups[result.constitution_id] = []
            const_groups[result.constitution_id].append(result)

        const_stats = {}
        for const_id, const_results in const_groups.items():
            overall_scores = [r.overall_score for r in const_results]
            factual_scores = [r.factual_adherence for r in const_results]
            value_scores = [r.value_transparency for r in const_results]
            logic_scores = [r.logical_coherence for r in const_results]

            const_stats[const_id] = {
                "test_count": len(const_results),
                "overall_score": {
                    "mean": round(statistics.mean(overall_scores), 2),
                    "median": round(statistics.median(overall_scores), 2),
                    "stdev": round(statistics.stdev(overall_scores), 2) if len(overall_scores) > 1 else 0,
                    "min": round(min(overall_scores), 2),
                    "max": round(max(overall_scores), 2)
                },
                "factual_adherence": round(statistics.mean(factual_scores), 2),
                "value_transparency": round(statistics.mean(value_scores), 2),
                "logical_coherence": round(statistics.mean(logic_scores), 2)
            }

        # Sort by mean overall score
        sorted_consts = sorted(const_stats.items(),
                              key=lambda x: x[1]["overall_score"]["mean"],
                              reverse=True)

        return {"constitutions": dict(sorted_consts), "ranking": [c[0] for c in sorted_consts]}

    def _aggregate_by_scenario(self, results: List[TestResult]) -> Dict[str, Any]:
        """Aggregate statistics by scenario"""

        scenario_groups = {}
        for result in results:
            if result.scenario_id not in scenario_groups:
                scenario_groups[result.scenario_id] = []
            scenario_groups[result.scenario_id].append(result)

        scenario_stats = {}
        for scenario_id, scenario_results in scenario_groups.items():
            overall_scores = [r.overall_score for r in scenario_results]

            scenario_stats[scenario_id] = {
                "test_count": len(scenario_results),
                "mean_score": round(statistics.mean(overall_scores), 2),
                "stdev": round(statistics.stdev(overall_scores), 2) if len(overall_scores) > 1 else 0,
                "min": round(min(overall_scores), 2),
                "max": round(max(overall_scores), 2),
                "score_range": round(max(overall_scores) - min(overall_scores), 2)
            }

        return {"scenarios": scenario_stats}

    def _aggregate_by_dimension(self, results: List[TestResult], dimension: str) -> Dict[str, Any]:
        """Aggregate by dimensional property (scale, directionality, severity)"""

        dim_groups = {}
        for result in results:
            dim_value = getattr(result, dimension)
            if dim_value not in dim_groups:
                dim_groups[dim_value] = []
            dim_groups[dim_value].append(result)

        dim_stats = {}
        for dim_value, dim_results in dim_groups.items():
            overall_scores = [r.overall_score for r in dim_results]

            dim_stats[dim_value] = {
                "test_count": len(dim_results),
                "mean_score": round(statistics.mean(overall_scores), 2),
                "stdev": round(statistics.stdev(overall_scores), 2) if len(overall_scores) > 1 else 0
            }

        return {dimension: dim_stats}

    def _create_interaction_matrix(self, results: List[TestResult]) -> Dict[str, Any]:
        """Create model × constitution interaction matrix"""

        matrix = {}
        for result in results:
            if result.model_id not in matrix:
                matrix[result.model_id] = {}
            if result.constitution_id not in matrix[result.model_id]:
                matrix[result.model_id][result.constitution_id] = []

            matrix[result.model_id][result.constitution_id].append(result.overall_score)

        # Calculate means for each cell
        matrix_means = {}
        for model_id, const_dict in matrix.items():
            matrix_means[model_id] = {}
            for const_id, scores in const_dict.items():
                matrix_means[model_id][const_id] = round(statistics.mean(scores), 2)

        return {"matrix": matrix_means}

    def _get_top_scores(self, results: List[TestResult], n: int = 10) -> List[Dict[str, Any]]:
        """Get top N highest-scoring tests"""
        sorted_results = sorted(results, key=lambda r: r.overall_score, reverse=True)

        return [{
            "trial_id": r.trial_id,
            "scenario": r.scenario_id,
            "constitution": r.constitution_id,
            "model": r.model_id,
            "score": r.overall_score
        } for r in sorted_results[:n]]

    def _get_bottom_scores(self, results: List[TestResult], n: int = 10) -> List[Dict[str, Any]]:
        """Get bottom N lowest-scoring tests"""
        sorted_results = sorted(results, key=lambda r: r.overall_score)

        return [{
            "trial_id": r.trial_id,
            "scenario": r.scenario_id,
            "constitution": r.constitution_id,
            "model": r.model_id,
            "score": r.overall_score
        } for r in sorted_results[:n]]

    def _calculate_variance_across_experiments(self, experiment_ids: List[str]) -> Dict[str, Any]:
        """Calculate how much variance exists across different experiment runs"""

        # For each model/constitution combination, get mean scores from each experiment
        combo_scores = {}

        for exp_id in experiment_ids:
            try:
                results = self.load_experiment_results(exp_id)

                for result in results:
                    key = f"{result.model_id}_{result.constitution_id}"
                    if key not in combo_scores:
                        combo_scores[key] = []
                    combo_scores[key].append(result.overall_score)
            except:
                continue

        # Calculate variance for each combination
        variance_stats = {}
        for combo_key, scores in combo_scores.items():
            if len(scores) > 1:
                variance_stats[combo_key] = {
                    "mean": round(statistics.mean(scores), 2),
                    "stdev": round(statistics.stdev(scores), 2),
                    "min": round(min(scores), 2),
                    "max": round(max(scores), 2),
                    "range": round(max(scores) - min(scores), 2)
                }

        return {"variance_by_combination": variance_stats}

    def save_analysis(self, analysis: Dict[str, Any], filename: str):
        """Save analysis to JSON file"""
        # Single experiment: save to experiment's analysis directory
        if analysis.get("analysis_type") == "single_experiment":
            experiment_id = analysis.get("experiment_id")
            output_path = self.experiments_dir / experiment_id / "analysis" / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
        # Multi-experiment: save to aggregate directory
        else:
            output_path = self.aggregate_dir / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)

        print(f"✅ Analysis saved to {output_path}")
        return output_path


def main():
    """CLI for running analysis"""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze experiment results")
    parser.add_argument("--experiment", "-e", help="Analyze single experiment ID")
    parser.add_argument("--all", action="store_true", help="Analyze all experiments")
    parser.add_argument("--experiments", "-m", nargs="+", help="Analyze multiple specific experiments")
    parser.add_argument("--output", "-o", help="Output filename (default: auto-generated)")

    args = parser.parse_args()

    analyzer = ExperimentAnalyzer()

    if args.experiment:
        # Single experiment analysis
        print(f"Analyzing experiment: {args.experiment}")
        analysis = analyzer.analyze_single_experiment(args.experiment)

        output_file = args.output or f"{args.experiment}_analysis.json"
        analyzer.save_analysis(analysis, output_file)

        # Print summary
        print(f"\nSummary for {args.experiment}:")
        print(f"Total tests: {analysis['total_tests']}")
        print(f"Overall mean score: {analysis['summary']['overall_score']['mean']}")

    elif args.all:
        # All experiments aggregated
        experiment_ids = analyzer.discover_experiments()
        print(f"Found {len(experiment_ids)} experiments: {experiment_ids}")

        analysis = analyzer.analyze_multiple_experiments(experiment_ids)

        output_file = args.output or f"all_experiments_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        analyzer.save_analysis(analysis, output_file)

        # Print summary
        print(f"\nAggregated Summary across {len(experiment_ids)} experiments:")
        print(f"Total tests: {analysis['total_tests']}")
        print(f"Overall mean score: {analysis['aggregated_summary']['overall_score']['mean']}")

    elif args.experiments:
        # Specific experiments aggregated
        print(f"Analyzing experiments: {args.experiments}")

        analysis = analyzer.analyze_multiple_experiments(args.experiments)

        output_file = args.output or f"custom_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        analyzer.save_analysis(analysis, output_file)

        # Print summary
        print(f"\nAggregated Summary:")
        print(f"Total tests: {analysis['total_tests']}")
        print(f"Overall mean score: {analysis['aggregated_summary']['overall_score']['mean']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
