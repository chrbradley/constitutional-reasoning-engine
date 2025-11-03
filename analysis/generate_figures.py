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
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns

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
    MODEL_COLORS,
    MODEL_DISPLAY_NAMES,
    CONSTITUTION_COLORS,
    CONSTITUTION_DISPLAY_NAMES,
    RUBRIC_COLORS,
    RUBRIC_DISPLAY_NAMES,
    FIGURE_SIZE,
    FIGURE_SIZE_WIDE,
    FIGURE_SIZE_SQUARE,
)


# ============================================================================
# Data Loading Utilities
# ============================================================================

def load_analysis_results(experiment_id: str, analysis_name: str) -> dict:
    """Load analysis results JSON file."""
    results_path = Path("results/experiments") / experiment_id / "analysis" / f"{analysis_name}.json"

    if not results_path.exists():
        raise FileNotFoundError(f"Analysis results not found: {results_path}")

    with open(results_path) as f:
        return json.load(f)


def load_consensus_scores(experiment_id: str) -> pd.DataFrame:
    """Load consensus scores as DataFrame with metadata from trial files."""
    scores_path = Path("results/experiments") / experiment_id / "analysis" / "consensus_scores.json"
    layer3_path = Path("results/experiments") / experiment_id / "data" / "layer3"

    if not scores_path.exists():
        raise FileNotFoundError(f"Consensus scores not found: {scores_path}")

    with open(scores_path) as f:
        data = json.load(f)

    # Load metadata from trial files
    trial_metadata = {}
    for trial_file in layer3_path.glob("*.json"):
        with open(trial_file) as f:
            trial_data = json.load(f)
            trial_id = trial_data['trial_id']
            trial_metadata[trial_id] = {
                'scenario_id': trial_data['scenario_id'],
                'constitution': trial_data['constitution'],
                'layer2_model': trial_data['model']
            }

    # Convert to DataFrame
    records = []
    for trial_score in data['consensus_scores']:
        trial_id = trial_score['trial_id']
        metadata = trial_metadata.get(trial_id, {})

        records.append({
            'trial_id': trial_id,
            'scenario_id': metadata.get('scenario_id', 'unknown'),
            'constitution': metadata.get('constitution', 'unknown'),
            'layer2_model': metadata.get('layer2_model', 'unknown'),
            'epistemic_integrity': trial_score['mean_all']['epistemic_integrity'],
            'value_transparency': trial_score['mean_all']['value_transparency'],
            'overall_score': trial_score['mean_all']['overall_score'],
        })

    return pd.DataFrame(records)


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

    # Load interaction analysis results
    interaction_data = load_analysis_results(experiment_id, 'interaction_analysis')
    cell_means = interaction_data['dimensions']['overall_score']['cell_means']

    # Convert to DataFrame for heatmap
    # Rows = constitutions, Columns = models
    constitutions = sorted(cell_means.keys())
    models = sorted(list(cell_means[constitutions[0]].keys()))

    # Build matrix
    matrix = []
    for const in constitutions:
        row = [cell_means[const][model] for model in models]
        matrix.append(row)

    df = pd.DataFrame(
        matrix,
        index=[CONSTITUTION_DISPLAY_NAMES.get(c, c) for c in constitutions],
        columns=[MODEL_DISPLAY_NAMES.get(m, m) for m in models]
    )

    # Create heatmap
    fig, ax = plt.subplots(figsize=FIGURE_SIZE_WIDE)

    sns.heatmap(df, annot=True, fmt='.1f', cmap='RdYlGn', center=90,
                vmin=80, vmax=100, cbar_kws={'label': 'Mean Overall Score'},
                linewidths=0.5, linecolor='gray', ax=ax)

    ax.set_title('Model × Constitution Interaction', fontsize=14, fontweight='bold')
    ax.set_xlabel('Model', fontsize=12)
    ax.set_ylabel('Constitution', fontsize=12)

    # Rotate x-axis labels for readability
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    plt.tight_layout()
    save_figure(fig, '02_model_constitution_heatmap')
    plt.close(fig)

    # Export data for web app
    web_data = {
        'constitutions': constitutions,
        'models': models,
        'cell_means': cell_means,
        'generated': datetime.now().isoformat(),
    }

    export_web_data('model_constitution_matrix.json', web_data)

    print("✅ Figure 2 complete")


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

    # Load consensus scores
    df = load_consensus_scores(experiment_id)

    # Create figure with 3 subplots (one for each dimension)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    dimensions = [
        ('epistemic_integrity', 'Epistemic Integrity', axes[0]),
        ('value_transparency', 'Value Transparency', axes[1]),
        ('overall_score', 'Overall Score', axes[2])
    ]

    # Get model order for consistent coloring
    models = sorted(df['layer2_model'].unique())
    model_labels = [MODEL_DISPLAY_NAMES.get(m, m) for m in models]

    for dim_col, dim_name, ax in dimensions:
        # Prepare data for violin plot
        data_by_model = [df[df['layer2_model'] == model][dim_col].values for model in models]
        colors = [MODEL_COLORS.get(model, '#999999') for model in models]

        # Create violin plot
        parts = ax.violinplot(data_by_model, positions=range(len(models)),
                              showmeans=True, showmedians=True, widths=0.7)

        # Color the violins
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.7)
            pc.set_edgecolor('black')
            pc.set_linewidth(1)

        # Styling
        parts['cmeans'].set_color('red')
        parts['cmeans'].set_linewidth(2)
        parts['cmedians'].set_color('blue')
        parts['cmedians'].set_linewidth(2)

        ax.set_title(dim_name, fontsize=12, fontweight='bold')
        ax.set_ylabel('Score', fontsize=11)
        ax.set_xlabel('Model', fontsize=11)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(model_labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Score Distributions by Model', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, '05_score_distributions_by_model')
    plt.close(fig)

    # Export data for web app
    web_data = {
        'models': models,
        'model_labels': model_labels,
        'distributions': {}
    }

    for dim_col, dim_name, _ in dimensions:
        web_data['distributions'][dim_col] = {
            model: {
                'values': df[df['layer2_model'] == model][dim_col].tolist(),
                'mean': float(df[df['layer2_model'] == model][dim_col].mean()),
                'median': float(df[df['layer2_model'] == model][dim_col].median()),
                'std': float(df[df['layer2_model'] == model][dim_col].std()),
            }
            for model in models
        }

    web_data['generated'] = datetime.now().isoformat()
    export_web_data('score_distributions_by_model.json', web_data)

    print("✅ Figure 5 complete")


def generate_figure_06_score_distributions_by_constitution(experiment_id: str):
    """
    Figure 6: Score Distributions by Constitution
    Violin plots showing score distributions for each constitution.
    """
    print("\n📊 Generating Figure 6: Score Distributions by Constitution...")

    # Load consensus scores
    df = load_consensus_scores(experiment_id)

    # Create figure with 3 subplots (one for each dimension)
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))

    dimensions = [
        ('epistemic_integrity', 'Epistemic Integrity', axes[0]),
        ('value_transparency', 'Value Transparency', axes[1]),
        ('overall_score', 'Overall Score', axes[2])
    ]

    # Get constitution order for consistent coloring
    constitutions = sorted(df['constitution'].unique())
    const_labels = [CONSTITUTION_DISPLAY_NAMES.get(c, c) for c in constitutions]

    for dim_col, dim_name, ax in dimensions:
        # Prepare data for violin plot
        data_by_const = [df[df['constitution'] == const][dim_col].values for const in constitutions]
        colors = [CONSTITUTION_COLORS.get(const, '#999999') for const in constitutions]

        # Create violin plot
        parts = ax.violinplot(data_by_const, positions=range(len(constitutions)),
                              showmeans=True, showmedians=True, widths=0.7)

        # Color the violins
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.7)
            pc.set_edgecolor('black')
            pc.set_linewidth(1)

        # Styling
        parts['cmeans'].set_color('red')
        parts['cmeans'].set_linewidth(2)
        parts['cmedians'].set_color('blue')
        parts['cmedians'].set_linewidth(2)

        ax.set_title(dim_name, fontsize=12, fontweight='bold')
        ax.set_ylabel('Score', fontsize=11)
        ax.set_xlabel('Constitution', fontsize=11)
        ax.set_xticks(range(len(constitutions)))
        ax.set_xticklabels(const_labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylim(0, 100)
        ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Score Distributions by Constitution', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, '06_score_distributions_by_constitution')
    plt.close(fig)

    # Export data for web app
    web_data = {
        'constitutions': constitutions,
        'constitution_labels': const_labels,
        'distributions': {}
    }

    for dim_col, dim_name, _ in dimensions:
        web_data['distributions'][dim_col] = {
            const: {
                'values': df[df['constitution'] == const][dim_col].tolist(),
                'mean': float(df[df['constitution'] == const][dim_col].mean()),
                'median': float(df[df['constitution'] == const][dim_col].median()),
                'std': float(df[df['constitution'] == const][dim_col].std()),
            }
            for const in constitutions
        }

    web_data['generated'] = datetime.now().isoformat()
    export_web_data('score_distributions_by_constitution.json', web_data)

    print("✅ Figure 6 complete")


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

    # Load consensus scores
    df = load_consensus_scores(experiment_id)

    # Load dimensional analysis for correlation stats
    dim_analysis = load_analysis_results(experiment_id, 'dimensional_analysis')
    overall_corr = dim_analysis['independence_test']['overall_correlation']

    # Create scatter plot
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    # Scatter plot with transparency
    ax.scatter(df['epistemic_integrity'], df['value_transparency'],
               alpha=0.6, s=50, color='#0173B2', edgecolors='black', linewidth=0.5)

    # Add regression line
    z = np.polyfit(df['epistemic_integrity'], df['value_transparency'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df['epistemic_integrity'].min(), df['epistemic_integrity'].max(), 100)
    ax.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2, label=f"r = {overall_corr['r']:.3f}")

    # Labels and title
    ax.set_xlabel('Epistemic Integrity', fontsize=12)
    ax.set_ylabel('Value Transparency', fontsize=12)
    ax.set_title('Dimensional Independence (Integrity × Transparency)', fontsize=14, fontweight='bold')

    # Add correlation info as text box
    textstr = f"r = {overall_corr['r']:.3f}\n95% CI [{overall_corr['ci_lower']:.3f}, {overall_corr['ci_upper']:.3f}]\np < 0.001\nn = {overall_corr['n']}"
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)

    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    save_figure(fig, '09_dimensional_scatter')
    plt.close(fig)

    # Export data for web app
    web_data = {
        'trials': df[['epistemic_integrity', 'value_transparency']].to_dict('records'),
        'correlation': {
            'r': overall_corr['r'],
            'p': overall_corr['p'],
            'ci_lower': overall_corr['ci_lower'],
            'ci_upper': overall_corr['ci_upper'],
            'n': overall_corr['n']
        },
        'generated': datetime.now().isoformat(),
    }

    export_web_data('dimensional_scatter.json', web_data)

    print("✅ Figure 9 complete")


def generate_figure_10_ceiling_effect_evidence(experiment_id: str):
    """
    Figure 10: Ceiling Effects in Discrete Rubrics
    Histograms showing 96-99% PASS rates in Binary/Ternary.
    """
    print("\n📊 Generating Figure 10: Ceiling Effect Evidence...")

    # Load rubric diagnostic data
    diagnostic = load_analysis_results(experiment_id, 'rubric_diagnostic')
    ceiling_effects = diagnostic['diagnostics']['ceiling_effects']

    # Create figure with 3 subplots (Binary, Ternary, Likert)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    rubrics = [
        ('binary_overall_score', 'Binary\n(Pass/Fail)', axes[0], RUBRIC_COLORS['binary']),
        ('ternary_overall_score', 'Ternary\n(Pass/Partial/Fail)', axes[1], RUBRIC_COLORS['ternary']),
    ]

    # Load actual score distributions for Binary and Ternary
    exp_path = Path("results/experiments") / experiment_id

    # Binary scores
    binary_scores = []
    for trial_file in (exp_path / "data" / "layer3_binary").glob("*.json"):
        with open(trial_file) as f:
            trial_data = json.load(f)
            evaluations = trial_data.get('evaluations', {})
            for evaluator_name, eval_result in evaluations.items():
                if 'response_parsed' in eval_result and 'overallScore' in eval_result['response_parsed']:
                    binary_scores.append(eval_result['response_parsed']['overallScore'])

    # Ternary scores
    ternary_scores = []
    for trial_file in (exp_path / "data" / "layer3_ternary").glob("*.json"):
        with open(trial_file) as f:
            trial_data = json.load(f)
            evaluations = trial_data.get('evaluations', {})
            for evaluator_name, eval_result in evaluations.items():
                if 'response_parsed' in eval_result and 'overallScore' in eval_result['response_parsed']:
                    ternary_scores.append(eval_result['response_parsed']['overallScore'])

    # Likert scores (from consensus_scores for comparison)
    df = load_consensus_scores(experiment_id)
    likert_scores = df['overall_score'].tolist()

    # Plot Binary
    axes[0].hist(binary_scores, bins=20, color=RUBRIC_COLORS['binary'], alpha=0.7, edgecolor='black')
    pass_rate_binary = ceiling_effects['binary_overall_score']['pass_rate']
    axes[0].axvline(x=50, color='red', linestyle='--', linewidth=2, label=f'Pass Threshold')
    axes[0].set_title(f'Binary\n{pass_rate_binary*100:.1f}% ≥ Pass', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Overall Score', fontsize=11)
    axes[0].set_ylabel('Frequency', fontsize=11)
    axes[0].set_xlim(0, 100)
    axes[0].legend()
    axes[0].grid(axis='y', alpha=0.3)

    # Plot Ternary
    axes[1].hist(ternary_scores, bins=20, color=RUBRIC_COLORS['ternary'], alpha=0.7, edgecolor='black')
    pass_rate_ternary = ceiling_effects['ternary_overall_score']['pass_rate']
    axes[1].axvline(x=66.67, color='red', linestyle='--', linewidth=2, label=f'Pass Threshold')
    axes[1].set_title(f'Ternary\n{pass_rate_ternary*100:.1f}% ≥ Pass', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Overall Score', fontsize=11)
    axes[1].set_ylabel('Frequency', fontsize=11)
    axes[1].set_xlim(0, 100)
    axes[1].legend()
    axes[1].grid(axis='y', alpha=0.3)

    # Plot Likert (for comparison)
    axes[2].hist(likert_scores, bins=20, color=RUBRIC_COLORS['likert'], alpha=0.7, edgecolor='black')
    axes[2].set_title(f'Likert\n(Continuous 0-100)', fontsize=12, fontweight='bold')
    axes[2].set_xlabel('Overall Score', fontsize=11)
    axes[2].set_ylabel('Frequency', fontsize=11)
    axes[2].set_xlim(0, 100)
    axes[2].grid(axis='y', alpha=0.3)

    plt.suptitle('Ceiling Effects in Discrete Rubrics', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    save_figure(fig, '10_ceiling_effect_evidence')
    plt.close(fig)

    # Export data for web app
    web_data = {
        'binary': {
            'scores': binary_scores,
            'pass_rate': ceiling_effects['binary_overall_score']['pass_rate'],
            'mean': ceiling_effects['binary_overall_score']['mean'],
            'unique_values': ceiling_effects['binary_overall_score']['unique_values']
        },
        'ternary': {
            'scores': ternary_scores,
            'pass_rate': ceiling_effects['ternary_overall_score']['pass_rate'],
            'mean': ceiling_effects['ternary_overall_score']['mean'],
            'unique_values': ceiling_effects['ternary_overall_score']['unique_values']
        },
        'likert': {
            'scores': likert_scores,
        },
        'generated': datetime.now().isoformat(),
    }

    export_web_data('ceiling_effect_evidence.json', web_data)

    print("✅ Figure 10 complete")


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

    # Load rubric comparison data
    rubric_comp = load_analysis_results(experiment_id, 'rubric_comparison')

    # Load actual scores from all three rubrics
    exp_path = Path("results/experiments") / experiment_id

    # Binary scores
    binary_scores = []
    for trial_file in (exp_path / "data" / "layer3_binary").glob("*.json"):
        with open(trial_file) as f:
            trial_data = json.load(f)
            evaluations = trial_data.get('evaluations', {})
            for evaluator_name, eval_result in evaluations.items():
                if 'response_parsed' in eval_result and 'overallScore' in eval_result['response_parsed']:
                    binary_scores.append(eval_result['response_parsed']['overallScore'])

    # Ternary scores
    ternary_scores = []
    for trial_file in (exp_path / "data" / "layer3_ternary").glob("*.json"):
        with open(trial_file) as f:
            trial_data = json.load(f)
            evaluations = trial_data.get('evaluations', {})
            for evaluator_name, eval_result in evaluations.items():
                if 'response_parsed' in eval_result and 'overallScore' in eval_result['response_parsed']:
                    ternary_scores.append(eval_result['response_parsed']['overallScore'])

    # Likert scores
    df = load_consensus_scores(experiment_id)
    likert_scores = df['overall_score'].tolist()

    # Prepare data for box plot
    data = [binary_scores, ternary_scores, likert_scores]
    labels = ['Binary\n(Pass/Fail)', 'Ternary\n(Pass/Partial/Fail)', 'Likert\n(0-100)']
    colors = [RUBRIC_COLORS['binary'], RUBRIC_COLORS['ternary'], RUBRIC_COLORS['likert']]

    # Create box plot
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    bp = ax.boxplot(data, labels=labels, patch_artist=True, widths=0.6,
                     showmeans=True, meanline=True,
                     boxprops=dict(linewidth=1.5),
                     medianprops=dict(color='blue', linewidth=2),
                     meanprops=dict(color='red', linewidth=2, linestyle='--'),
                     whiskerprops=dict(linewidth=1.5),
                     capprops=dict(linewidth=1.5))

    # Color the boxes
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Add ICC values as text annotations
    icc_likert = rubric_comp['rubrics']['likert']['dimensions']['overall_score']['icc']
    icc_ternary = rubric_comp['rubrics']['ternary']['dimensions']['overall_score']['icc']
    icc_binary = rubric_comp['rubrics']['binary']['dimensions']['overall_score']['icc']

    ax.text(1, 5, f"ICC: {icc_binary:.2f}", ha='center', fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax.text(2, 5, f"ICC: {icc_ternary:.2f}", ha='center', fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax.text(3, 5, f"ICC: {icc_likert:.2f}", ha='center', fontsize=9, bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Labels and title
    ax.set_ylabel('Overall Score', fontsize=12)
    ax.set_xlabel('Rubric Format', fontsize=12)
    ax.set_title('Score Range Comparison by Rubric Format', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3)

    # Add legend for median and mean
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='blue', linewidth=2, label='Median'),
        Line2D([0], [0], color='red', linewidth=2, linestyle='--', label='Mean')
    ]
    ax.legend(handles=legend_elements, loc='upper left')

    plt.tight_layout()
    save_figure(fig, '12_rubric_score_ranges')
    plt.close(fig)

    # Export data for web app
    web_data = {
        'rubrics': ['binary', 'ternary', 'likert'],
        'labels': labels,
        'statistics': {
            'binary': {
                'scores': binary_scores,
                'mean': float(np.mean(binary_scores)),
                'median': float(np.median(binary_scores)),
                'std': float(np.std(binary_scores)),
                'min': float(np.min(binary_scores)),
                'max': float(np.max(binary_scores)),
                'q1': float(np.percentile(binary_scores, 25)),
                'q3': float(np.percentile(binary_scores, 75)),
                'icc': icc_binary
            },
            'ternary': {
                'scores': ternary_scores,
                'mean': float(np.mean(ternary_scores)),
                'median': float(np.median(ternary_scores)),
                'std': float(np.std(ternary_scores)),
                'min': float(np.min(ternary_scores)),
                'max': float(np.max(ternary_scores)),
                'q1': float(np.percentile(ternary_scores, 25)),
                'q3': float(np.percentile(ternary_scores, 75)),
                'icc': icc_ternary
            },
            'likert': {
                'scores': likert_scores,
                'mean': float(np.mean(likert_scores)),
                'median': float(np.median(likert_scores)),
                'std': float(np.std(likert_scores)),
                'min': float(np.min(likert_scores)),
                'max': float(np.max(likert_scores)),
                'q1': float(np.percentile(likert_scores, 25)),
                'q3': float(np.percentile(likert_scores, 75)),
                'icc': icc_likert
            }
        },
        'generated': datetime.now().isoformat(),
    }

    export_web_data('rubric_score_ranges.json', web_data)

    print("✅ Figure 12 complete")


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
