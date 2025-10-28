# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Constitutional Reasoning Engine** - an AI safety research project that tests whether frontier models can maintain factual integrity while reasoning from different value systems. It runs systematic experiments across 6 models × 5 constitutional frameworks × multiple scenarios.

**Core Question:** Can AI systems hold different values while maintaining intellectual honesty, or do value systems require motivated reasoning (fact distortion)?

## Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Set up API keys (copy .env.example to .env and add keys)
cp .env.example .env

# Test API connectivity
poetry run python tests/model_tests/test_connectivity.py
```

### Running Experiments
```bash
# Run full experiment (smart mode: resumes incomplete or starts new)
poetry run python -m src.runner

# Force start new experiment
poetry run python -m src.runner --new

# Resume specific experiment
poetry run python -m src.runner --resume exp_20251025_121451

# Check experiment status
poetry run python -m src.inspector

# Run single test (for quick validation)
poetry run python test_single.py
```

### Analysis & Visualization
```bash
# Generate statistical analysis
poetry run python -m analysis.analyze --experiment exp_20251023_105245

# Create visualizations
poetry run python -m analysis.visualize --experiment exp_20251023_105245

# Export web-friendly JSON
poetry run python -m analysis.export --experiment exp_20251023_105245
```

### Code Quality
```bash
# Format code
poetry run black src/ analysis/ tests/

# Type checking
poetry run mypy src/

# Linting
poetry run flake8 src/ analysis/ tests/
```

## Architecture: Three-Layer Pipeline

The experiment runs each trial through three distinct layers:

### Layer 1: Fact Establishment (Currently Bypassed in Phase 1)
- **Status:** `SKIP_LAYER_1 = True` in `src/runner.py`
- **Phase 1:** Facts loaded directly from `src/data/scenarios.json`
- **Future Phases:** Will test different fact-grounding mechanisms (RAG, citations, etc.)
- **Output:** `results/experiments/{exp_id}/data/layer1/{trial_id}.json`

### Layer 2: Constitutional Reasoning
- **Input:** Established facts + constitutional framework
- **Process:** Model applies assigned values to facts
- **Key Feature:** Truncation detection with automatic retry (8K → 12K → 16K tokens)
- **Output:** `results/experiments/{exp_id}/data/layer2/{trial_id}.json`

### Layer 3: Integrity Evaluation
- **Evaluator:** Claude Sonnet 4.5 (consistent across all trials)
- **Scores 3 dimensions:**
  - Factual Adherence (0-100): Did it accept facts without distortion?
  - Value Transparency (0-100): Did it explicitly state values/tradeoffs?
  - Logical Coherence (0-100): Does conclusion follow from values?
- **Output:** `results/experiments/{exp_id}/data/layer3/{trial_id}.json`

## State Management Architecture (Critical)

**Pointer Pattern** - Per-experiment state with global pointer:

```
results/
├── state/
│   └── current_experiment.json          # Pointer to active experiment
└── experiments/
    ├── exp_20251025_121451/
    │   ├── data/                        # Layer 1/2/3 outputs
    │   ├── state/                       # Per-experiment state
    │   │   ├── experiment_state.json
    │   │   └── trial_registry.json
    │   ├── visualizations/
    │   └── metadata.json
    └── exp_20251023_105245/             # Previous experiments preserved
```

### Key State Management Methods (src/core/experiment_state.py)

```python
# ExperimentManager initialization
ExperimentManager()                      # Load from pointer or start fresh
ExperimentManager(experiment_id="...")   # Resume specific experiment

# Lifecycle methods
create_experiment(scenarios, constitutions, models)  # Start new
finalize_experiment(clear_pointer=True)              # Mark complete, clear pointer
```

### State Lifecycle
1. **Create:** `create_experiment()` → saves pointer to `results/state/current_experiment.json`
2. **Run:** Progress tracked in per-experiment `trial_registry.json`
3. **Complete:** `finalize_experiment()` → marks status="completed", clears pointer
4. **Resume:** Pointer allows automatic resume of incomplete experiments

**Important:** State files are **never deleted**, only the pointer is cleared. This preserves audit trail for debugging.

## JSON Parsing Strategy

Models return JSON in different formats:
- **Clean JSON:** Claude, GPT, DeepSeek, Grok (direct parse)
- **Markdown-wrapped:** Llama, Gemini (strip ```json blocks)

**GracefulJsonParser** (`src/core/graceful_parser.py`) handles all cases with fallback strategies:
1. Standard cleaning (remove markdown blocks)
2. Control character removal
3. Brace-balanced extraction
4. Manual review flagging for edge cases

**Key Feature:** Zero data loss - all unparseable responses saved to `data/debug/manual_review/` with original text preserved.

## Truncation Detection

**Problem:** Models sometimes truncate responses mid-JSON, especially Llama.

**Solution:** `TruncationDetector` (`src/core/truncation_detector.py`):
- Detects incomplete JSON (unclosed braces, mid-sentence cutoffs)
- Automatically retries with increased token limits: 8K → 12K → 16K
- Logs final token requirement per model

## Rate Limiting & Batching

**Batch Strategy** (`src/runner.py`):
- 12 trials per batch (2 per model to avoid rate limits)
- 20-second delay between batches
- Round-robin distribution ensures no model gets multiple trials in same batch

## Data Flow

1. **Scenarios:** Loaded from `src/data/scenarios.json` (Pydantic validation)
2. **Constitutions:** Defined in `src/core/constitutions.py` (5 frameworks)
3. **Models:** API calls via LiteLLM (`src/core/models.py`) - abstracts 6 providers
4. **Prompts:** Templates in `src/core/prompts.py` (f-strings with fact/value injection)
5. **Results:** Per-experiment directories with layer-segregated outputs

## Key Files for Code Changes

- **`src/core/experiment_state.py`**: State management, pointer logic
- **`src/runner.py`**: Main experiment runner, argparse CLI, batching
- **`src/core/models.py`**: LLM API wrappers, add new models here
- **`src/core/constitutions.py`**: Add new constitutional frameworks
- **`src/data/scenarios.json`**: Add new test scenarios
- **`src/core/prompts.py`**: Modify prompting strategy

## Common Patterns

### Adding a New Model
1. Add API key to `.env`
2. Add model config to `MODELS` list in `src/core/models.py`
3. Test connectivity: `poetry run python tests/model_tests/test_connectivity.py`
4. Run single test: `poetry run python test_single.py`

### Adding a New Constitution
1. Define in `src/core/constitutions.py` (Constitution class with system_prompt)
2. Add to `CONSTITUTIONS` list
3. Document in `docs/METHODOLOGY.md`

### Debugging Failed Tests
1. Check `results/experiments/{exp_id}/state/test_registry.json` for error messages
2. Look for manual review files in `data/debug/manual_review/`
3. Inspect layer outputs: `data/layer2/{trial_id}.json` for reasoning

## Important Constraints

### Phase 1 Current State
- Layer 1 is **bypassed** (facts from JSON, not API call)
- 5 scenarios (redesigned from 16 trivial scenarios to polarizing policy issues)
- Testing single-shot reasoning (no multi-turn conversations)

### Do Not
- Delete `results/experiments/` - these are preserved experiments
- Manually edit state files - use ExperimentManager methods
- Run experiments without checking `python -m src.runner --help` first
- Assume test_single.py uses separate directory - it uses `results/` like production

## Documentation Hierarchy

1. **README.md**: Quick start, project structure
2. **docs/PROJECT_OVERVIEW.md**: Vision, mission, research roadmap (3 phases)
3. **docs/METHODOLOGY.md**: Experimental design, scenarios, constitutions, scoring
4. **docs/TECHNICAL_ARCHITECTURE.md**: Implementation details, tech stack
5. **PROJECT_JOURNAL.md**: Development log with all major decisions/bug fixes

**Always check PROJECT_JOURNAL.md for recent architectural changes before modifying core systems.**

## Research Context

This is **Phase 1** of a 3-phase research program:
- **Phase 1 (Current):** Single-shot reasoning with uncontested facts
- **Phase 2 (Planned):** Testing fact-grounding mechanisms (RAG, citations, etc.)
- **Phase 3 (Planned):** Multi-turn adversarial resistance

Understanding the phase context is important when making changes - don't implement Phase 2/3 features prematurely.

## Experimental Design & Methodological Rigor

**CRITICAL:** This project involves scientific research with statistical analysis. Always follow these principles to ensure valid, reliable findings.

### Sample Size Requirements

**ALWAYS verify adequate sample size before drawing conclusions:**

| Analysis Type | Minimum n | Recommended n | Confidence Interval | Statistical Power |
|--------------|-----------|---------------|---------------------|-------------------|
| **Correlation (Pearson r)** |
| Rough estimate | 30 | 100 | ±0.18 | 0.60 |
| Reliable estimate | 100 | 200 | ±0.10 | 0.80 |
| Tight CI | 200 | 400 | ±0.07 | 0.95 |
| **T-test (comparing 2 groups)** |
| Large effect (d=0.8) | 26 | 50 | - | 0.80 |
| Medium effect (d=0.5) | 64 | 100 | - | 0.80 |
| Small effect (d=0.2) | 393 | 500 | - | 0.80 |
| **ANOVA (comparing 3+ groups)** |
| 2 groups, medium effect | 64 | 100 | - | 0.80 |
| 5 groups, medium effect | 100 | 150 | - | 0.80 |
| **Subgroup analysis** |
| Per group (k groups total) | n/k ≥ 30 | n/k ≥ 50 | - | 0.80 |

**Red flag example:** The initial 24-trial evaluator comparison showed r=0.061, but with n=24, the 95% CI spans ±0.35, making the estimate unreliable. The n=119 analysis (r=0.632, CI ±0.10) is much more trustworthy.

### Statistical Reporting Standards

**ALWAYS include these when reporting findings:**

1. **Confidence Intervals (not just point estimates)**
   - ❌ Bad: "Correlation is r=0.63"
   - ✅ Good: "Correlation is r=0.63, 95% CI [0.54, 0.71]"

2. **Effect Sizes (not just p-values)**
   - ❌ Bad: "Models differ significantly (p<0.05)"
   - ✅ Good: "Models differ significantly (F=12.3, p<0.001, η²=0.14, large effect)"

3. **Multiple Comparison Corrections**
   - If testing >3 hypotheses, use Bonferroni or FDR correction
   - Report both raw and adjusted p-values

4. **Assumption Checks**
   - Test normality (Shapiro-Wilk)
   - Test equal variance (Levene's test)
   - Report violations and use appropriate alternatives

### Premature Conclusion Prevention Checklist

**Before reporting ANY findings, verify:**

- [ ] **Sample size adequate:** n meets minimum for analysis type (see table above)
- [ ] **Confidence intervals reported:** Not just point estimates
- [ ] **Data quality verified:** Parsing success >90%, evaluator completion >95%
- [ ] **Assumptions tested:** Normality, equal variance, independence checked
- [ ] **Multiple comparisons corrected:** If testing >3 hypotheses simultaneously
- [ ] **Effect sizes reported:** Practical significance, not just statistical
- [ ] **Results replicate:** If using LLM judges, results consistent across evaluators (r>0.60)
- [ ] **Outliers investigated:** High-disagreement cases reviewed manually

**If ANY checkbox is unchecked, DO NOT report findings as conclusive.**

### Pilot Study Protocol

**ALWAYS run a pilot before full experiment:**

1. **Size:** 10-20% of planned sample
2. **Purpose:**
   - Check data quality (parsing, API reliability)
   - Estimate effect sizes (adjust sample size if needed)
   - Identify design flaws early (fail fast)
3. **Analysis:** Calculate preliminary correlations/means with WIDE CIs
4. **Decision:** Adjust design based on pilot, THEN run full experiment

**Example:** Phase 2 runs 20-trial pilot to test evaluation strategies before committing to 150+ trials.

### One Variable at a Time Principle

**Change ONE thing per experiment phase:**

✅ **Good:**
- Phase 2: Test evaluation design (multi-prompt vs single-prompt) on FIXED dataset
- Phase 3: Add scenarios with FIXED evaluation design

❌ **Bad:**
- Phase 2+3 combined: Change eval design AND add scenarios simultaneously
- **Problem:** Can't isolate which change caused differences in results

### Stratified Analysis Protocol

**Before scaling up, analyze existing data by subgroups:**

1. **By constitution:** Do some value systems show higher/lower agreement?
2. **By scenario:** Do some topics cause more evaluator disagreement?
3. **By dimension:** Which rubric dimensions have best inter-rater reliability?
4. **By score range:** Do evaluators agree more on high-scoring or low-scoring trials?

**Purpose:** Identify issues (outlier constitutions, ambiguous scenarios) BEFORE adding more data.

**Example:** Phase 1 diagnostic analysis checks if harm-minimization (the 24-trial subset) differs from other constitutions.

### Statistical Test Selection Guide

| Research Question | Data Type | Test | Python Function |
|-------------------|-----------|------|-----------------|
| Do 2 groups differ? | Continuous | Independent t-test | `scipy.stats.ttest_ind` |
| Do 3+ groups differ? | Continuous | One-way ANOVA | `scipy.stats.f_oneway` |
| Do 2 factors interact? | Continuous | Two-way ANOVA | `statsmodels.formula.api.ols` |
| Which groups differ? | Continuous | Tukey HSD | `scipy.stats.tukey_hsd` |
| Do 2 variables correlate? | Continuous | Pearson r | `scipy.stats.pearsonr` |
| Non-linear correlation? | Ordinal | Spearman ρ | `scipy.stats.spearmanr` |
| Do raters agree? | Binary | Cohen's Kappa | `sklearn.metrics.cohen_kappa_score` |
| Do raters agree? | Continuous | ICC | `pingouin.intraclass_corr` |

**Always check assumptions:**
- Normality: `scipy.stats.shapiro(data)` → If p<0.05, use non-parametric alternative
- Equal variance: `scipy.stats.levene(group1, group2)` → If p<0.05, use Welch's t-test
- Independence: Design check (no repeated measures unless using paired/mixed methods)

### Key References

- **Research Roadmap:** `docs/RESEARCH_ROADMAP.md` - Complete phased plan with decision points
- **Decision Log:** `docs/DECISION_LOG.md` - All major decisions with rationale
- **Sample Size Calculator:** `src/tools/sample_size_calculator.py` (Phase 0)
- **CI Calculator:** `src/tools/ci_calculator.py` (Phase 0)

### When to Flag Issues

**Immediately flag if:**
- Sample size below minimum for planned analysis
- Data quality <90% (parsing failures, API errors)
- Assumption violations not addressed
- Effect sizes calculated but not reported
- Multiple comparisons not corrected
- Findings reported without confidence intervals

**Example flagging:**
```
⚠️ WARNING: Sample size (n=24) is below minimum (n=100) for reliable correlation estimates.
Current CI: ±0.35 (estimate could range from r=-0.29 to r=+0.41)
Recommendation: Collect at least 76 more trials before drawing conclusions.
```

## Commit Message Guidelines

**Keep commit messages concise** - detailed context belongs in PROJECT_JOURNAL.md, not git history.

### Good (What changed + why in 1-2 lines)
```
Refactor state management to per-experiment directories

Eliminates stale state file blocking by using pointer pattern with preserved audit trail.
```

```
Add argparse CLI for experiment control

Enables --new and --resume flags for explicit experiment management.
```

```
Bypass Layer 1 for Phase 1 (facts from JSON)
```

### Bad (Too verbose - save this for PROJECT_JOURNAL.md)
```
Redesign Phase 1 experiment with 5 polarizing policy scenarios

**Rationale:**
Phase 1 iteration 1 tested 16 trivial scenarios...

**New Scenarios (5 replacing 16):**
1. Vaccine Mandate Religious Exemption...
2. Asylum Claim vs. Expedited Removal...
[20+ more lines]
```

### Workflow
1. **Make focused changes** - One logical unit of work per commit
2. **Document in PROJECT_JOURNAL.md** - Add detailed entry explaining rationale, implementation, impact
3. **Commit with concise message** - Reference what changed and why (1-2 sentences)
4. **Git log should be scannable** - Someone should understand the history at a glance

### Why This Matters
- Git history is for navigation ("When did we change X?")
- PROJECT_JOURNAL.md is for understanding ("Why did we change X and how?")
- Verbose commit messages duplicate information and clutter `git log --oneline`
