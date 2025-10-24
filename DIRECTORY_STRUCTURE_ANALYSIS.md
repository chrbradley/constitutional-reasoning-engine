# Directory Structure Analysis & Proposal

## Current Structure Problems

### 1. **Fragmented Experiment Data**

**Current State:**
```
results/
├── runs/
│   └── exp_20251023_105245/        # Raw test data lives here
│       ├── raw/                     # 480 JSON files with full test pipeline
│       ├── manual_review/           # Parsing failures
│       ├── charts/                  # (empty)
│       └── MANIFEST.txt
├── analysis/
│   └── single/
│       └── exp_20251023_105245_analysis.json    # Lives OUTSIDE experiment folder
├── visualizations/
│   └── exp_20251023_105245/        # Lives OUTSIDE experiment folder
│       └── *.png (8 charts)
├── web_exports/
│   └── exp_20251023_105245_web_export.json     # Lives OUTSIDE experiment folder
├── state/                           # Global state tracking
│   ├── experiment_state.json
│   └── test_registry.json
├── manual_review/                   # Duplicate location? Legacy?
├── raw/                            # Empty - legacy?
├── processed/                      # Empty - legacy?
└── charts/                         # Empty - legacy?
```

**Problems:**
1. **Experiment assets are scattered** - To find all data for exp_20251023_105245, you must look in:
   - `results/runs/exp_20251023_105245/` (raw data)
   - `results/analysis/single/` (statistical analysis)
   - `results/visualizations/exp_20251023_105245/` (charts)
   - `results/web_exports/` (web export)

2. **No single-experiment cohesion** - Can't simply `tar -czf experiment.tar.gz results/runs/exp_ID/` to archive

3. **Unclear navigation** - "Where are the charts for experiment X?" requires knowledge of structure

4. **Empty legacy directories** - `results/raw/`, `results/charts/`, `results/processed/` serve no purpose

5. **Duplicate paths** - `results/manual_review/` vs `results/runs/exp_X/manual_review/`

## Proposed Structure

### **Experiment-Centric Organization**

```
results/
├── experiments/                              # All experiment runs
│   ├── exp_20251023_105245/                  # Complete experiment package
│   │   ├── metadata.json                     # Experiment config, timestamp, status
│   │   ├── data/
│   │   │   ├── raw/                          # 480 test result JSON files
│   │   │   └── manual_review/                # Parsing failures for debugging
│   │   ├── analysis/
│   │   │   ├── statistics.json               # Full statistical analysis
│   │   │   └── summary.txt                   # Human-readable summary
│   │   ├── visualizations/                   # All charts for this experiment
│   │   │   ├── 01_model_rankings.png
│   │   │   ├── 02_constitution_rankings.png
│   │   │   └── ... (6 more)
│   │   └── exports/
│   │       ├── web_export.json               # For web viewer
│   │       └── data_export.csv               # For external analysis
│   │
│   └── exp_20251023_072503/                  # Another experiment
│       └── ... (same structure)
│
├── aggregate/                                # Cross-experiment analyses
│   ├── multi_experiment_analysis.json        # Aggregated statistics
│   ├── reproducibility_report.json           # Variance across runs
│   ├── visualizations/                       # Comparison charts
│   │   ├── model_consistency_across_runs.png
│   │   └── experiment_variance_heatmap.png
│   └── exports/
│       └── aggregate_web_export.json
│
└── state/                                    # Global tracking (unchanged)
    ├── experiment_registry.json              # All experiments metadata
    └── active_experiment.json                # Current experiment being run
```

### **Key Improvements**

1. **Self-Contained Experiments** - Everything for exp_X lives in `results/experiments/exp_X/`
   - Easy to archive: `tar -czf exp_X.tar.gz results/experiments/exp_X/`
   - Easy to share: Send entire folder
   - Easy to navigate: One place to look

2. **Clear Hierarchy** - Data → Analysis → Visualizations → Exports
   - Intuitive flow matches the processing pipeline
   - New team members can understand immediately

3. **Aggregate Separation** - Multi-experiment analyses live in `results/aggregate/`
   - Clear distinction between single-run and multi-run
   - Matches our analysis.py design (single vs. aggregate)

4. **No Empty Directories** - Remove legacy unused paths

5. **Consistent Naming** - `metadata.json`, `statistics.json`, `web_export.json` (not `exp_X_analysis.json`)

## Migration Plan

### Phase 1: Reorganize Current Experiment

```bash
# Create new structure
mkdir -p results/experiments/exp_20251023_105245/{data,analysis,visualizations,exports}

# Move raw data
mv results/runs/exp_20251023_105245/raw results/experiments/exp_20251023_105245/data/
mv results/runs/exp_20251023_105245/manual_review results/experiments/exp_20251023_105245/data/

# Move analysis
mv results/analysis/single/exp_20251023_105245_analysis.json \
   results/experiments/exp_20251023_105245/analysis/statistics.json

# Move visualizations
mv results/visualizations/exp_20251023_105245 \
   results/experiments/exp_20251023_105245/visualizations

# Move exports
mv results/web_exports/exp_20251023_105245_web_export.json \
   results/experiments/exp_20251023_105245/exports/web_export.json

# Create metadata file
cat > results/experiments/exp_20251023_105245/metadata.json <<EOF
{
  "experiment_id": "exp_20251023_105245",
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
rm -rf results/runs
rm -rf results/analysis/single
rm -rf results/visualizations
rm -rf results/web_exports
rm -rf results/raw results/processed results/charts  # Legacy empty dirs
```

### Phase 2: Update Code References

Files to update:
1. `experiments/analysis.py` - Change output paths
2. `experiments/visualize.py` - Change input/output paths
3. `experiments/export_for_web.py` - Change output paths
4. `notebooks/01_exploratory_analysis.ipynb` - Update RESULTS_DIR path
5. `notebooks/02_statistical_analysis.ipynb` - Update RESULTS_DIR path

Example change in `analysis.py`:
```python
# OLD
self.analysis_dir = base_dir / "analysis" / "single"

# NEW
self.analysis_dir = base_dir / "experiments" / experiment_id / "analysis"
```

### Phase 3: Create aggregate/ Structure

```bash
mkdir -p results/aggregate/{visualizations,exports}

# This will be populated when we run multi-experiment analysis
```

### Phase 4: Update Documentation

- README.md - Update directory structure documentation
- FINDINGS.md - Update file paths in references
- PROJECT_JOURNAL.md - Document restructuring

## Benefits Summary

### For Users:
- ✅ **Intuitive** - "Where's experiment X data?" → `results/experiments/exp_X/`
- ✅ **Complete** - Everything in one place
- ✅ **Shareable** - Easy to archive and distribute
- ✅ **Discoverable** - Clear hierarchy shows data flow

### For Developers:
- ✅ **Maintainable** - Predictable paths, no scattered files
- ✅ **Extensible** - Easy to add new experiment types
- ✅ **Debuggable** - All experiment artifacts together
- ✅ **Scalable** - Works for 1 or 100 experiments

### For Research:
- ✅ **Reproducible** - Complete experiment packages
- ✅ **Comparable** - Consistent structure across experiments
- ✅ **Archivable** - Self-contained for long-term storage
- ✅ **Publishable** - Easy to share datasets

## Alternative: Keep Current Structure?

**Arguments against current structure:**
- No clear organizing principle (experiment-centric vs. file-type-centric confusion)
- Requires mental map to find data
- Difficult to explain to new users
- Hard to archive/share individual experiments
- Legacy directories create confusion

**I cannot find a compelling argument to keep the current structure.**

The proposed experiment-centric organization is:
- More intuitive
- Easier to navigate
- Better for collaboration
- Aligned with research best practices
- Consistent with our multi-experiment goals

## Recommendation

**Proceed with migration** using the 4-phase plan above.

Estimated effort: 2-3 hours (mostly code path updates and testing).

Benefits are immediate and will prevent confusion as we:
- Run additional experiments
- Build the web viewer (Week 3)
- Share results with collaborators
- Archive experiments for publication
