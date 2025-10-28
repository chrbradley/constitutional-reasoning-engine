# Data Architecture Migration (Phase 0.2)

## Purpose

One-time migration from long-filename structure to sequential trial IDs with centralized registry.

### What Changed?

**Old Structure (Long Filenames):**
```
results/experiments/exp_20251026_193228/data/
├── layer1/vaccine-mandate-religious-exemption_harm-minimization_claude-sonnet-4-5.json
├── layer2/vaccine-mandate-religious-exemption_harm-minimization_claude-sonnet-4-5.json
└── layer3/vaccine-mandate-religious-exemption_harm-minimization_claude-sonnet-4-5.json
```

**New Structure (Sequential Trial IDs):**
```
results/experiments/exp_20251026_193228/
├── state/trial_registry.json           # Maps trial IDs to metadata
└── data/
    ├── layer1/trial_001.json
    ├── layer2/trial_001.json
    └── layer3/trial_001.json
```

### Benefits

- **Simpler filenames:** `trial_001.json` instead of long descriptive names
- **Easy filtering:** Query `trial_registry.json` to find trials by scenario/constitution/model
- **Scalable:** Supports multiple evaluation strategies per trial
- **Audit trail:** All layer outputs preserved immutably

---

## Usage

### Basic Migration

```bash
poetry run python migration/migrate_to_v2.py --experiment exp_20251026_193228
```

### What It Does

1. **Reads** old experiment data (read-only, never modifies source)
2. **Creates** temporary directory with new structure
3. **Renames** original experiment to `exp_20251026_193228_BAK` (backup)
4. **Renames** temporary directory to clean experiment name
5. **Generates** migration report in `migration/reports/`
6. **Clears** current experiment pointer (`results/state/current_experiment.json` → `{}`)

### Migration Process

```
Before:
  results/experiments/exp_20251026_193228/  (119 trials, old format)
  results/state/current_experiment.json  {"experiment_id": "exp_20251026_193228"}

After:
  results/experiments/exp_20251026_193228_BAK/  (backup, untouched)
  results/experiments/exp_20251026_193228/  (119 trials, new format)
  results/state/current_experiment.json  {}
```

---

## Verification

### Automatic Verification (Built-in)

The migration script automatically:
- Computes checksums on all `response_raw` fields
- Verifies all Layer 3 scores match (factual_adherence, value_transparency, logical_coherence)
- Spot-checks 3 random trials for full data integrity
- Generates detailed report in `migration/reports/migration_YYYYMMDD_HHMMSS.json`

### Manual Verification (Optional)

```bash
poetry run python migration/verify_migration.py --experiment exp_20251026_193228
```

This separate script:
- Compares trial counts (should be 119 in both old and new)
- Re-computes checksums independently
- Performs full data comparison on all trials
- Generates verification report

---

## New Data Schema

### Trial Registry (`state/trial_registry.json`)

Maps trial IDs to metadata:

```json
{
  "trial_001": {
    "scenario_id": "vaccine-mandate-religious-exemption",
    "constitution": "harm-minimization",
    "model": "claude-sonnet-4-5",
    "created_at": "2025-10-26T19:32:28Z",
    "status": "completed"
  },
  "trial_002": {
    "scenario_id": "vaccine-mandate-religious-exemption",
    "constitution": "harm-minimization",
    "model": "gpt-4o",
    "created_at": "2025-10-26T19:32:35Z",
    "status": "completed"
  }
}
```

### Layer Files (`data/layer2/trial_001.json` example)

Each layer file is immutable and contains:

```json
{
  "trial_id": "trial_001",
  "layer": 2,
  "timestamp": "2025-10-26T19:32:30Z",
  "status": "completed",
  "model": "claude-sonnet-4-5",
  "constitution": "harm-minimization",
  "prompt_sent": "Given the following facts...",
  "response_raw": "From a harm-minimization perspective...",
  "response_parsed": {
    "reasoning": "...",
    "conclusion": "..."
  },
  "parsing": {
    "success": true,
    "method": "standard_json",
    "fallback_attempts": 0,
    "error": null
  },
  "tokens_used": 8234,
  "latency_ms": 4521,
  "truncation_detected": false
}
```

**Key guarantee:** `response_raw` is ALWAYS captured (saved immediately after API call). `response_parsed` is optional and may be null if parsing fails.

---

## Using Migrated Data

### Python Example

```python
import json

# Load registry
with open("results/experiments/exp_20251026_193228/state/trial_registry.json") as f:
    registry = json.load(f)

# Filter: Get all harm-minimization trials
harm_min_trials = [
    trial_id for trial_id, meta in registry.items()
    if meta["constitution"] == "harm-minimization"
]

# Load Layer 3 scores for those trials
scores = []
for trial_id in harm_min_trials:
    with open(f"results/experiments/exp_20251026_193228/data/layer3/{trial_id}.json") as f:
        data = json.load(f)
        scores.append(data["response_parsed"]["factual_adherence"])

# Analyze
import numpy as np
mean_score = np.mean(scores)
print(f"Mean factual adherence for harm-minimization: {mean_score:.1f}")
```

---

## Migration Report Format

After successful migration, a report is generated in `migration/reports/`:

```json
{
  "migration_timestamp": "2025-10-27T14:30:22Z",
  "source": "exp_20251026_193228 → exp_20251026_193228_BAK",
  "target": "exp_20251026_193228 (new format)",
  "trials_migrated": 119,
  "verification": {
    "all_response_hashes_match": true,
    "all_scores_match": true,
    "spot_checks": [
      {"trial_001": "✓ verified"},
      {"trial_060": "✓ verified"},
      {"trial_119": "✓ verified"}
    ]
  },
  "status": "success",
  "warnings": [],
  "errors": []
}
```

---

## After Successful Migration

### Option A: Keep Both Temporarily
- Leave `exp_20251026_193228_BAK/` as backup for a few weeks
- Ensure new format works with all analysis scripts
- Delete backup after Phase 1 analysis completes

### Option B: Archive Immediately
```bash
mkdir -p results/experiments/archived
mv results/experiments/exp_20251026_193228_BAK results/experiments/archived/
```

### Option C: Keep Reports Only
```bash
mkdir -p docs/migration_reports
cp migration/reports/* docs/migration_reports/
# Later: rm -rf migration/
```

---

## Troubleshooting

### Migration Fails Partway

The migration is atomic - if it fails, the original data is untouched. Simply re-run the migration script.

### Checksum Mismatch

If verification reports checksum mismatch:
1. Check migration report in `migration/reports/` for details
2. Run manual verification: `python migration/verify_migration.py`
3. If issues persist, keep backup and investigate before deleting

### Need to Rollback

```bash
# Delete new format
rm -rf results/experiments/exp_20251026_193228

# Restore backup
mv results/experiments/exp_20251026_193228_BAK results/experiments/exp_20251026_193228
```

---

## Files in This Directory

- **`README.md`** (this file) - Migration documentation
- **`migrate_to_v2.py`** - Main migration script
- **`verify_migration.py`** - Optional verification script
- **`reports/`** - Generated migration reports (timestamped JSON files)

---

**Status:** Phase 0.2 one-time migration
**After Migration:** This directory can be archived or deleted (keep reports for audit trail)
