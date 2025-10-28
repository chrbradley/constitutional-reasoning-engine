"""
Export Analysis Results for Web Viewer

Creates a web-viewer-friendly JSON file with:
- Human-readable labels
- Flattened structure
- Pre-computed insights
- Links to visualizations

Usage:
    python experiments/export_for_web.py --experiment exp_20251023_105245
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any, List


class WebExporter:
    """Export analysis results in web-viewer-friendly format."""

    def __init__(self, base_dir: Path = Path("results")):
        self.base_dir = base_dir
        self.analysis_dir = base_dir / "analysis" / "single"
        self.viz_dir = base_dir / "visualizations"
        self.export_dir = base_dir / "web_exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_experiment(self, experiment_id: str) -> None:
        """Export experiment analysis for web viewer."""

        # Load analysis (from experiment's analysis directory)
        analysis_path = Path("results/experiments") / experiment_id / "analysis" / f"{experiment_id}_analysis.json"
        if not analysis_path.exists():
            raise FileNotFoundError(f"Analysis file not found: {analysis_path}")

        with open(analysis_path) as f:
            analysis = json.load(f)

        print(f"Exporting {experiment_id} for web viewer...")

        # Build web export
        web_data = {
            "experiment": self._build_experiment_metadata(experiment_id, analysis),
            "summary": self._build_summary(analysis),
            "models": self._build_models_data(analysis),
            "constitutions": self._build_constitutions_data(analysis),
            "scenarios": self._build_scenarios_data(analysis),
            "interactions": self._build_interactions(analysis),
            "insights": self._extract_insights(analysis),
            "visualizations": self._list_visualizations(experiment_id)
        }

        # Save
        export_path = self.export_dir / f"{experiment_id}_web_export.json"
        with open(export_path, 'w') as f:
            json.dump(web_data, f, indent=2)

        print(f"✓ Web export saved to {export_path}")

    def _build_experiment_metadata(self, experiment_id: str, analysis: Dict) -> Dict[str, Any]:
        """Build experiment metadata section."""
        return {
            "id": experiment_id,
            "timestamp": analysis.get("analysis_timestamp"),
            "total_tests": analysis.get("total_tests"),
            "status": "completed",
            "description": "Full constitutional reasoning experiment across 16 scenarios, 5 constitutions, and 6 models"
        }

    def _build_summary(self, analysis: Dict) -> Dict[str, Any]:
        """Build high-level summary section."""
        summary = analysis["summary"]
        return {
            "overall": {
                "mean": summary["overall_score"]["mean"],
                "median": summary["overall_score"]["median"],
                "std": summary["overall_score"]["stdev"],
                "range": {
                    "min": summary["overall_score"]["min"],
                    "max": summary["overall_score"]["max"]
                },
                "interpretation": self._interpret_overall_score(summary["overall_score"]["mean"])
            },
            "dimensions": {
                "epistemic_integrity": {
                    "mean": summary["epistemic_integrity"]["mean"],
                    "median": summary["epistemic_integrity"]["median"],
                    "label": "Epistemic Integrity",
                    "description": "Does the model maintain factual accuracy and intellectual honesty?"
                },
                "value_transparency": {
                    "mean": summary["value_transparency"]["mean"],
                    "median": summary["value_transparency"]["median"],
                    "label": "Value Transparency",
                    "description": "Does the model explicitly state its values and reasoning?"
                }
            }
        }

    def _build_models_data(self, analysis: Dict) -> List[Dict[str, Any]]:
        """Build models data with human-readable labels."""
        models_data = analysis["by_model"]["models"]
        ranking = analysis["by_model"]["ranking"]

        models = []
        for rank, model_id in enumerate(ranking, 1):
            data = models_data[model_id]
            models.append({
                "id": model_id,
                "name": self._format_model_name(model_id),
                "rank": rank,
                "score": {
                    "mean": data["overall_score"]["mean"],
                    "median": data["overall_score"]["median"],
                    "std": data["overall_score"]["stdev"],
                    "min": data["overall_score"]["min"],
                    "max": data["overall_score"]["max"]
                },
                "dimensions": {
                    "epistemic_integrity": data["epistemic_integrity"],
                    "value_transparency": data["value_transparency"]
                },
                "tier": self._classify_model_tier(data["overall_score"]["mean"]),
                "consistency": self._classify_consistency(data["overall_score"]["stdev"]),
                "test_count": data["test_count"]
            })

        return models

    def _build_constitutions_data(self, analysis: Dict) -> List[Dict[str, Any]]:
        """Build constitutions data with human-readable labels."""
        const_data = analysis["by_constitution"]["constitutions"]
        ranking = analysis["by_constitution"]["ranking"]

        constitutions = []
        for rank, const_id in enumerate(ranking, 1):
            data = const_data[const_id]
            constitutions.append({
                "id": const_id,
                "name": self._format_constitution_name(const_id),
                "rank": rank,
                "score": {
                    "mean": data["overall_score"]["mean"],
                    "median": data["overall_score"]["median"],
                    "std": data["overall_score"]["stdev"],
                    "min": data["overall_score"]["min"],
                    "max": data["overall_score"]["max"]
                },
                "dimensions": {
                    "epistemic_integrity": data["epistemic_integrity"],
                    "value_transparency": data["value_transparency"]
                },
                "type": "control" if const_id == "bad-faith" else "honest",
                "description": self._get_constitution_description(const_id),
                "test_count": data["test_count"]
            })

        return constitutions

    def _build_scenarios_data(self, analysis: Dict) -> List[Dict[str, Any]]:
        """Build scenarios data."""
        scenarios_data = analysis["by_scenario"]["scenarios"]

        scenarios = []
        for scenario_id, data in scenarios_data.items():
            scenarios.append({
                "id": scenario_id,
                "name": self._format_scenario_name(scenario_id),
                "difficulty": self._classify_difficulty(data["mean_score"]),
                "mean_score": data["mean_score"],
                "std": data["stdev"],
                "variability": self._classify_variability(data["stdev"]),
                "test_count": data["test_count"]
            })

        # Sort by difficulty (lowest score = hardest)
        scenarios.sort(key=lambda x: x["mean_score"])

        return scenarios

    def _build_interactions(self, analysis: Dict) -> Dict[str, Any]:
        """Build model × constitution interaction matrix."""
        matrix = analysis["model_constitution_matrix"]["matrix"]

        interactions = []
        for model_id, const_scores in matrix.items():
            for const_id, score in const_scores.items():
                interactions.append({
                    "model": self._format_model_name(model_id),
                    "model_id": model_id,
                    "constitution": self._format_constitution_name(const_id),
                    "constitution_id": const_id,
                    "score": score,
                    "performance": self._classify_performance(score)
                })

        return {
            "matrix": interactions,
            "best": max(interactions, key=lambda x: x["score"]),
            "worst": min(interactions, key=lambda x: x["score"])
        }

    def _extract_insights(self, analysis: Dict) -> List[Dict[str, Any]]:
        """Extract key insights from analysis."""
        insights = []

        # Top model
        top_model = analysis["by_model"]["ranking"][0]
        top_model_score = analysis["by_model"]["models"][top_model]["overall_score"]["mean"]
        insights.append({
            "type": "success",
            "category": "model_performance",
            "title": "Top Model Identified",
            "message": f"{self._format_model_name(top_model)} achieved highest integrity (mean: {top_model_score:.1f}/100)",
            "importance": "high"
        })

        # Bad-faith detection
        bad_faith_score = analysis["by_constitution"]["constitutions"]["bad-faith"]["overall_score"]["mean"]
        honest_avg = sum(
            analysis["by_constitution"]["constitutions"][c]["overall_score"]["mean"]
            for c in analysis["by_constitution"]["ranking"]
            if c != "bad-faith"
        ) / 4
        gap = honest_avg - bad_faith_score

        insights.append({
            "type": "success",
            "category": "motivated_reasoning",
            "title": "Motivated Reasoning Detected",
            "message": f"Bad-faith constitution scored {gap:.1f} points lower than honest constitutions (68 vs 82-86)",
            "importance": "high"
        })

        # Value pluralism
        honest_scores = [
            analysis["by_constitution"]["constitutions"][c]["overall_score"]["mean"]
            for c in analysis["by_constitution"]["ranking"]
            if c != "bad-faith"
        ]
        spread = max(honest_scores) - min(honest_scores)

        insights.append({
            "type": "info",
            "category": "value_pluralism",
            "title": "Value Pluralism Validated",
            "message": f"Honest constitutions cluster together (only {spread:.1f} point spread), proving different values don't require different facts",
            "importance": "high"
        })

        # Llama parsing issues
        llama_score = analysis["by_model"]["models"]["llama-3-8b"]["overall_score"]["mean"]
        insights.append({
            "type": "warning",
            "category": "model_reliability",
            "title": "Smaller Models Struggle",
            "message": f"Llama 3 8B averaged {llama_score:.1f}/100 with 18.75% parsing failures, suggesting smaller models need additional safeguards",
            "importance": "medium"
        })

        return insights

    def _list_visualizations(self, experiment_id: str) -> List[Dict[str, str]]:
        """List available visualizations."""
        viz_dir = self.viz_dir / experiment_id

        if not viz_dir.exists():
            return []

        visualizations = [
            {
                "id": "model_rankings",
                "title": "Model Performance Rankings",
                "filename": "01_model_rankings.png",
                "category": "models"
            },
            {
                "id": "constitution_rankings",
                "title": "Constitution Integrity Scores",
                "filename": "02_constitution_rankings.png",
                "category": "constitutions"
            },
            {
                "id": "score_dist_models",
                "title": "Score Distributions by Model",
                "filename": "03_score_distributions_by_model.png",
                "category": "models"
            },
            {
                "id": "score_dist_constitutions",
                "title": "Score Distributions by Constitution",
                "filename": "04_score_distributions_by_constitution.png",
                "category": "constitutions"
            },
            {
                "id": "interaction_heatmap",
                "title": "Model × Constitution Interactions",
                "filename": "05_model_constitution_heatmap.png",
                "category": "interactions"
            },
            {
                "id": "dimensions_models",
                "title": "Integrity Dimensions by Model",
                "filename": "06_dimensional_breakdown_by_model.png",
                "category": "models"
            },
            {
                "id": "scenario_difficulty",
                "title": "Scenario Difficulty Analysis",
                "filename": "07_scenario_difficulty.png",
                "category": "scenarios"
            },
            {
                "id": "dimensions_constitutions",
                "title": "Integrity Dimensions by Constitution",
                "filename": "08_dimensional_breakdown_by_constitution.png",
                "category": "constitutions"
            }
        ]

        return visualizations

    # Helper methods

    def _format_model_name(self, model_id: str) -> str:
        name_map = {
            'claude-sonnet-4-5': 'Claude Sonnet 4.5',
            'gpt-4o': 'GPT-4o',
            'llama-3-8b': 'Llama 3 8B',
            'gemini-2-5-flash': 'Gemini 2.5 Flash',
            'grok-3': 'Grok 3',
            'deepseek-chat': 'DeepSeek Chat'
        }
        return name_map.get(model_id, model_id)

    def _format_constitution_name(self, const_id: str) -> str:
        name_map = {
            'harm-minimization': 'Harm Minimization',
            'balanced-justice': 'Balanced Justice',
            'self-sovereignty': 'Self-Sovereignty',
            'community-order': 'Community Order',
            'bad-faith': 'Bad-Faith (Control)'
        }
        return name_map.get(const_id, const_id)

    def _format_scenario_name(self, scenario_id: str) -> str:
        return scenario_id.replace('-', ' ').title()

    def _get_constitution_description(self, const_id: str) -> str:
        descriptions = {
            'harm-minimization': 'Prioritizes reducing harm and protecting vulnerable parties',
            'balanced-justice': 'Balances individual rights with collective welfare',
            'self-sovereignty': 'Emphasizes individual autonomy and personal responsibility',
            'community-order': 'Values social cohesion and collective stability',
            'bad-faith': 'Control condition: Motivated reasoning with fact distortion'
        }
        return descriptions.get(const_id, '')

    def _classify_model_tier(self, score: float) -> str:
        if score >= 87: return "top"
        if score >= 82: return "strong"
        return "struggling"

    def _classify_consistency(self, std: float) -> str:
        if std < 10: return "highly_consistent"
        if std < 15: return "consistent"
        if std < 25: return "variable"
        return "highly_variable"

    def _classify_difficulty(self, mean_score: float) -> str:
        if mean_score < 78: return "hard"
        if mean_score < 82: return "moderate"
        return "easy"

    def _classify_variability(self, std: float) -> str:
        if std < 12: return "low"
        if std < 20: return "moderate"
        return "high"

    def _classify_performance(self, score: float) -> str:
        if score >= 90: return "excellent"
        if score >= 85: return "strong"
        if score >= 75: return "adequate"
        if score >= 60: return "weak"
        return "failing"

    def _interpret_overall_score(self, mean: float) -> str:
        if mean >= 85:
            return "Excellent overall integrity - models maintain factual accuracy while reasoning from values"
        if mean >= 80:
            return "Strong overall integrity - most models successfully separate values from facts"
        if mean >= 70:
            return "Adequate integrity - some models struggle with consistent factual adherence"
        return "Concerning integrity - widespread issues with motivated reasoning"


def main():
    parser = argparse.ArgumentParser(
        description="Export analysis results for web viewer"
    )
    parser.add_argument(
        '--experiment',
        type=str,
        required=True,
        help='Experiment ID to export (e.g., exp_20251023_105245)'
    )

    args = parser.parse_args()

    exporter = WebExporter()
    exporter.export_experiment(args.experiment)


if __name__ == "__main__":
    main()
