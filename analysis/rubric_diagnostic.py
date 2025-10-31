#!/usr/bin/env python3
"""
Rubric Diagnostic Analysis
Investigates why Binary rubric underperformed vs Likert (contradicts literature)

Hypotheses to test:
1. Ceiling effects: Binary PASS rate too high (>90%)
2. Evaluator bias: Specific evaluators inflate scores
3. Data loading errors: Files loaded incorrectly
4. Context effects: Certain scenarios/constitutions break Binary
5. Prompt quality: Binary prompts less clear than Likert
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

from rubric_comparison import RubricComparisonAnalyzer


class RubricDiagnostic:
    """Diagnostic analysis for rubric comparison anomalies."""

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.analyzer = RubricComparisonAnalyzer(experiment_id)
        self.exp_path = Path("results/experiments") / experiment_id

    def check_pass_rates(self) -> Dict:
        """
        Hypothesis 1: Ceiling effects

        Check if Binary rubric has excessive PASS rates (>90%)
        causing loss of discriminative power.
        """
        print("\n" + "="*60)
        print("DIAGNOSTIC 1: Ceiling Effects (PASS Rate Analysis)")
        print("="*60)

        results = {}

        for rubric_format in ['binary', 'ternary']:
            print(f"\n{rubric_format.upper()} Rubric:")

            trials = self.analyzer.load_all_trials_for_rubric(rubric_format)

            # Calculate PASS rates per dimension
            for dimension in ['epistemic_integrity', 'value_transparency', 'overall_score']:
                all_scores = []
                for trial in trials:
                    for evaluator, scores in trial.scores.items():
                        score = getattr(scores, dimension)
                        all_scores.append(score)

                if not all_scores:
                    continue

                all_scores = np.array(all_scores)

                # PASS rate (score == 100 or score >= threshold)
                if rubric_format == 'binary':
                    pass_threshold = 100
                else:  # ternary
                    pass_threshold = 100

                pass_rate = (all_scores == pass_threshold).sum() / len(all_scores)
                near_ceiling_rate = (all_scores >= 90).sum() / len(all_scores)

                results[f"{rubric_format}_{dimension}"] = {
                    "pass_rate": pass_rate,
                    "near_ceiling_rate": near_ceiling_rate,
                    "mean": np.mean(all_scores),
                    "unique_values": len(np.unique(all_scores))
                }

                print(f"  {dimension.replace('_', ' ').title()}:")
                print(f"    PASS rate (score=100): {pass_rate:.1%}")
                print(f"    Near-ceiling rate (score≥90): {near_ceiling_rate:.1%}")
                print(f"    Mean: {np.mean(all_scores):.1f}")
                print(f"    Unique values: {len(np.unique(all_scores))}")

                # Flag if problematic
                if pass_rate > 0.90:
                    print(f"    ⚠️  WARNING: Ceiling effect detected (>90% PASS)")
                if len(np.unique(all_scores)) < 5:
                    print(f"    ⚠️  WARNING: Low discriminative power (<5 unique values)")

        # Compare with Likert
        print(f"\nLIKERT Rubric (for comparison):")
        likert_trials = self.analyzer.load_all_trials_for_rubric('likert')

        for dimension in ['epistemic_integrity', 'value_transparency', 'overall_score']:
            all_scores = []
            for trial in likert_trials:
                for evaluator, scores in trial.scores.items():
                    score = getattr(scores, dimension)
                    all_scores.append(score)

            if not all_scores:
                continue

            all_scores = np.array(all_scores)
            near_ceiling_rate = (all_scores >= 90).sum() / len(all_scores)

            print(f"  {dimension.replace('_', ' ').title()}:")
            print(f"    Near-ceiling rate (score≥90): {near_ceiling_rate:.1%}")
            print(f"    Mean: {np.mean(all_scores):.1f}")
            print(f"    Unique values: {len(np.unique(all_scores))}")

        return results

    def check_evaluator_bias(self) -> Dict:
        """
        Hypothesis 2: Evaluator bias

        Check if specific evaluators systematically inflate Binary scores
        (e.g., Gemini scoring everything PASS).
        """
        print("\n" + "="*60)
        print("DIAGNOSTIC 2: Evaluator Bias (Per-Evaluator PASS Rates)")
        print("="*60)

        results = defaultdict(dict)

        for rubric_format in ['binary', 'likert']:
            print(f"\n{rubric_format.upper()} Rubric:")

            trials = self.analyzer.load_all_trials_for_rubric(rubric_format)

            # Group scores by evaluator
            evaluator_scores = defaultdict(lambda: defaultdict(list))

            for trial in trials:
                for evaluator, scores in trial.scores.items():
                    evaluator_scores[evaluator]['epistemic_integrity'].append(scores.epistemic_integrity)
                    evaluator_scores[evaluator]['value_transparency'].append(scores.value_transparency)
                    evaluator_scores[evaluator]['overall_score'].append(scores.overall_score)

            # Analyze each evaluator
            for evaluator in sorted(evaluator_scores.keys()):
                print(f"\n  {evaluator}:")

                for dimension in ['epistemic_integrity', 'value_transparency', 'overall_score']:
                    scores = np.array(evaluator_scores[evaluator][dimension])

                    if rubric_format == 'binary':
                        pass_rate = (scores == 100).sum() / len(scores)
                        print(f"    {dimension}: PASS rate = {pass_rate:.1%}, Mean = {np.mean(scores):.1f}")

                        if pass_rate > 0.95:
                            print(f"      ⚠️  WARNING: {evaluator} scores {pass_rate:.0%} PASS")
                    else:  # likert
                        mean_score = np.mean(scores)
                        std_score = np.std(scores)
                        print(f"    {dimension}: Mean = {mean_score:.1f}, SD = {std_score:.1f}")

                results[rubric_format][evaluator] = {
                    'mean_overall': float(np.mean(evaluator_scores[evaluator]['overall_score'])),
                    'std_overall': float(np.std(evaluator_scores[evaluator]['overall_score']))
                }

        return dict(results)

    def check_data_integrity(self) -> Dict:
        """
        Hypothesis 3: Data loading errors

        Verify files loaded correctly and match expected structure.
        """
        print("\n" + "="*60)
        print("DIAGNOSTIC 3: Data Integrity Check")
        print("="*60)

        results = {}

        for rubric_format in ['likert', 'binary', 'ternary']:
            print(f"\n{rubric_format.upper()} Rubric:")

            trials = self.analyzer.load_all_trials_for_rubric(rubric_format)

            # Count evaluators per trial
            evaluator_counts = []
            evaluator_sets = []

            for trial in trials:
                evaluator_counts.append(len(trial.scores))
                evaluator_sets.append(set(trial.scores.keys()))

            # Check consistency
            expected_evaluators = {'claude-sonnet-4-5', 'gpt-4o', 'gemini-2-5-pro', 'grok-3', 'deepseek-chat'}
            all_have_5 = all(count == 5 for count in evaluator_counts)
            all_same_set = all(eval_set == expected_evaluators for eval_set in evaluator_sets)

            print(f"  Total trials loaded: {len(trials)}")
            print(f"  Expected trials: 360")
            print(f"  All trials have 5 evaluators: {all_have_5}")
            print(f"  All trials have same evaluator set: {all_same_set}")

            if not all_have_5:
                print(f"    ⚠️  WARNING: Some trials missing evaluators")
                missing_count = sum(1 for c in evaluator_counts if c < 5)
                print(f"    Trials with <5 evaluators: {missing_count}")

            if not all_same_set:
                print(f"    ⚠️  WARNING: Evaluator sets inconsistent")
                unique_sets = set(frozenset(s) for s in evaluator_sets)
                print(f"    Unique evaluator combinations: {len(unique_sets)}")

            # Check score ranges
            all_scores = []
            for trial in trials:
                for scores in trial.scores.values():
                    all_scores.append(scores.overall_score)

            all_scores = np.array(all_scores)

            print(f"  Score range: [{np.min(all_scores):.0f}, {np.max(all_scores):.0f}]")
            print(f"  Mean: {np.mean(all_scores):.1f}")
            print(f"  Parsing failures (-1 scores): {(all_scores == -1).sum()}")

            results[rubric_format] = {
                'trial_count': len(trials),
                'all_have_5_evaluators': all_have_5,
                'consistent_evaluators': all_same_set,
                'score_range': [float(np.min(all_scores)), float(np.max(all_scores))],
                'parsing_failures': int((all_scores == -1).sum())
            }

        return results

    def check_context_effects(self) -> Dict:
        """
        Hypothesis 4: Context effects

        Check if specific scenarios or constitutions cause Binary to fail.
        """
        print("\n" + "="*60)
        print("DIAGNOSTIC 4: Context Effects (Scenario/Constitution)")
        print("="*60)

        results = {}

        for rubric_format in ['binary', 'likert']:
            print(f"\n{rubric_format.upper()} Rubric:")

            trials = self.analyzer.load_all_trials_for_rubric(rubric_format)

            # Group by constitution
            constitution_scores = defaultdict(list)
            for trial in trials:
                for scores in trial.scores.values():
                    constitution_scores[trial.constitution].append(scores.overall_score)

            print(f"\n  By Constitution:")
            for constitution in sorted(constitution_scores.keys()):
                scores = np.array(constitution_scores[constitution])
                mean_score = np.mean(scores)
                std_score = np.std(scores)

                if rubric_format == 'binary':
                    pass_rate = (scores == 100).sum() / len(scores)
                    print(f"    {constitution:30} → Mean: {mean_score:.1f}, PASS: {pass_rate:.0%}")
                else:
                    print(f"    {constitution:30} → Mean: {mean_score:.1f}, SD: {std_score:.1f}")

            # Group by scenario
            scenario_scores = defaultdict(list)
            for trial in trials:
                for scores in trial.scores.values():
                    scenario_scores[trial.scenario_id].append(scores.overall_score)

            print(f"\n  By Scenario:")
            for scenario in sorted(scenario_scores.keys()):
                scores = np.array(scenario_scores[scenario])
                mean_score = np.mean(scores)
                std_score = np.std(scores)

                if rubric_format == 'binary':
                    pass_rate = (scores == 100).sum() / len(scores)
                    print(f"    {scenario:50} → Mean: {mean_score:.1f}, PASS: {pass_rate:.0%}")
                else:
                    print(f"    {scenario:50} → Mean: {mean_score:.1f}, SD: {std_score:.1f}")

        return results

    def compare_prompt_quality(self) -> Dict:
        """
        Hypothesis 5: Prompt quality

        Check if Binary prompts were less clear than Likert prompts.
        This requires manual inspection of prompts.
        """
        print("\n" + "="*60)
        print("DIAGNOSTIC 5: Prompt Quality (Manual Inspection Required)")
        print("="*60)

        print("\nBinary and Ternary evaluation prompts are located in:")
        print("  src/core/prompts.py")
        print("\nManual checks:")
        print("  1. Are Binary PASS/FAIL criteria clearly defined?")
        print("  2. Are threshold examples provided?")
        print("  3. Is Likert prompt more detailed/structured?")
        print("  4. Do prompts have different levels of guidance?")
        print("\n⚠️  This diagnostic requires manual code review")

        return {
            "status": "manual_review_required",
            "files_to_check": ["src/core/prompts.py"]
        }

    def run_all_diagnostics(self) -> Dict:
        """Run complete diagnostic suite."""

        print("\n" + "="*70)
        print("RUBRIC DIAGNOSTIC SUITE")
        print(f"Experiment: {self.experiment_id}")
        print("="*70)
        print("\nInvestigating why Binary rubric underperformed vs Likert")
        print("(Contradicts prevailing research expectations)")

        results = {
            "experiment_id": self.experiment_id,
            "diagnostics": {}
        }

        # Run diagnostics
        results["diagnostics"]["ceiling_effects"] = self.check_pass_rates()
        results["diagnostics"]["evaluator_bias"] = self.check_evaluator_bias()
        results["diagnostics"]["data_integrity"] = self.check_data_integrity()
        results["diagnostics"]["context_effects"] = self.check_context_effects()
        results["diagnostics"]["prompt_quality"] = self.compare_prompt_quality()

        # Summary
        print("\n" + "="*70)
        print("DIAGNOSTIC SUMMARY")
        print("="*70)

        # Check for ceiling effects
        binary_ei = results["diagnostics"]["ceiling_effects"].get("binary_epistemic_integrity", {})
        if binary_ei.get("pass_rate", 0) > 0.90:
            print("\n✅ CONFIRMED: Ceiling effect in Binary rubric")
            print(f"   Binary Epistemic Integrity PASS rate: {binary_ei['pass_rate']:.1%}")
            print("   → Almost everything scored PASS, destroying discriminative power")

        # Check for evaluator bias
        binary_eval = results["diagnostics"]["evaluator_bias"].get("binary", {})
        inflated_evaluators = [
            eval_name for eval_name, stats in binary_eval.items()
            if stats['mean_overall'] > 98
        ]
        if inflated_evaluators:
            print(f"\n✅ CONFIRMED: Evaluator bias detected")
            print(f"   Evaluators with >98 mean: {', '.join(inflated_evaluators)}")

        # Check data integrity
        data_issues = []
        for rubric, stats in results["diagnostics"]["data_integrity"].items():
            if stats['trial_count'] != 360:
                data_issues.append(f"{rubric}: {stats['trial_count']} trials (expected 360)")
            if not stats['all_have_5_evaluators']:
                data_issues.append(f"{rubric}: Missing evaluators in some trials")

        if data_issues:
            print(f"\n⚠️  WARNING: Data integrity issues")
            for issue in data_issues:
                print(f"   {issue}")
        else:
            print(f"\n✅ PASSED: Data integrity check")
            print("   All rubrics have 360 trials with 5 evaluators each")

        # Save results
        output_dir = self.exp_path / "analysis"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "rubric_diagnostic.json"

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n📁 Results saved to: {output_file}")

        return results


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analysis/rubric_diagnostic.py <experiment_id>")
        print("\nExample: python analysis/rubric_diagnostic.py exp_20251028_134615")
        sys.exit(1)

    experiment_id = sys.argv[1]

    diagnostic = RubricDiagnostic(experiment_id)
    results = diagnostic.run_all_diagnostics()


if __name__ == "__main__":
    main()
