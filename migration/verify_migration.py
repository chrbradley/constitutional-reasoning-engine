#!/usr/bin/env python3
"""
Verification script for Phase 0.2 migration.

Optional standalone verification that can be run after migration to
independently verify data integrity.

Usage:
    poetry run python migration/verify_migration.py --experiment exp_20251026_193228
"""

import argparse
import json
import hashlib
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def compute_content_hash(content: Any) -> str:
    """Compute SHA256 hash of content"""
    if isinstance(content, dict):
        canonical = json.dumps(content, sort_keys=True)
    else:
        canonical = str(content)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load JSON file"""
    with open(file_path, "r") as f:
        return json.load(f)


def verify_experiment(
    experiment_id: str, new_dir: Path, backup_dir: Path
) -> Dict[str, Any]:
    """
    Verify migrated experiment data against backup.

    Args:
        experiment_id: Experiment ID
        new_dir: New format directory
        backup_dir: Backup directory (old format)

    Returns:
        Verification report dict
    """
    print(f"\n{'=' * 70}")
    print(f"VERIFICATION: {experiment_id}")
    print(f"{'=' * 70}")
    print(f"New format: {new_dir}")
    print(f"Backup: {backup_dir}")
    print()

    report = {
        "experiment_id": experiment_id,
        "new_format_dir": str(new_dir),
        "backup_dir": str(backup_dir),
        "checks": {
            "registry_exists": False,
            "trial_count_match": False,
            "all_layer2_hashes_match": True,
            "all_layer3_scores_match": True,
        },
        "trial_count_new": 0,
        "trial_count_old": 0,
        "mismatches": [],
        "status": "in_progress",
    }

    try:
        # Check 1: Registry exists
        print("Check 1: Registry exists...")
        registry_path = new_dir / "state" / "trial_registry.json"
        if not registry_path.exists():
            print("  ✗ Registry not found")
            report["status"] = "failed"
            return report

        registry = load_json_file(registry_path)
        report["checks"]["registry_exists"] = True
        report["trial_count_new"] = len(registry["trials"])
        print(f"  ✓ Registry found: {report['trial_count_new']} trials")

        # Check 2: Trial count matches
        print("\nCheck 2: Trial count matches...")
        old_layer2_dir = backup_dir / "data" / "layer2"
        if not old_layer2_dir.exists():
            print(f"  ✗ Old Layer 2 directory not found: {old_layer2_dir}")
            report["status"] = "failed"
            return report

        # Check for parsed/ subdirectory
        old_layer2_parsed = old_layer2_dir / "parsed"
        if old_layer2_parsed.exists():
            old_files = list(old_layer2_parsed.glob("*.json"))
        else:
            old_files = list(old_layer2_dir.glob("*.json"))
        report["trial_count_old"] = len(old_files)
        print(f"  Old format: {report['trial_count_old']} trials")
        print(f"  New format: {report['trial_count_new']} trials")

        if report["trial_count_new"] == report["trial_count_old"]:
            report["checks"]["trial_count_match"] = True
            print(f"  ✓ Trial counts match")
        else:
            print(f"  ✗ Trial counts do NOT match")
            report["status"] = "failed"
            return report

        # Check 3: Layer 2 response_raw hashes match
        print("\nCheck 3: Layer 2 response hashes...")
        layer2_mismatches = []

        # Determine if using parsed/ subdirectory
        use_parsed = old_layer2_parsed.exists()
        search_dir_layer2 = old_layer2_parsed if use_parsed else old_layer2_dir

        for trial_id, trial_meta in registry["trials"].items():
            # Find corresponding old file
            scenario = trial_meta["scenario_id"]
            constitution = trial_meta["constitution"]
            model = trial_meta["model"]
            old_filename = f"{scenario}_{constitution}_{model}.json"
            old_file = search_dir_layer2 / old_filename

            if not old_file.exists():
                layer2_mismatches.append(
                    f"{trial_id}: Old file not found: {old_filename}"
                )
                continue

            # Load both files
            old_data = load_json_file(old_file)
            new_file = new_dir / "data" / "layer2" / f"{trial_id}.json"
            new_data = load_json_file(new_file)

            # Compare response_raw hashes
            old_hash = compute_content_hash(old_data.get("response_raw", ""))
            new_hash = compute_content_hash(new_data.get("response_raw", ""))

            if old_hash != new_hash:
                layer2_mismatches.append(
                    f"{trial_id}: Layer 2 hash mismatch ({old_hash} != {new_hash})"
                )

        if layer2_mismatches:
            report["checks"]["all_layer2_hashes_match"] = False
            report["mismatches"].extend(layer2_mismatches)
            print(f"  ✗ {len(layer2_mismatches)} mismatches found")
        else:
            print(f"  ✓ All Layer 2 response hashes match")

        # Check 4: Layer 3 scores match
        print("\nCheck 4: Layer 3 scores...")
        layer3_mismatches = []
        old_layer3_dir = backup_dir / "data" / "layer3"

        # Check for parsed/ subdirectory
        old_layer3_parsed = old_layer3_dir / "parsed"
        search_dir_layer3 = old_layer3_parsed if old_layer3_parsed.exists() else old_layer3_dir

        for trial_id, trial_meta in registry["trials"].items():
            # Find corresponding old file
            scenario = trial_meta["scenario_id"]
            constitution = trial_meta["constitution"]
            model = trial_meta["model"]
            old_filename = f"{scenario}_{constitution}_{model}.json"
            old_file = search_dir_layer3 / old_filename

            if not old_file.exists():
                layer3_mismatches.append(
                    f"{trial_id}: Old Layer 3 file not found: {old_filename}"
                )
                continue

            # Load both files
            old_data = load_json_file(old_file)
            new_file = new_dir / "data" / "layer3" / f"{trial_id}.json"
            new_data = load_json_file(new_file)

            # Compare scores
            old_parsed = old_data.get("response_parsed", {})
            new_parsed = new_data.get("response_parsed", {})

            for key in ["factual_adherence", "value_transparency", "logical_coherence"]:
                if key in old_parsed and key in new_parsed:
                    if old_parsed[key] != new_parsed[key]:
                        layer3_mismatches.append(
                            f"{trial_id}: Score mismatch for {key}: {old_parsed[key]} != {new_parsed[key]}"
                        )

        if layer3_mismatches:
            report["checks"]["all_layer3_scores_match"] = False
            report["mismatches"].extend(layer3_mismatches)
            print(f"  ✗ {len(layer3_mismatches)} mismatches found")
        else:
            print(f"  ✓ All Layer 3 scores match")

        # Final status
        if (
            report["checks"]["registry_exists"]
            and report["checks"]["trial_count_match"]
            and report["checks"]["all_layer2_hashes_match"]
            and report["checks"]["all_layer3_scores_match"]
        ):
            report["status"] = "verified"
        else:
            report["status"] = "failed"

    except Exception as e:
        report["status"] = "error"
        report["error"] = str(e)
        print(f"\n✗ Verification error: {e}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Verify migrated experiment data (Phase 0.2)"
    )
    parser.add_argument(
        "--experiment",
        required=True,
        help="Experiment ID to verify (e.g., exp_20251026_193228)",
    )
    parser.add_argument(
        "--results-dir",
        default="results/experiments",
        help="Results directory (default: results/experiments)",
    )
    args = parser.parse_args()

    # Paths
    results_dir = Path(args.results_dir)
    new_dir = results_dir / args.experiment
    backup_dir = results_dir / f"{args.experiment}_BAK"

    # Validate directories exist
    if not new_dir.exists():
        print(f"ERROR: New format directory not found: {new_dir}")
        sys.exit(1)

    if not backup_dir.exists():
        print(f"ERROR: Backup directory not found: {backup_dir}")
        sys.exit(1)

    # Run verification
    report = verify_experiment(args.experiment, new_dir, backup_dir)

    # Print summary
    print(f"\n{'=' * 70}")
    print("VERIFICATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"Registry exists: {'✓' if report['checks']['registry_exists'] else '✗'}")
    print(
        f"Trial count match: {'✓' if report['checks']['trial_count_match'] else '✗'} ({report['trial_count_new']} trials)"
    )
    print(
        f"Layer 2 hashes match: {'✓' if report['checks']['all_layer2_hashes_match'] else '✗'}"
    )
    print(
        f"Layer 3 scores match: {'✓' if report['checks']['all_layer3_scores_match'] else '✗'}"
    )

    if report["mismatches"]:
        print(f"\nMismatches found: {len(report['mismatches'])}")
        for mismatch in report["mismatches"][:10]:  # Show first 10
            print(f"  - {mismatch}")
        if len(report["mismatches"]) > 10:
            print(f"  ... and {len(report['mismatches']) - 10} more")

    print(f"\nOverall status: {report['status'].upper()}")

    if report["status"] == "verified":
        print("\n✓ VERIFICATION PASSED")
        sys.exit(0)
    else:
        print("\n✗ VERIFICATION FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
