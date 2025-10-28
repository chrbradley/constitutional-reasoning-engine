"""
Visualization System for Constitutional Reasoning Experiment

Generates publication-ready visualizations from analysis results:
- Model performance rankings (bar charts)
- Constitution integrity scores (bar charts)
- Score distributions (box plots)
- Model × Constitution interactions (heatmaps)
- Scenario difficulty analysis (scatter plots)
- Dimensional breakdowns (grouped bar charts)

Usage:
    python experiments/visualize.py --experiment exp_20251023_105245
    python experiments/visualize.py --all
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

# Set publication-ready style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10


class ExperimentVisualizer:
    """Generate visualizations from experiment analysis results."""

    def __init__(self, base_dir: Path = Path("results")):
        self.base_dir = base_dir
        self.analysis_dir = base_dir / "analysis" / "single"
        self.viz_dir = base_dir / "visualizations"
        self.viz_dir.mkdir(parents=True, exist_ok=True)

    def visualize_experiment(self, experiment_id: str) -> None:
        """Generate all visualizations for a single experiment."""

        # Load analysis results (from experiment's analysis directory)
        analysis_path = Path("results/experiments") / experiment_id / "analysis" / f"{experiment_id}_analysis.json"
        if not analysis_path.exists():
            raise FileNotFoundError(f"Analysis file not found: {analysis_path}")

        with open(analysis_path) as f:
            data = json.load(f)

        print(f"Generating visualizations for {experiment_id}...")

        # Create experiment-specific directory
        exp_viz_dir = self.viz_dir / experiment_id
        exp_viz_dir.mkdir(exist_ok=True)

        # Generate all visualizations
        self._plot_model_rankings(data, exp_viz_dir)
        self._plot_constitution_rankings(data, exp_viz_dir)
        self._plot_score_distributions_by_model(data, exp_viz_dir)
        self._plot_score_distributions_by_constitution(data, exp_viz_dir)
        self._plot_model_constitution_heatmap(data, exp_viz_dir)
        self._plot_dimensional_breakdown(data, exp_viz_dir)
        self._plot_scenario_difficulty(data, exp_viz_dir)
        self._plot_integrity_dimensions(data, exp_viz_dir)

        print(f"✓ Visualizations saved to {exp_viz_dir}")

    def _plot_model_rankings(self, data: Dict[str, Any], output_dir: Path) -> None:
        """Bar chart: Model performance rankings."""

        models_data = data['by_model']['models']

        # Prepare data
        models = []
        scores = []
        stdevs = []

        for model_id in data['by_model']['ranking']:
            model_data = models_data[model_id]
            models.append(self._format_model_name(model_id))
            scores.append(model_data['overall_score']['mean'])
            stdevs.append(model_data['overall_score']['stdev'])

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(models))
        bars = ax.bar(x, scores, yerr=stdevs, capsize=5,
                     color=sns.color_palette("RdYlGn", len(models))[::-1])

        # Customize
        ax.set_xlabel('Model', fontweight='bold')
        ax.set_ylabel('Mean Integrity Score', fontweight='bold')
        ax.set_title('Model Performance Rankings\n(Higher = Better Integrity)',
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.axhline(y=80, color='gray', linestyle='--', alpha=0.5, label='80 (Strong Threshold)')
        ax.legend()

        # Add score labels on bars
        for i, (bar, score, std) in enumerate(zip(bars, scores, stdevs)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + std + 2,
                   f'{score:.1f}\n(±{std:.1f})',
                   ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        plt.savefig(output_dir / '01_model_rankings.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_constitution_rankings(self, data: Dict[str, Any], output_dir: Path) -> None:
        """Bar chart: Constitution integrity scores."""

        const_data = data['by_constitution']['constitutions']

        # Prepare data
        constitutions = []
        scores = []
        stdevs = []
        colors = []

        for const_id in data['by_constitution']['ranking']:
            const_info = const_data[const_id]
            constitutions.append(self._format_constitution_name(const_id))
            scores.append(const_info['overall_score']['mean'])
            stdevs.append(const_info['overall_score']['stdev'])
            # Color bad-faith differently
            colors.append('salmon' if const_id == 'bad-faith' else 'skyblue')

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))

        x = np.arange(len(constitutions))
        bars = ax.bar(x, scores, yerr=stdevs, capsize=5, color=colors)

        # Customize
        ax.set_xlabel('Constitution', fontweight='bold')
        ax.set_ylabel('Mean Integrity Score', fontweight='bold')
        ax.set_title('Constitution Performance Rankings\n(Bad-Faith as Control)',
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(constitutions, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.axhline(y=80, color='gray', linestyle='--', alpha=0.5)

        # Add score labels
        for bar, score, std in zip(bars, scores, stdevs):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + std + 2,
                   f'{score:.1f}',
                   ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        plt.savefig(output_dir / '02_constitution_rankings.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_score_distributions_by_model(self, data: Dict[str, Any], output_dir: Path) -> None:
        """Box plot: Score distributions by model."""

        # We need raw test results for box plots
        # For now, we'll use the statistics we have
        models_data = data['by_model']['models']

        fig, ax = plt.subplots(figsize=(12, 6))

        # Prepare data for visualization
        plot_data = []
        labels = []

        for model_id in data['by_model']['ranking']:
            model_info = models_data[model_id]
            labels.append(self._format_model_name(model_id))

            # Create synthetic data points from statistics
            # This is approximate - ideally we'd load raw results
            mean = model_info['overall_score']['mean']
            std = model_info['overall_score']['stdev']
            min_val = model_info['overall_score']['min']
            max_val = model_info['overall_score']['max']
            median = model_info['overall_score']['median']

            plot_data.append({
                'mean': mean,
                'median': median,
                'std': std,
                'min': min_val,
                'max': max_val
            })

        # Plot as error bars with median markers
        x = np.arange(len(labels))
        for i, d in enumerate(plot_data):
            ax.errorbar(i, d['mean'], yerr=d['std'], fmt='o',
                       capsize=5, capthick=2, markersize=8)
            ax.plot(i, d['median'], 's', markersize=10,
                   color='red', alpha=0.7, label='Median' if i == 0 else '')

        ax.set_xlabel('Model', fontweight='bold')
        ax.set_ylabel('Integrity Score', fontweight='bold')
        ax.set_title('Score Distributions by Model\n(Circle = Mean ± SD, Square = Median)',
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / '03_score_distributions_by_model.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_score_distributions_by_constitution(self, data: Dict[str, Any], output_dir: Path) -> None:
        """Box plot: Score distributions by constitution."""

        const_data = data['by_constitution']['constitutions']

        fig, ax = plt.subplots(figsize=(10, 6))

        plot_data = []
        labels = []
        colors = []

        for const_id in data['by_constitution']['ranking']:
            const_info = const_data[const_id]
            labels.append(self._format_constitution_name(const_id))

            mean = const_info['overall_score']['mean']
            std = const_info['overall_score']['stdev']
            median = const_info['overall_score']['median']

            plot_data.append({'mean': mean, 'median': median, 'std': std})
            colors.append('red' if const_id == 'bad-faith' else 'blue')

        x = np.arange(len(labels))
        for i, (d, color) in enumerate(zip(plot_data, colors)):
            ax.errorbar(i, d['mean'], yerr=d['std'], fmt='o',
                       capsize=5, capthick=2, markersize=8, color=color, alpha=0.7)
            ax.plot(i, d['median'], 's', markersize=10,
                   color='darkred' if color == 'red' else 'darkblue', alpha=0.8)

        ax.set_xlabel('Constitution', fontweight='bold')
        ax.set_ylabel('Integrity Score', fontweight='bold')
        ax.set_title('Score Distributions by Constitution\n(Red = Bad-Faith Control)',
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / '04_score_distributions_by_constitution.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_model_constitution_heatmap(self, data: Dict[str, Any], output_dir: Path) -> None:
        """Heatmap: Model × Constitution interaction matrix."""

        matrix_data = data['model_constitution_matrix']['matrix']

        # Extract models and constitutions
        models = list(data['by_model']['ranking'])
        constitutions = list(data['by_constitution']['ranking'])

        # Build matrix
        scores = []
        for model in models:
            row = []
            for const in constitutions:
                score = matrix_data.get(model, {}).get(const, 0)
                row.append(score)
            scores.append(row)

        # Create heatmap
        fig, ax = plt.subplots(figsize=(10, 8))

        im = ax.imshow(scores, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)

        # Customize
        ax.set_xticks(np.arange(len(constitutions)))
        ax.set_yticks(np.arange(len(models)))
        ax.set_xticklabels([self._format_constitution_name(c) for c in constitutions],
                          rotation=45, ha='right')
        ax.set_yticklabels([self._format_model_name(m) for m in models])

        ax.set_title('Model × Constitution Interaction Matrix\n(Integrity Scores)',
                    fontsize=14, fontweight='bold', pad=20)

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Integrity Score', rotation=270, labelpad=20, fontweight='bold')

        # Add text annotations
        for i in range(len(models)):
            for j in range(len(constitutions)):
                text = ax.text(j, i, f'{scores[i][j]:.1f}',
                             ha="center", va="center", color="black", fontsize=9)

        plt.tight_layout()
        plt.savefig(output_dir / '05_model_constitution_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_dimensional_breakdown(self, data: Dict[str, Any], output_dir: Path) -> None:
        """Grouped bar chart: Epistemic integrity, value transparency by model."""

        models_data = data['by_model']['models']

        # Prepare data
        models = [self._format_model_name(m) for m in data['by_model']['ranking']]
        epistemic = [models_data[m]['epistemic_integrity'] for m in data['by_model']['ranking']]
        value = [models_data[m]['value_transparency'] for m in data['by_model']['ranking']]

        # Create plot
        fig, ax = plt.subplots(figsize=(14, 6))

        x = np.arange(len(models))
        width = 0.35

        bars1 = ax.bar(x - width/2, epistemic, width, label='Epistemic Integrity', color='steelblue')
        bars2 = ax.bar(x + width/2, value, width, label='Value Transparency', color='seagreen')

        # Customize
        ax.set_xlabel('Model', fontweight='bold')
        ax.set_ylabel('Score', fontweight='bold')
        ax.set_title('Integrity Dimensions by Model\n(Two-Dimensional Breakdown)',
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(output_dir / '06_dimensional_breakdown_by_model.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_scenario_difficulty(self, data: Dict[str, Any], output_dir: Path) -> None:
        """Scatter plot: Scenario difficulty (mean score vs. variance)."""

        scenarios_data = data['by_scenario']['scenarios']

        # Prepare data
        scenarios = []
        means = []
        stdevs = []

        for scenario_id, scenario_info in scenarios_data.items():
            scenarios.append(self._format_scenario_name(scenario_id))
            means.append(scenario_info['mean_score'])
            stdevs.append(scenario_info['stdev'])

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 8))

        scatter = ax.scatter(means, stdevs, s=100, alpha=0.6, c=means,
                           cmap='RdYlGn', vmin=70, vmax=90)

        # Add labels for interesting points
        for i, (scenario, mean, std) in enumerate(zip(scenarios, means, stdevs)):
            if mean < 78 or std > 20:  # Highlight difficult/variable scenarios
                ax.annotate(scenario, (mean, std),
                          xytext=(5, 5), textcoords='offset points',
                          fontsize=8, alpha=0.8)

        ax.set_xlabel('Mean Integrity Score', fontweight='bold')
        ax.set_ylabel('Standard Deviation', fontweight='bold')
        ax.set_title('Scenario Difficulty Analysis\n(Lower-left = Harder, Upper-right = More Variable)',
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        plt.colorbar(scatter, ax=ax, label='Mean Score')
        plt.tight_layout()
        plt.savefig(output_dir / '07_scenario_difficulty.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_integrity_dimensions(self, data: Dict[str, Any], output_dir: Path) -> None:
        """Grouped bar chart: Dimensional breakdown by constitution."""

        const_data = data['by_constitution']['constitutions']

        # Prepare data
        constitutions = [self._format_constitution_name(c) for c in data['by_constitution']['ranking']]
        epistemic = [const_data[c]['epistemic_integrity'] for c in data['by_constitution']['ranking']]
        value = [const_data[c]['value_transparency'] for c in data['by_constitution']['ranking']]

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(constitutions))
        width = 0.35

        bars1 = ax.bar(x - width/2, epistemic, width, label='Epistemic Integrity', color='steelblue')
        bars2 = ax.bar(x + width/2, value, width, label='Value Transparency', color='seagreen')

        # Customize
        ax.set_xlabel('Constitution', fontweight='bold')
        ax.set_ylabel('Score', fontweight='bold')
        ax.set_title('Integrity Dimensions by Constitution\n(Bad-Faith Shows Epistemic Integrity Failure)',
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(constitutions, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(output_dir / '08_dimensional_breakdown_by_constitution.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _format_model_name(self, model_id: str) -> str:
        """Format model ID for display."""
        name_map = {
            'claude-sonnet-4-5': 'Claude\nSonnet 4.5',
            'gpt-4o': 'GPT-4o',
            'llama-3-8b': 'Llama 3\n8B',
            'gemini-2-5-flash': 'Gemini 2.5\nFlash',
            'grok-3': 'Grok 3',
            'deepseek-chat': 'DeepSeek\nChat'
        }
        return name_map.get(model_id, model_id)

    def _format_constitution_name(self, const_id: str) -> str:
        """Format constitution ID for display."""
        name_map = {
            'harm-minimization': 'Harm\nMinimization',
            'balanced-justice': 'Balanced\nJustice',
            'self-sovereignty': 'Self-\nSovereignty',
            'community-order': 'Community\nOrder',
            'bad-faith': 'Bad-Faith\n(Control)'
        }
        return name_map.get(const_id, const_id)

    def _format_scenario_name(self, scenario_id: str) -> str:
        """Format scenario ID for display."""
        return scenario_id.replace('-', ' ').title()


def main():
    parser = argparse.ArgumentParser(
        description="Generate visualizations from experiment analysis results"
    )
    parser.add_argument(
        '--experiment',
        type=str,
        help='Experiment ID to visualize (e.g., exp_20251023_105245)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Visualize all available experiments'
    )

    args = parser.parse_args()

    visualizer = ExperimentVisualizer()

    if args.all:
        # Find all analysis files
        analysis_files = list(visualizer.analysis_dir.glob("*_analysis.json"))
        if not analysis_files:
            print("No analysis files found.")
            return

        print(f"Found {len(analysis_files)} experiment(s) to visualize")
        for analysis_file in analysis_files:
            experiment_id = analysis_file.stem.replace('_analysis', '')
            visualizer.visualize_experiment(experiment_id)

    elif args.experiment:
        visualizer.visualize_experiment(args.experiment)

    else:
        print("Please specify --experiment <id> or --all")
        print("\nExample:")
        print("  python experiments/visualize.py --experiment exp_20251023_105245")
        print("  python experiments/visualize.py --all")


if __name__ == "__main__":
    main()
