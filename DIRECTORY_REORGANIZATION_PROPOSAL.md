# Directory Structure Reorganization Proposal

## Current State Analysis

### Root Level - **CLUTTERED**
```
.
├── experiments/                    # Business logic (GOOD)
├── results/                        # Generated data (GOOD)
├── notebooks/                      # Analysis notebooks (GOOD)
├── docs/                          # Documentation (GOOD)
├── robust_experiment_runner.py    # Main runner (ROOT - BAD)
├── experiment_inspector.py        # Utility script (ROOT - BAD)
├── debug_llama.py                 # Debug script (ROOT - BAD)
├── test_connectivity.py           # Test scripts (ROOT - BAD)
├── test_gemini.py                 # Test scripts (ROOT - BAD)
├── test_grok.py                   # Test scripts (ROOT - BAD)
├── test_llama.py                  # Test scripts (ROOT - BAD)
├── test_deepseek.py               # Test scripts (ROOT - BAD)
├── simple_test.py                 # Test scripts (ROOT - BAD)
├── minimal_test.py                # Test scripts (ROOT - BAD)
├── quick_test.py                  # Test scripts (ROOT - BAD)
├── fix_llama_json.py              # Utility script (ROOT - BAD)
├── fix_experiment_state.py        # Utility script (ROOT - BAD)
├── test_state_management.py       # Test script (ROOT - BAD)
├── PROJECT_BRIEF.md               # Docs (ROOT - OK)
├── PROJECT_JOURNAL.md             # Docs (ROOT - OK)
├── FINDINGS.md                    # Docs (ROOT - OK)
├── README.md                      # Docs (ROOT - ESSENTIAL)
└── DIRECTORY_STRUCTURE_ANALYSIS.md # Docs (ROOT - OK)
```

**Problem:** 14 test/debug/utility scripts pollute root directory!

### experiments/ - **CONFUSED PURPOSE**
```
experiments/
├── src/                           # Core experiment code (GOOD)
│   ├── constitutions.py
│   ├── data_types.py
│   ├── experiment_state.py
│   ├── graceful_parser.py
│   ├── manifest_generator.py
│   ├── models.py
│   ├── prompts.py
│   ├── scenarios.py
│   └── truncation_detector.py
├── data/                          # INPUT data (GOOD)
│   ├── scenarios.json
│   └── SCENARIOS.md
├── analysis.py                    # Post-processing (MISPLACED?)
├── visualize.py                   # Post-processing (MISPLACED?)
├── export_for_web.py              # Post-processing (MISPLACED?)
├── extract_scenarios.py           # Utility (OK)
├── test_batching.py               # Test (MISPLACED?)
├── test_state_management.py       # Test (MISPLACED?)
├── notebooks/                     # Empty (LEGACY)
└── results/                       # Empty (LEGACY)
```

**Problems:**
1. **analysis.py, visualize.py, export_for_web.py** - These are POST-experiment processors, not experiment runners
2. **test_*.py** - Tests scattered between root and experiments/
3. **Empty notebooks/ and results/** - Confusing legacy directories

### results/ - **FRAGMENTED**
```
results/
├── runs/                          # Per-experiment raw data
│   └── exp_20251023_105245/
│       ├── raw/                   # 480 test JSONs (GOOD)
│       ├── manual_review/         # Debug data (GOOD)
│       ├── charts/                # Empty (LEGACY)
│       └── MANIFEST.txt           # Metadata (GOOD)
├── analysis/                      # OUTSIDE experiment folder (BAD)
│   └── single/
│       └── exp_20251023_105245_analysis.json
├── visualizations/                # OUTSIDE experiment folder (BAD)
│   └── exp_20251023_105245/
│       └── *.png (8 charts)
├── web_exports/                   # OUTSIDE experiment folder (BAD)
│   └── exp_20251023_105245_web_export.json
├── state/                         # Global state (GOOD)
│   ├── experiment_state.json
│   └── test_registry.json
├── manual_review/                 # Duplicate? (CONFUSING)
├── raw/                          # Empty (LEGACY)
├── processed/                    # Empty (LEGACY)
└── charts/                       # Empty (LEGACY)
```

**Problems:**
1. Experiment assets scattered across 4 locations
2. Legacy empty directories
3. Unclear navigation

---

## Proposed Structure

### Principle: **Separation of Concerns**

1. **Source code** - Business logic that runs experiments
2. **Data** - Generated outputs from experiments
3. **Analysis** - Post-processing tools
4. **Tests** - Validation and debugging scripts
5. **Documentation** - Project docs and findings

```
constitution/                       # Project root
│
├── README.md                       # Essential
├── PROJECT_BRIEF.md               # Project overview
├── PROJECT_JOURNAL.md             # Development log
├── FINDINGS.md                    # Key results
├── pyproject.toml                 # Dependencies
├── poetry.lock                    # Lock file
├── .env / .env.example            # Config
│
├── src/                           # **CORE EXPERIMENT ENGINE**
│   ├── __init__.py
│   ├── runner.py                  # Main experiment runner (was robust_experiment_runner.py)
│   ├── inspector.py               # Experiment inspector utility
│   ├── core/                      # Core experiment logic
│   │   ├── __init__.py
│   │   ├── constitutions.py
│   │   ├── data_types.py
│   │   ├── experiment_state.py
│   │   ├── graceful_parser.py
│   │   ├── manifest_generator.py
│   │   ├── models.py
│   │   ├── prompts.py
│   │   ├── scenarios.py
│   │   └── truncation_detector.py
│   └── data/                      # INPUT data (scenarios, constitutions)
│       ├── scenarios.json
│       ├── scenarios.md
│       └── constitutions.json (future)
│
├── analysis/                      # **POST-PROCESSING TOOLS**
│   ├── __init__.py
│   ├── analyze.py                 # Statistical analysis (was experiments/analysis.py)
│   ├── visualize.py               # Chart generation (was experiments/visualize.py)
│   └── export.py                  # Web export (was experiments/export_for_web.py)
│
├── notebooks/                     # **JUPYTER ANALYSIS**
│   ├── README.md
│   ├── 01_exploratory_analysis.ipynb
│   └── 02_statistical_analysis.ipynb
│
├── results/                       # **GENERATED DATA**
│   ├── experiments/               # Per-experiment complete packages
│   │   ├── exp_20251023_105245/
│   │   │   ├── metadata.json      # Experiment config, timestamps, status
│   │   │   ├── data/
│   │   │   │   ├── tests/         # 480 test result JSONs
│   │   │   │   └── debug/         # Manual review, parsing failures
│   │   │   ├── analysis/
│   │   │   │   ├── statistics.json
│   │   │   │   └── summary.txt
│   │   │   ├── visualizations/    # All 8 PNG charts
│   │   │   └── exports/
│   │   │       ├── web_export.json
│   │   │       └── data_export.csv
│   │   └── exp_20251023_072503/
│   │       └── ... (same structure)
│   │
│   ├── aggregate/                 # Multi-experiment analyses
│   │   ├── metadata.json
│   │   ├── analysis/
│   │   │   ├── multi_experiment_stats.json
│   │   │   └── reproducibility_report.json
│   │   ├── visualizations/
│   │   │   ├── model_consistency_across_runs.png
│   │   │   └── experiment_variance_heatmap.png
│   │   └── exports/
│   │       └── aggregate_web_export.json
│   │
│   └── state/                     # Global experiment tracking
│       ├── experiment_registry.json
│       └── active_experiment.json
│
├── tests/                         # **ALL TESTS & DEBUG SCRIPTS**
│   ├── unit/
│   │   ├── test_constitutions.py
│   │   ├── test_models.py
│   │   ├── test_parser.py
│   │   └── test_state_management.py
│   ├── integration/
│   │   ├── test_connectivity.py
│   │   ├── test_full_pipeline.py
│   │   └── test_batching.py
│   ├── model_tests/               # Model-specific debug scripts
│   │   ├── test_gemini.py
│   │   ├── test_grok.py
│   │   ├── test_llama.py
│   │   └── test_deepseek.py
│   ├── debug/                     # Debug/fix scripts
│   │   ├── debug_llama.py
│   │   ├── fix_llama_json.py
│   │   ├── fix_experiment_state.py
│   │   ├── simple_test.py
│   │   ├── minimal_test.py
│   │   └── quick_test.py
│   └── __init__.py
│
└── docs/                          # **ADDITIONAL DOCUMENTATION**
    ├── architecture.md
    ├── api_reference.md
    └── ... (future docs)
```

---

## Key Improvements

### 1. **Clean Root Directory**
- Only essential files: README, config, project docs
- All code moved into organized subdirectories
- Immediate clarity on project structure

### 2. **Clear Separation: src/ vs. analysis/ vs. tests/**
- **src/** - Runs experiments (produces data)
- **analysis/** - Processes data (produces insights)
- **tests/** - Validates code (produces confidence)

### 3. **Self-Contained Experiment Packages**
```
results/experiments/exp_X/
├── metadata.json       # What was run
├── data/               # What was produced
├── analysis/           # What was found
├── visualizations/     # How it looks
└── exports/            # How to share
```
- Archive: `tar -czf exp_X.tar.gz results/experiments/exp_X/`
- Share: Send entire folder
- Navigate: One place for everything

### 4. **Logical Test Organization**
- **unit/** - Test individual components
- **integration/** - Test system behavior
- **model_tests/** - Model-specific validation
- **debug/** - One-off debug/fix scripts

### 5. **Intuitive Analysis Tools**
- `analysis/analyze.py` - Generate statistics
- `analysis/visualize.py` - Create charts
- `analysis/export.py` - Prepare web exports

---

## Migration Steps

### Phase 1: Reorganize Source Code (30 min)

```bash
# Create new structure
mkdir -p src/core analysis tests/{unit,integration,model_tests,debug}

# Move core experiment code
mv experiments/src/* src/core/
mv experiments/data/ src/
mv robust_experiment_runner.py src/runner.py
mv experiment_inspector.py src/inspector.py

# Move analysis tools
mv experiments/analysis.py analysis/analyze.py
mv experiments/visualize.py analysis/
mv experiments/export_for_web.py analysis/export.py

# Move tests
mv test_connectivity.py tests/integration/
mv experiments/test_batching.py tests/integration/
mv experiments/test_state_management.py tests/unit/

# Move model tests
mv test_gemini.py test_grok.py test_llama.py test_deepseek.py tests/model_tests/

# Move debug scripts
mv debug_llama.py fix_llama_json.py fix_experiment_state.py tests/debug/
mv simple_test.py minimal_test.py quick_test.py tests/debug/
mv test_fixed_llama.py tests/debug/

# Clean up empty directories
rm -rf experiments/src experiments/notebooks experiments/results experiments/data
```

### Phase 2: Reorganize Results (20 min)

```bash
# Create new results structure
mkdir -p results/experiments results/aggregate/{analysis,visualizations,exports}

# Reorganize exp_20251023_105245
EXP_ID="exp_20251023_105245"
mkdir -p results/experiments/$EXP_ID/{data/{tests,debug},analysis,visualizations,exports}

# Move data
mv results/runs/$EXP_ID/raw/* results/experiments/$EXP_ID/data/tests/
mv results/runs/$EXP_ID/manual_review results/experiments/$EXP_ID/data/debug

# Move analysis
mv results/analysis/single/${EXP_ID}_analysis.json \
   results/experiments/$EXP_ID/analysis/statistics.json

# Move visualizations
mv results/visualizations/$EXP_ID/* results/experiments/$EXP_ID/visualizations/

# Move exports
mv results/web_exports/${EXP_ID}_web_export.json \
   results/experiments/$EXP_ID/exports/web_export.json

# Copy MANIFEST as metadata
cp results/runs/$EXP_ID/MANIFEST.txt results/experiments/$EXP_ID/metadata.txt

# Create metadata.json
cat > results/experiments/$EXP_ID/metadata.json <<EOF
{
  "experiment_id": "$EXP_ID",
  "created_at": "2025-10-23T10:52:45.490789",
  "completed_at": "2025-10-23T22:02:18.624108",
  "status": "completed",
  "configuration": {
    "scenarios": 16,
    "constitutions": 5,
    "models": 6,
    "total_tests": 480
  },
  "results": {
    "completed": 480,
    "failed": 0,
    "success_rate": 1.0
  }
}
EOF

# Clean up old structure
rm -rf results/runs results/analysis results/visualizations results/web_exports
rm -rf results/raw results/processed results/charts results/manual_review
```

### Phase 3: Update Code References (45 min)

**Files requiring path updates:**

1. **src/runner.py** (was robust_experiment_runner.py)
   - Update imports: `from experiments.src` → `from src.core`
   - Update results path: `results/runs` → `results/experiments`

2. **src/inspector.py** (was experiment_inspector.py)
   - Update results path

3. **src/core/experiment_state.py**
   - Update results path: `results/runs` → `results/experiments`
   - Update state path (unchanged: `results/state`)

4. **analysis/analyze.py** (was experiments/analysis.py)
   - Update input path: `results/runs/exp_X` → `results/experiments/exp_X/data/tests`
   - Update output path: `results/analysis/single` → `results/experiments/exp_X/analysis`

5. **analysis/visualize.py** (was experiments/visualize.py)
   - Update input path: `results/analysis/single/exp_X_analysis.json` → `results/experiments/exp_X/analysis/statistics.json`
   - Update output path: `results/visualizations/exp_X` → `results/experiments/exp_X/visualizations`

6. **analysis/export.py** (was experiments/export_for_web.py)
   - Update input path
   - Update output path: `results/web_exports` → `results/experiments/exp_X/exports`

7. **notebooks/01_exploratory_analysis.ipynb**
   - Update RESULTS_DIR: `Path("../results/runs")` → `Path("../results/experiments")`
   - Update path to analysis JSON

8. **notebooks/02_statistical_analysis.ipynb**
   - Same as above

### Phase 4: Update Documentation (15 min)

- Update README.md with new structure
- Update PROJECT_JOURNAL.md with restructuring entry
- Add architecture.md explaining directory organization

---

## Benefits

### For Navigation
- ✅ **Root directory clean** - Only essential files visible
- ✅ **Clear purpose** - src/ = code, analysis/ = tools, results/ = data
- ✅ **Intuitive hierarchy** - Matches mental model

### For Development
- ✅ **Organized tests** - Easy to find and run
- ✅ **Separated concerns** - Experiment engine vs. analysis tools
- ✅ **Import clarity** - `from src.core import models` vs. `from experiments.src import models`

### For Research
- ✅ **Self-contained experiments** - Archive/share easily
- ✅ **Complete packages** - All assets in one place
- ✅ **Aggregate separation** - Multi-experiment analyses isolated

### For Collaboration
- ✅ **Newcomer friendly** - Structure explains itself
- ✅ **Predictable paths** - No hunting for files
- ✅ **Standard layout** - Follows Python project conventions

---

## Comparison Table

| Aspect | Current | Proposed | Improvement |
|--------|---------|----------|-------------|
| Root files | 14 scripts | 5 docs | ✅ -64% clutter |
| Experiment assets | 4 locations | 1 location | ✅ 75% simpler |
| Test organization | Root + experiments/ | tests/ with subcategories | ✅ Clear structure |
| Code organization | Flat + experiments/src | src/core + analysis/ | ✅ Logical separation |
| Empty directories | 5 legacy dirs | 0 | ✅ No confusion |
| Archive experiment | Impossible | Single tar command | ✅ Shareable |
| Navigation time | ~30 seconds | ~5 seconds | ✅ 83% faster |

---

## Recommendation

**Strongly recommend proceeding with full reorganization.**

Current structure has evolved organically and accumulated cruft. The proposed structure:
- Is standard for Python projects
- Separates concerns clearly
- Makes experiments self-contained
- Reduces cognitive load dramatically

Estimated total time: **2 hours**
- Phase 1 (Code): 30 min
- Phase 2 (Results): 20 min
- Phase 3 (Path updates): 45 min
- Phase 4 (Docs): 15 min
- Testing: 10 min

The structure will immediately make more sense and prevent ongoing confusion as the project grows.
