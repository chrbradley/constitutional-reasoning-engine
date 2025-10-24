# Reorganization Testing Plan

## Strategy: Test-After-Each-Phase

We'll reorganize in small, testable increments. After each phase, we run **Minimum Viable Tests (MVT)** to ensure nothing broke.

---

## Minimum Viable Test Suite

### MVT-1: Core Experiment Engine
**Purpose:** Verify experiment runner can still find and import all core modules

```bash
# Test imports
python -c "from src.core import models, constitutions, scenarios, experiment_state"
echo "✓ All core imports successful"

# Test data loading
python -c "from src.core.scenarios import load_scenarios; scenarios = load_scenarios('src/data/scenarios.json'); print(f'✓ Loaded {len(scenarios)} scenarios')"

# Test constitutions
python -c "from src.core.constitutions import CONSTITUTIONS; print(f'✓ Loaded {len(CONSTITUTIONS)} constitutions')"

# Test models
python -c "from src.core.models import MODELS; print(f'✓ Configured {len(MODELS)} models')"
```

**Expected output:**
```
✓ All core imports successful
✓ Loaded 16 scenarios
✓ Loaded 5 constitutions
✓ Configured 6 models
```

### MVT-2: State Management
**Purpose:** Verify experiment state system can read/write to new paths

```bash
# Test state paths
python -c "
from src.core.experiment_state import ExperimentManager
from pathlib import Path

# Initialize with new results path
em = ExperimentManager(base_dir=Path('results'))
print('✓ ExperimentManager initialized')

# Check state directory
state_dir = Path('results/state')
print(f'✓ State directory exists: {state_dir.exists()}')
"
```

**Expected output:**
```
✓ ExperimentManager initialized
✓ State directory exists: True
```

### MVT-3: Results Loading
**Purpose:** Verify analysis tools can load experiment data from new paths

```bash
# Test loading experiment results
python -c "
from pathlib import Path
import json

exp_id = 'exp_20251023_105245'
exp_dir = Path('results/experiments') / exp_id

# Check structure
assert exp_dir.exists(), f'Experiment directory missing: {exp_dir}'
assert (exp_dir / 'metadata.json').exists(), 'metadata.json missing'
assert (exp_dir / 'data/tests').exists(), 'data/tests/ missing'
assert (exp_dir / 'analysis').exists(), 'analysis/ missing'

# Load a test result
test_files = list((exp_dir / 'data/tests').glob('*.json'))
assert len(test_files) > 0, 'No test result files found'

with open(test_files[0]) as f:
    result = json.load(f)
    assert 'testId' in result, 'Invalid test result format'

print(f'✓ Successfully loaded experiment {exp_id}')
print(f'✓ Found {len(test_files)} test result files')
"
```

**Expected output:**
```
✓ Successfully loaded experiment exp_20251023_105245
✓ Found 480 test result files
```

### MVT-4: Analysis Pipeline
**Purpose:** Verify analysis tools work with new paths

```bash
# Test analysis script can find data
python -c "
from pathlib import Path
import sys
sys.path.insert(0, 'analysis')
from analyze import ExperimentAnalyzer

analyzer = ExperimentAnalyzer(base_dir=Path('results'))
exp_id = 'exp_20251023_105245'

# Check if experiment directory exists
exp_dir = Path('results/experiments') / exp_id
print(f'✓ Experiment directory: {exp_dir.exists()}')

# Check if statistics.json exists
stats_file = exp_dir / 'analysis/statistics.json'
print(f'✓ Statistics file: {stats_file.exists()}')
"
```

**Expected output:**
```
✓ Experiment directory: True
✓ Statistics file: True
```

### MVT-5: Notebooks
**Purpose:** Verify Jupyter notebooks can load data

```bash
# Test notebook data loading (without running full notebook)
python -c "
from pathlib import Path
import json

# Simulate notebook paths
EXPERIMENT_ID = 'exp_20251023_105245'
BASE_DIR = Path('.')
RESULTS_DIR = BASE_DIR / 'results' / 'experiments' / EXPERIMENT_ID

# Check paths
assert RESULTS_DIR.exists(), f'Results dir missing: {RESULTS_DIR}'
assert (RESULTS_DIR / 'data/tests').exists(), 'Test data missing'

# Count results
test_files = list((RESULTS_DIR / 'data/tests').glob('*.json'))
print(f'✓ Notebooks can access {len(test_files)} test results')
"
```

**Expected output:**
```
✓ Notebooks can access 480 test results
```

---

## Phase-by-Phase Testing

### Phase 1: Reorganize Source Code
**Changes:**
- Move `experiments/src/` → `src/core/`
- Move `experiments/data/` → `src/data/`
- Move `robust_experiment_runner.py` → `src/runner.py`
- Move analysis scripts to `analysis/`
- Move test scripts to `tests/`

**Tests to run:**
1. MVT-1: Core Experiment Engine ✓
2. Quick import check:
```bash
python -c "import sys; sys.path.insert(0, 'src'); from core import models; print('✓ Imports work')"
```

**Rollback if fails:** `git checkout .` (revert all changes)

### Phase 2: Reorganize Results Directory
**Changes:**
- Create `results/experiments/exp_X/` structure
- Move raw data, analysis, visualizations, exports
- Create metadata.json
- Remove old directories

**Tests to run:**
1. MVT-3: Results Loading ✓
2. Verify file count:
```bash
# Count test results
test_count=$(find results/experiments/exp_20251023_105245/data/tests -name "*.json" | wc -l)
echo "Test files: $test_count (expected: 480)"

# Count visualizations
viz_count=$(find results/experiments/exp_20251023_105245/visualizations -name "*.png" | wc -l)
echo "Visualizations: $viz_count (expected: 8)"
```

**Rollback if fails:** Restore from backup (created before phase)

### Phase 3: Update Code Paths
**Changes:**
- Update imports in all Python files
- Update path references

**Tests to run:**
1. ALL MVTs (1-5) ✓
2. Dry-run test:
```bash
# Test that runner can be imported
python -c "from src.runner import main; print('✓ Runner imports successfully')"
```

**Rollback if fails:** `git checkout <files>` (revert specific files)

### Phase 4: Update Documentation
**Changes:**
- Update README, notebooks/README

**Tests to run:**
- Visual inspection only (no code changes)

---

## Full Test Run (After All Phases)

**Optional but recommended:** Run a minimal end-to-end test

```bash
# Create a tiny test experiment (1 scenario, 1 constitution, 1 model)
# This would take ~2 minutes and verify everything works end-to-end

python src/runner.py --scenarios barking-dog --constitutions balanced-justice --models gpt-4o --experiment-id test_reorganization
```

**Success criteria:**
- Experiment runs without errors
- Results saved to `results/experiments/test_reorganization/`
- Can run analysis: `python analysis/analyze.py --experiment test_reorganization`

---

## Safety Measures

### Before Starting
1. **Commit current state:**
```bash
git add -A
git commit -m "Pre-reorganization checkpoint"
git tag pre-reorganization
```

2. **Create backup of results directory:**
```bash
tar -czf results_backup_$(date +%Y%m%d_%H%M%S).tar.gz results/
```

### During Migration
- Run MVTs after EACH phase
- If any MVT fails, STOP and investigate
- Don't proceed to next phase until all MVTs pass

### Rollback Strategy
- Phase 1 fails → `git checkout .`
- Phase 2 fails → `tar -xzf results_backup_*.tar.gz`
- Phase 3 fails → `git checkout <specific-files>`
- Phase 4 fails → No rollback needed (docs only)

---

## Test Execution Plan

```bash
# 1. Setup safety measures
git add -A && git commit -m "Pre-reorganization checkpoint"
git tag pre-reorganization
tar -czf results_backup_$(date +%Y%m%d_%H%M%S).tar.gz results/

# 2. Phase 1 + Test
# ... (reorganize source code)
# Run MVT-1
# If fail: git checkout .

# 3. Phase 2 + Test
# ... (reorganize results)
# Run MVT-3
# Verify counts
# If fail: tar -xzf results_backup_*.tar.gz

# 4. Phase 3 + Test
# ... (update code paths)
# Run ALL MVTs (1-5)
# If fail: git checkout <files>

# 5. Phase 4 + Test
# ... (update docs)
# Visual inspection
```

---

## Expected Timeline

- Safety measures: 2 min
- Phase 1 + Test: 15 min
- Phase 2 + Test: 10 min
- Phase 3 + Test: 30 min
- Phase 4 + Test: 5 min
- **Total: ~1 hour** (with testing)

---

## Success Criteria

✅ All MVTs pass
✅ No import errors
✅ Results directory structure correct
✅ File counts match (480 tests, 8 visualizations)
✅ Notebooks can load data
✅ Analysis scripts can find experiments

## Abort Criteria

❌ Any MVT fails
❌ Import errors
❌ Missing data files
❌ Incorrect file counts

**If abort:** Roll back to `pre-reorganization` tag and investigate issue.
