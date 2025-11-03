#!/usr/bin/env python3
"""
Master script to generate all publication-quality figures.

Generates 12 figures for the research report and exports JSON data for web app.
Figures are saved to docs/figures/ in both PNG (300 DPI) and SVG formats.

Usage:
    python analysis/generate_figures.py [experiment_id]

Example:
    python analysis/generate_figures.py exp_20251028_134615
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Import configuration
from visualization_config import (
    FIGURES_DIR,
    WEB_DATA_DIR,
    EXPERIMENT_DIR,
    FIGURE_LIST,
    apply_publication_style,
    save_figure,
    JSON_INDENT,
    JSON_ENSURE_ASCII,
)

# Import existing analysis modules
# (We'll add these as we extract visualization code)
# from rubric_comparison import RubricComparisonAnalyzer
# from evaluator_agreement import EvaluatorAgreementAnalyzer
# from interaction_analysis import InteractionAnalyzer
# from dimensional_analysis import DimensionalAnalyzer


def setup_environment():
    """Set up matplotlib environment for publication-quality figures."""
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend

    apply_publication_style()
    print("✅ Publication style applied")


def validate_experiment(experiment_id: str):
    """Validate experiment directory exists and has required data."""
    exp_path = Path("results/experiments") / experiment_id

    if not exp_path.exists():
        raise FileNotFoundError(
            f"Experiment not found: {exp_path}\n"
            f"Please check the experiment ID and try again."
        )

    # Check for required directories
    required_dirs = [
        exp_path / "data" / "layer3",
        exp_path / "data" / "layer3_binary",
        exp_path / "data" / "layer3_ternary",
    ]

    missing_dirs = [d for d in required_dirs if not d.exists()]
    if missing_dirs:
        raise FileNotFoundError(
            f"Missing required directories:\n" +
            "\n".join(f"  - {d}" for d in missing_dirs)
        )

    print(f"✅ Experiment validated: {experiment_id}")
    return exp_path


# ============================================================================
# Figure Generation Functions
# ============================================================================

def generate_figure_01_rubric_comparison(experiment_id: str):
    """
    Figure 1: Rubric Format Comparison
    Bar chart comparing ICC values across Likert, Ternary, Binary rubrics.
    """
    print("\n📊 Generating Figure 1: Rubric Comparison...")

    # TODO: Extract from rubric_comparison.py
    # For now, placeholder
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(10, 6))

    rubrics = ['Likert\n(0-100)', 'Ternary\n(Pass/Partial/Fail)', 'Binary\n(Pass/Fail)']
    icc_values = [0.68, 0.60, 0.19]
    ci_lower = [0.62, 0.53, 0.11]
    ci_upper = [0.73, 0.66, 0.27]

    # Calculate error bars
    errors = [
        [icc_values[i] - ci_lower[i] for i in range(3)],
        [ci_upper[i] - icc_values[i] for i in range(3)]
    ]

    colors = ['#0173B2', '#F39C12', '#E74C3C']  # Blue, Orange, Red

    ax.bar(rubrics, icc_values, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    ax.errorbar(rubrics, icc_values, yerr=errors, fmt='none', ecolor='black',
                capsize=5, capthick=2, linewidth=2)

    ax.set_ylabel('Inter-Rater Reliability (ICC)', fontsize=12)
    ax.set_title('Rubric Format Comparison', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1.0)
    ax.axhline(y=0.70, color='gray', linestyle='--', linewidth=1, alpha=0.7, label='Good reliability (0.70)')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    save_figure(fig, '01_rubric_comparison')
    plt.close(fig)

    # Export data for web app
    web_data = {
        'rubrics': ['likert', 'ternary', 'binary'],
        'display_names': rubrics,
        'icc_values': icc_values,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'generated': datetime.now().isoformat(),
    }

    export_web_data('rubric_comparison.json', web_data)

    print("✅ Figure 1 complete")


def generate_figure_02_model_constitution_heatmap(experiment_id: str):
    """
    Figure 2: Model × Constitution Interaction Heatmap
    Shows mean overall scores across 5 models and 6 constitutions.
    """
    print("\n📊 Generating Figure 2: Model × Constitution Heatmap...")

    # TODO: Extract from interaction_analysis.py
    print("⏭️  Figure 2 - TODO: Extract from interaction_analysis.py")


def generate_figure_03_evaluator_agreement_matrix(experiment_id: str):
    """
    Figure 3: Evaluator Agreement Matrix
    Correlation heatmap showing pairwise agreement between 5 evaluators.
    """
    print("\n📊 Generating Figure 3: Evaluator Agreement Matrix...")

    # TODO: Extract from evaluator_agreement.py
    print("⏭️  Figure 3 - TODO: Extract from evaluator_agreement.py")


def generate_figure_04_dimensional_structure_pca(experiment_id: str):
    """
    Figure 4: Dimensional Structure (PCA Biplot)
    Shows 2D rubric structure with loadings.
    """
    print("\n📊 Generating Figure 4: PCA Biplot...")

    # TODO: Extract from dimensional_analysis.py
    print("⏭️  Figure 4 - TODO: Extract from dimensional_analysis.py")


def generate_figure_05_score_distributions_by_model(experiment_id: str):
    """
    Figure 5: Score Distributions by Model
    Violin plots showing score distributions for each model.
    """
    print("\n📊 Generating Figure 5: Score Distributions by Model...")

    # TODO: Extract from interaction_analysis.py
    print("⏭️  Figure 5 - TODO: Extract from interaction_analysis.py")


def generate_figure_06_score_distributions_by_constitution(experiment_id: str):
    """
    Figure 6: Score Distributions by Constitution
    Violin plots showing score distributions for each constitution.
    """
    print("\n📊 Generating Figure 6: Score Distributions by Constitution...")

    # TODO: Extract from interaction_analysis.py
    print("⏭️  Figure 6 - TODO: Extract from interaction_analysis.py")


def generate_figure_07_interaction_plot(experiment_id: str):
    """
    Figure 7: Model × Constitution Interaction Plot
    Line plot showing how different models respond to constitutions.
    """
    print("\n📊 Generating Figure 7: Interaction Plot...")

    # TODO: Extract from interaction_analysis.py
    print("⏭️  Figure 7 - TODO: Extract from interaction_analysis.py")


def generate_figure_08_evaluator_icc_forest(experiment_id: str):
    """
    Figure 8: Evaluator ICC Forest Plot
    Shows individual evaluator ICC vs. ensemble ICC.
    """
    print("\n📊 Generating Figure 8: ICC Forest Plot...")

    # TODO: Extract from evaluator_agreement.py
    print("⏭️  Figure 8 - TODO: Extract from evaluator_agreement.py")


def generate_figure_09_dimensional_scatter(experiment_id: str):
    """
    Figure 9: Integrity × Transparency Scatter
    Scatter plot of two rubric dimensions.
    """
    print("\n📊 Generating Figure 9: Dimensional Scatter...")

    # TODO: Extract from dimensional_analysis.py
    print("⏭️  Figure 9 - TODO: Extract from dimensional_analysis.py")


def generate_figure_10_ceiling_effect_evidence(experiment_id: str):
    """
    Figure 10: Ceiling Effects in Discrete Rubrics
    Histograms showing 96-99% PASS rates in Binary/Ternary.
    """
    print("\n📊 Generating Figure 10: Ceiling Effect Evidence...")

    # TODO: Extract from rubric_comparison.py or rubric_diagnostic.py
    print("⏭️  Figure 10 - TODO: Extract from rubric diagnostic analysis")


def generate_figure_11_evaluation_coverage_heatmap(experiment_id: str):
    """
    Figure 11: Evaluation Coverage Heatmap
    Shows which trials were evaluated by which evaluators.
    """
    print("\n📊 Generating Figure 11: Evaluation Coverage...")

    # TODO: Create from evaluator_agreement.py data
    print("⏭️  Figure 11 - TODO: Create coverage heatmap")


def generate_figure_12_rubric_score_ranges(experiment_id: str):
    """
    Figure 12: Score Range Comparison by Rubric
    Box plots showing score variance across rubric formats.
    """
    print("\n📊 Generating Figure 12: Score Range Comparison...")

    # TODO: Extract from rubric_comparison.py
    print("⏭️  Figure 12 - TODO: Extract from rubric comparison")


# ============================================================================
# Web Data Export
# ============================================================================

def export_web_data(filename: str, data: dict):
    """Export data as JSON for web app consumption."""
    filepath = WEB_DATA_DIR / filename

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=JSON_INDENT, ensure_ascii=JSON_ENSURE_ASCII)

    print(f"   💾 Exported: {filepath.relative_to(Path.cwd().parent)}")


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Generate all figures and export web data."""

    # Get experiment ID from command line or use default
    if len(sys.argv) > 1:
        experiment_id = sys.argv[1]
    else:
        experiment_id = "exp_20251028_134615"
        print(f"ℹ️  No experiment ID provided, using default: {experiment_id}")

    print("=" * 70)
    print("FIGURE GENERATION")
    print("=" * 70)
    print(f"Experiment: {experiment_id}")
    print(f"Output: {FIGURES_DIR}")
    print(f"Web data: {WEB_DATA_DIR}")
    print("=" * 70)

    # Setup
    setup_environment()
    validate_experiment(experiment_id)

    # Generate all figures
    figure_generators = [
        generate_figure_01_rubric_comparison,
        generate_figure_02_model_constitution_heatmap,
        generate_figure_03_evaluator_agreement_matrix,
        generate_figure_04_dimensional_structure_pca,
        generate_figure_05_score_distributions_by_model,
        generate_figure_06_score_distributions_by_constitution,
        generate_figure_07_interaction_plot,
        generate_figure_08_evaluator_icc_forest,
        generate_figure_09_dimensional_scatter,
        generate_figure_10_ceiling_effect_evidence,
        generate_figure_11_evaluation_coverage_heatmap,
        generate_figure_12_rubric_score_ranges,
    ]

    completed = 0
    skipped = 0
    errors = []

    for generator in figure_generators:
        try:
            generator(experiment_id)
            completed += 1
        except NotImplementedError:
            skipped += 1
            print(f"⏭️  {generator.__name__} - Not yet implemented (TODO)")
        except Exception as e:
            errors.append((generator.__name__, str(e)))
            print(f"❌ {generator.__name__} - ERROR: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Completed: {completed}/{len(figure_generators)} figures")
    if skipped > 0:
        print(f"⏭️  Skipped: {skipped} (TODO)")
    if errors:
        print(f"❌ Errors: {len(errors)}")
        for name, error in errors:
            print(f"   - {name}: {error}")
    print("=" * 70)

    if completed > 0:
        print(f"\n🎉 Generated {completed} figures in {FIGURES_DIR}")
        print(f"📁 View figures: ls {FIGURES_DIR}")

    if errors:
        sys.exit(1)  # Exit with error code if any failures


if __name__ == "__main__":
    main()
