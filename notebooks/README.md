# Constitutional Reasoning Experiment - Jupyter Notebooks

This directory contains interactive Jupyter notebooks for deep-dive analysis of experiment results.

## Available Notebooks

### 1. **01_exploratory_analysis.ipynb**
**Purpose:** Interactive data exploration and visualization

**Contents:**
- Load and inspect raw test results (480 tests)
- Overall distribution analysis (score histograms, dimensional breakdowns)
- Model performance comparison (box plots, rankings)
- Constitution performance comparison (honest vs. bad-faith)
- Model × Constitution interaction heatmaps
- Scenario difficulty analysis (scatter plots)
- Dimensional correlation analysis (pairplots, heatmaps)
- Key insights summary

**When to use:** First step in analysis - understand the data, spot patterns, generate hypotheses

---

### 2. **02_statistical_analysis.ipynb**
**Purpose:** Rigorous statistical hypothesis testing

**Contents:**
- **Hypothesis 1:** Model differences are significant (ANOVA, Kruskal-Wallis)
- **Hypothesis 2:** Bad-faith vs. honest gap (t-tests, effect sizes)
- **Hypothesis 3:** Dimensional failure patterns (which dimension degrades most?)
- **Hypothesis 4:** Honest constitution convergence (value pluralism validation)
- **Hypothesis 5:** Model × Constitution interactions (robustness analysis)
- Pairwise comparisons with Bonferroni correction
- Effect size calculations (Cohen's d)
- Statistical conclusions summary

**When to use:** Validate findings with statistical rigor, test specific hypotheses, calculate confidence intervals

---

## Getting Started

### Prerequisites

```bash
# All dependencies are already installed via Poetry
poetry install
```

### Launch Jupyter

```bash
# From project root
poetry run jupyter notebook notebooks/

# Or use Jupyter Lab
poetry run jupyter lab notebooks/
```

### Quick Start

1. **Open `01_exploratory_analysis.ipynb`** first
2. Run all cells (Cell → Run All)
3. Explore interactive visualizations
4. Note interesting patterns
5. **Move to `02_statistical_analysis.ipynb`**
6. Test specific hypotheses about patterns you observed

## Notebook Structure

Each notebook follows this pattern:

1. **Setup** - Import libraries, load data
2. **Analysis Sections** - Focused explorations with visualizations
3. **Summary** - Key takeaways and conclusions

All notebooks use the same dataset: `results/experiments/exp_20251023_105245/`

## Data Schema

Each test result contains:
- `test_id`: Unique identifier (scenario_constitution_model)
- `scenario_id`: Ethical dilemma tested
- `constitution_id`: Value framework applied
- `model_id`: AI model used
- `factual_adherence`: Did it stick to facts? (0-100)
- `value_transparency`: Did it state its values? (0-100)
- `logical_coherence`: Do conclusions follow from values? (0-100)
- `overall_score`: Mean of three dimensions

## Extending the Notebooks

### Adding New Analyses

```python
# Template for new analysis section
# --- Add to any notebook ---

# Your analysis title
print("Custom Analysis: [Your Question]")
print("="*60)

# Filter data
subset = df[df['model_id'] == 'gemini-2-5-flash']

# Compute statistics
result = subset['overall_score'].describe()

# Visualize
plt.figure(figsize=(10, 6))
plt.hist(subset['overall_score'], bins=20)
plt.title('Your Analysis Title')
plt.show()
```

### Common Tasks

**Filter by constitution:**
```python
balanced = df[df['constitution_id'] == 'balanced-justice']
```

**Filter by model:**
```python
claude = df[df['model_id'] == 'claude-sonnet-4-5']
```

**Compare two groups:**
```python
from scipy.stats import ttest_ind

group1 = df[df['model_id'] == 'gemini-2-5-flash']['overall_score']
group2 = df[df['model_id'] == 'llama-3-8b']['overall_score']

t_stat, p_value = ttest_ind(group1, group2)
print(f"t-statistic: {t_stat:.4f}, p-value: {p_value:.6f}")
```

## Tips for Analysis

1. **Always check assumptions** - Test normality before parametric tests
2. **Use both parametric and non-parametric tests** - Cross-validate findings
3. **Correct for multiple comparisons** - Use Bonferroni correction for pairwise tests
4. **Report effect sizes** - p-values alone don't tell the full story
5. **Visualize everything** - Patterns are easier to spot in charts

## Output

Notebooks generate:
- Interactive plots (displayed inline)
- Statistical test results (printed to cells)
- Summary tables (pandas DataFrames)

To save figures:
```python
plt.savefig('../results/custom_analysis.png', dpi=300, bbox_inches='tight')
```

## Troubleshooting

**Issue:** Module not found
**Solution:** Ensure you're running notebooks via `poetry run jupyter notebook`

**Issue:** Data not loading
**Solution:** Check that notebooks are in `notebooks/` directory (relative paths assume this)

**Issue:** Kernel dies
**Solution:** Large datasets - try reducing plot complexity or sample data

## Next Steps

After completing notebook analysis:
- Generate final report (FINDINGS.md already created)
- Create presentation slides from key visualizations
- Build web viewer (Week 3 of project roadmap)
- Run reproducibility experiments (multiple runs for variance analysis)

## Questions?

Refer to:
- `FINDINGS.md` - Automated analysis results
- `PROJECT_BRIEF.md` - Overall project goals
- `PROJECT_JOURNAL.md` - Development methodology

---

**Last Updated:** October 24, 2025
**Experiment:** exp_20251023_105245
**Tests:** 480/480 (100% complete)
