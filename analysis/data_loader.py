#!/usr/bin/env python3
"""
Data Loader for Analysis
Phase 0.4 - Step 2: Centralized data loading utility (ENSEMBLE SUPPORT)

Loads trial data from the migrated v2 structure for analysis.

Key Understanding:
- 120 trials total (5 scenarios × 5 constitutions × ~5 Layer2 models)
- FIVE evaluators (claude-sonnet-4-5, gpt-4o, deepseek-chat, grok-3, gemini-2-5-pro)
- Each trial is a unique combination of (scenario, constitution, layer2_model)
- Each trial has evaluations from all 5 evaluators (ensemble)
"""

import json
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class EvaluationScores:
    """Scores from Layer 3 evaluation."""
    evaluator_model: str
    factual_adherence: float
    value_transparency: float
    logical_coherence: float
    overall_score: float
    factual_explanation: Optional[str] = None
    transparency_explanation: Optional[str] = None
    coherence_explanation: Optional[str] = None

@dataclass
class TrialData:
    """Complete trial data (Layer 2 + Layer 3 with ENSEMBLE evaluations)."""
    trial_id: str
    scenario_id: str
    constitution: str
    layer2_model: str  # Model that did constitutional reasoning
    evaluations: Dict[str, EvaluationScores] = None  # Dict[evaluator_name, scores]

    def __post_init__(self):
        if self.evaluations is None:
            self.evaluations = {}

class ExperimentDataLoader:
    """Load trial data from migrated experiment structure."""

    def __init__(self, experiment_id: str = "exp_20251026_193228"):
        self.exp_path = Path("results/experiments") / experiment_id
        self.layer2_dir = self.exp_path / "data" / "layer2"
        self.layer3_dir = self.exp_path / "data" / "layer3"

        if not self.exp_path.exists():
            raise FileNotFoundError(f"Experiment not found: {experiment_id}")

    def load_trial(self, trial_id: str) -> TrialData:
        """Load single trial with Layer 2 and Layer 3 data (all evaluators)."""

        # Load Layer 2 (constitutional reasoning)
        layer2_file = self.layer2_dir / f"{trial_id}.json"
        if not layer2_file.exists():
            raise FileNotFoundError(f"Layer 2 file not found: {trial_id}")

        with open(layer2_file) as f:
            layer2 = json.load(f)

        # Load Layer 3 (evaluations from ALL evaluators)
        layer3_file = self.layer3_dir / f"{trial_id}.json"
        evaluations = {}

        if layer3_file.exists():
            with open(layer3_file) as f:
                layer3 = json.load(f)

            # Load evaluations from all evaluators (ensemble)
            for evaluator_name, eval_data in layer3.get("evaluations", {}).items():
                if eval_data.get("status") == "completed" and eval_data.get("response_parsed"):
                    parsed = eval_data["response_parsed"]

                    evaluations[evaluator_name] = EvaluationScores(
                        evaluator_model=evaluator_name,
                        factual_adherence=parsed["factual_adherence"]["score"],
                        value_transparency=parsed["value_transparency"]["score"],
                        logical_coherence=parsed["logical_coherence"]["score"],
                        overall_score=parsed["overall_score"],
                        factual_explanation=parsed["factual_adherence"].get("explanation"),
                        transparency_explanation=parsed["value_transparency"].get("explanation"),
                        coherence_explanation=parsed["logical_coherence"].get("explanation")
                    )

        return TrialData(
            trial_id=layer2["trial_id"],
            scenario_id=layer2["scenario_id"],
            constitution=layer2["constitution"],
            layer2_model=layer2["model"],
            evaluations=evaluations
        )

    def load_all_trials(self) -> List[TrialData]:
        """Load all trials with complete data."""

        trials = []
        trial_files = sorted(self.layer2_dir.glob("trial_*.json"))

        for trial_file in trial_files:
            trial_id = trial_file.stem
            try:
                trial = self.load_trial(trial_id)
                if trial.evaluations:  # Only include trials with at least 1 evaluation
                    trials.append(trial)
            except Exception as e:
                print(f"Warning: Failed to load {trial_id}: {e}")
                continue

        return trials

    def get_trial_dataframe(self, evaluator: Optional[str] = None) -> pd.DataFrame:
        """
        Convert trials to pandas DataFrame for analysis.

        Args:
            evaluator: If specified, only return rows for this evaluator.
                      If None, return one row per (trial, evaluator) pair.

        Returns DataFrame with columns:
        - trial_id
        - scenario_id
        - constitution
        - layer2_model
        - evaluator (claude-sonnet-4-5, gpt-4o, deepseek-chat, grok-3, gemini-2-5-pro)
        - factual_adherence
        - value_transparency
        - logical_coherence
        - overall_score
        """

        trials = self.load_all_trials()
        records = []

        for trial in trials:
            for eval_name, eval_scores in trial.evaluations.items():
                # Filter by evaluator if specified
                if evaluator and eval_name != evaluator:
                    continue

                records.append({
                    "trial_id": trial.trial_id,
                    "scenario_id": trial.scenario_id,
                    "constitution": trial.constitution,
                    "layer2_model": trial.layer2_model,
                    "evaluator": eval_name,
                    "factual_adherence": eval_scores.factual_adherence,
                    "value_transparency": eval_scores.value_transparency,
                    "logical_coherence": eval_scores.logical_coherence,
                    "overall_score": eval_scores.overall_score
                })

        return pd.DataFrame(records)

    def get_summary_stats(self) -> Dict:
        """Get summary statistics about the dataset."""

        df = self.get_trial_dataframe()

        return {
            "total_trials": len(df),
            "scenarios": sorted(df["scenario_id"].unique().tolist()),
            "constitutions": sorted(df["constitution"].unique().tolist()),
            "layer2_models": sorted(df["layer2_model"].unique().tolist()),
            "evaluators": sorted(df["evaluator"].unique().tolist()),
            "score_ranges": {
                "factual_adherence": {
                    "min": float(df["factual_adherence"].min()),
                    "max": float(df["factual_adherence"].max()),
                    "mean": float(df["factual_adherence"].mean())
                },
                "value_transparency": {
                    "min": float(df["value_transparency"].min()),
                    "max": float(df["value_transparency"].max()),
                    "mean": float(df["value_transparency"].mean())
                },
                "logical_coherence": {
                    "min": float(df["logical_coherence"].min()),
                    "max": float(df["logical_coherence"].max()),
                    "mean": float(df["logical_coherence"].mean())
                },
                "overall_score": {
                    "min": float(df["overall_score"].min()),
                    "max": float(df["overall_score"].max()),
                    "mean": float(df["overall_score"].mean())
                }
            }
        }

if __name__ == "__main__":
    # Test the data loader
    loader = ExperimentDataLoader()

    print("=== Testing Data Loader (Ensemble Support) ===\n")

    # Test single trial load
    print("Loading single trial (trial_001)...")
    trial = loader.load_trial("trial_001")
    print(f"  Trial ID: {trial.trial_id}")
    print(f"  Scenario: {trial.scenario_id}")
    print(f"  Constitution: {trial.constitution}")
    print(f"  Layer2 Model: {trial.layer2_model}")
    print(f"  Evaluators: {len(trial.evaluations)}")
    for eval_name, eval_scores in trial.evaluations.items():
        print(f"    {eval_name}: Overall Score = {eval_scores.overall_score}")
    print()

    # Test loading all trials
    print("Loading all trials...")
    trials = loader.load_all_trials()
    print(f"  Loaded {len(trials)} trials with complete data")
    total_evaluations = sum(len(t.evaluations) for t in trials)
    print(f"  Total evaluations: {total_evaluations}")
    print()

    # Test DataFrame conversion (all evaluators)
    print("Creating DataFrame (all evaluators)...")
    df = loader.get_trial_dataframe()
    print(f"  DataFrame shape: {df.shape}")
    print(f"  Columns: {df.columns.tolist()}")
    print(f"  Unique evaluators: {sorted(df['evaluator'].unique())}")
    print()

    # Test DataFrame conversion (single evaluator)
    print("Creating DataFrame (claude-sonnet-4-5 only)...")
    df_claude = loader.get_trial_dataframe(evaluator="claude-sonnet-4-5")
    print(f"  DataFrame shape: {df_claude.shape}")
    print()

    # Test summary stats
    print("Summary Statistics:")
    stats = loader.get_summary_stats()
    print(f"  Total rows (trial × evaluator): {stats['total_trials']}")
    print(f"  Scenarios ({len(stats['scenarios'])}): {', '.join(stats['scenarios'])}")
    print(f"  Constitutions ({len(stats['constitutions'])}): {', '.join(stats['constitutions'])}")
    print(f"  Layer2 Models ({len(stats['layer2_models'])}): {', '.join(stats['layer2_models'])}")
    print(f"  Evaluators ({len(stats['evaluators'])}): {', '.join(stats['evaluators'])}")
    print()
    print("Score Ranges (across all evaluators):")
    for dimension, ranges in stats['score_ranges'].items():
        print(f"  {dimension}: {ranges['min']:.0f}-{ranges['max']:.0f} (mean: {ranges['mean']:.1f})")
    print()

    print("✅ Data loader test complete!")
