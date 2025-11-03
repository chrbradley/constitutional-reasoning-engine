"""
Shared configuration for all research visualizations.

Ensures consistent styling across publication-ready figures and web app charts.
"""

from pathlib import Path
from typing import Dict

# ============================================================================
# Directory Paths
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"
WEB_DATA_DIR = PROJECT_ROOT / "results" / "experiments" / "exp_20251028_134615" / "web_data"
EXPERIMENT_DIR = PROJECT_ROOT / "results" / "experiments" / "exp_20251028_134615"

# Create directories if they don't exist
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Figure Settings
# ============================================================================

# Size and resolution
FIGURE_SIZE = (10, 6)  # Width x Height in inches
FIGURE_SIZE_WIDE = (12, 6)  # For wider plots (e.g., heatmaps)
FIGURE_SIZE_TALL = (10, 8)  # For taller plots (e.g., many categories)
FIGURE_SIZE_SQUARE = (8, 8)  # For square plots (e.g., correlation matrices)
DPI = 300  # High resolution for publication

# Fonts
FONT_SIZE_TITLE = 14
FONT_SIZE_LABEL = 12
FONT_SIZE_TICK = 10
FONT_SIZE_LEGEND = 10
FONT_FAMILY = "sans-serif"

# Styling
GRID_ALPHA = 0.3
GRID_LINESTYLE = "--"
SPINE_WIDTH = 1.0

# ============================================================================
# Color Palettes
# ============================================================================

# Colorblind-friendly palette for models
MODEL_COLORS: Dict[str, str] = {
    "claude-sonnet-4-5": "#0173B2",  # Blue
    "gpt-4o": "#029E73",             # Green
    "deepseek-chat": "#CC78BC",      # Purple/Pink
    "grok-3": "#DE8F05",             # Orange
    "gemini-2-5-pro": "#CA3542",     # Red
}

# Alternative model display names (for cleaner chart labels)
MODEL_DISPLAY_NAMES: Dict[str, str] = {
    "claude-sonnet-4-5": "Claude Sonnet 4.5",
    "gpt-4o": "GPT-4o",
    "deepseek-chat": "DeepSeek Chat",
    "grok-3": "Grok-3",
    "gemini-2-5-pro": "Gemini 2.5 Pro",
}

# Constitution colors (distinct, colorblind-friendly)
CONSTITUTION_COLORS: Dict[str, str] = {
    "harm-minimization": "#2ECC71",      # Green (caring)
    "liberty-maximization": "#3498DB",   # Blue (freedom)
    "utilitarian": "#F39C12",            # Orange (balance)
    "deontological": "#9B59B6",          # Purple (rules)
    "virtue-ethics": "#E74C3C",          # Red (character)
    "self-sovereignty": "#34495E",       # Dark gray (independence)
}

# Constitution display names
CONSTITUTION_DISPLAY_NAMES: Dict[str, str] = {
    "harm-minimization": "Harm Minimization",
    "liberty-maximization": "Liberty Maximization",
    "utilitarian": "Utilitarian",
    "deontological": "Deontological",
    "virtue-ethics": "Virtue Ethics",
    "self-sovereignty": "Self-Sovereignty",
}

# Rubric format colors
RUBRIC_COLORS: Dict[str, str] = {
    "likert": "#0173B2",    # Blue (best performer)
    "ternary": "#F39C12",   # Orange (middle)
    "binary": "#E74C3C",    # Red (worst performer)
}

# Rubric display names
RUBRIC_DISPLAY_NAMES: Dict[str, str] = {
    "likert": "Likert (0-100)",
    "ternary": "Ternary (Pass/Partial/Fail)",
    "binary": "Binary (Pass/Fail)",
}

# Dimension colors (for 2D rubric)
DIMENSION_COLORS: Dict[str, str] = {
    "epistemic_integrity": "#0173B2",    # Blue
    "value_transparency": "#DE8F05",     # Orange
    "overall": "#029E73",                # Green
}

# Dimension display names
DIMENSION_DISPLAY_NAMES: Dict[str, str] = {
    "epistemic_integrity": "Epistemic Integrity",
    "value_transparency": "Value Transparency",
    "overall": "Overall Score",
}

# ============================================================================
# Plot Styling Presets
# ============================================================================

def apply_publication_style():
    """Apply matplotlib rcParams for publication-quality figures."""
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        'font.size': FONT_SIZE_LABEL,
        'font.family': FONT_FAMILY,
        'axes.titlesize': FONT_SIZE_TITLE,
        'axes.labelsize': FONT_SIZE_LABEL,
        'xtick.labelsize': FONT_SIZE_TICK,
        'ytick.labelsize': FONT_SIZE_TICK,
        'legend.fontsize': FONT_SIZE_LEGEND,
        'figure.titlesize': FONT_SIZE_TITLE,
        'axes.grid': True,
        'grid.alpha': GRID_ALPHA,
        'grid.linestyle': GRID_LINESTYLE,
        'axes.linewidth': SPINE_WIDTH,
        'figure.dpi': DPI,
    })

def get_seaborn_style():
    """Return seaborn style configuration."""
    return {
        'style': 'whitegrid',
        'palette': 'colorblind',
        'context': 'paper',  # Options: paper, notebook, talk, poster
    }

# ============================================================================
# Helper Functions
# ============================================================================

def save_figure(fig, filename: str, formats: list = ['png', 'svg']):
    """
    Save figure in multiple formats with consistent naming.

    Args:
        fig: matplotlib Figure object
        filename: Base filename (without extension), e.g., "01_rubric_comparison"
        formats: List of formats to save, default ['png', 'svg']
    """
    for fmt in formats:
        filepath = FIGURES_DIR / f"{filename}.{fmt}"
        fig.savefig(filepath, format=fmt, dpi=DPI if fmt == 'png' else None,
                   bbox_inches='tight', facecolor='white')
        print(f"✅ Saved: {filepath.relative_to(PROJECT_ROOT)}")

def get_figure_number(filename: str) -> str:
    """
    Extract figure number from filename.

    Args:
        filename: Filename like "01_rubric_comparison"

    Returns:
        Figure number like "Figure 1"
    """
    number = filename.split('_')[0]
    return f"Figure {int(number)}"

# ============================================================================
# Data Export Settings
# ============================================================================

JSON_INDENT = 2  # Pretty-print JSON exports
JSON_ENSURE_ASCII = False  # Allow Unicode characters

# ============================================================================
# Figure Metadata
# ============================================================================

# Complete list of figures to be generated
FIGURE_LIST = [
    {
        'number': 1,
        'filename': '01_rubric_comparison',
        'title': 'Rubric Format Comparison',
        'description': 'Inter-rater reliability (ICC) by rubric format',
        'type': 'bar_chart',
        'data_source': 'rubric_comparison.py',
    },
    {
        'number': 2,
        'filename': '02_model_constitution_heatmap',
        'title': 'Model × Constitution Interaction',
        'description': 'Mean overall scores across 5 models and 6 constitutions',
        'type': 'heatmap',
        'data_source': 'interaction_analysis.py',
    },
    {
        'number': 3,
        'filename': '03_evaluator_agreement_matrix',
        'title': 'Evaluator Agreement Matrix',
        'description': 'Pairwise correlations between 5 LLM evaluators',
        'type': 'heatmap',
        'data_source': 'evaluator_agreement.py',
    },
    {
        'number': 4,
        'filename': '04_dimensional_structure_pca',
        'title': 'Dimensional Structure (PCA)',
        'description': 'Principal component analysis of 2D rubric structure',
        'type': 'biplot',
        'data_source': 'dimensional_analysis.py',
    },
    {
        'number': 5,
        'filename': '05_score_distributions_by_model',
        'title': 'Score Distributions by Model',
        'description': 'Violin plots showing score distributions for each model',
        'type': 'violin',
        'data_source': 'interaction_analysis.py',
    },
    {
        'number': 6,
        'filename': '06_score_distributions_by_constitution',
        'title': 'Score Distributions by Constitution',
        'description': 'Violin plots showing score distributions for each constitution',
        'type': 'violin',
        'data_source': 'interaction_analysis.py',
    },
    {
        'number': 7,
        'filename': '07_interaction_plot',
        'title': 'Model × Constitution Interaction Plot',
        'description': 'Line plot showing how models respond to different constitutions',
        'type': 'line',
        'data_source': 'interaction_analysis.py',
    },
    {
        'number': 8,
        'filename': '08_evaluator_icc_forest',
        'title': 'Evaluator Reliability (ICC Forest Plot)',
        'description': 'Individual evaluator ICC vs. ensemble ICC',
        'type': 'forest',
        'data_source': 'evaluator_agreement.py',
    },
    {
        'number': 9,
        'filename': '09_dimensional_scatter',
        'title': 'Integrity × Transparency Scatter',
        'description': 'Scatter plot of two rubric dimensions',
        'type': 'scatter',
        'data_source': 'dimensional_analysis.py',
    },
    {
        'number': 10,
        'filename': '10_ceiling_effect_evidence',
        'title': 'Ceiling Effects in Discrete Rubrics',
        'description': 'Score distributions showing 96-99% PASS rates',
        'type': 'histogram',
        'data_source': 'rubric_comparison.py',
    },
    {
        'number': 11,
        'filename': '11_evaluation_coverage_heatmap',
        'title': 'Evaluation Coverage',
        'description': 'Trials × Evaluators completion heatmap',
        'type': 'heatmap',
        'data_source': 'evaluator_agreement.py',
    },
    {
        'number': 12,
        'filename': '12_rubric_score_ranges',
        'title': 'Score Range Comparison by Rubric',
        'description': 'Box plots showing score variance across rubric formats',
        'type': 'box',
        'data_source': 'rubric_comparison.py',
    },
]

# ============================================================================
# Validation
# ============================================================================

def validate_config():
    """Validate configuration is properly set up."""
    errors = []

    # Check directories exist
    if not EXPERIMENT_DIR.exists():
        errors.append(f"Experiment directory not found: {EXPERIMENT_DIR}")

    # Check color palette completeness
    if len(MODEL_COLORS) != len(MODEL_DISPLAY_NAMES):
        errors.append("MODEL_COLORS and MODEL_DISPLAY_NAMES lengths don't match")

    if len(CONSTITUTION_COLORS) != len(CONSTITUTION_DISPLAY_NAMES):
        errors.append("CONSTITUTION_COLORS and CONSTITUTION_DISPLAY_NAMES lengths don't match")

    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    print("✅ Configuration validated successfully")

if __name__ == "__main__":
    # Run validation when executed directly
    validate_config()
    print(f"\n📁 Figures will be saved to: {FIGURES_DIR}")
    print(f"📁 Web data will be exported to: {WEB_DATA_DIR}")
    print(f"\n🎨 Configured {len(FIGURE_LIST)} figures to generate")
