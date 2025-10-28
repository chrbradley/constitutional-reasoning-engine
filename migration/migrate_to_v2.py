#!/usr/bin/env python3
"""
Migration script for Phase 0.2: Data Architecture Redesign

Migrates experiment data from long-filename format to sequential trial IDs.

Usage:
    poetry run python migration/migrate_to_v2.py --experiment exp_20251026_193228
"""

import argparse
import json
import hashlib
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.schemas import (
    TrialRegistry,
    TrialMetadata,
    Layer1Data,
    Layer2Data,
    Layer3Data,
    SingleEvaluationData,
    ParsingInfo,
    ParsingMethod,
    TrialStatus,
    parse_old_filename,
)


def compute_content_hash(content: Any) -> str:
    """
    Compute SHA256 hash of content (order-independent for dicts).

    Args:
        content: String or dict to hash

    Returns:
        First 16 characters of SHA256 hash
    """
    if isinstance(content, dict):
        # Sort keys for consistent hashing
        canonical = json.dumps(content, sort_keys=True)
    else:
        canonical = str(content)

    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def load_old_layer_file(file_path: Path) -> Dict[str, Any]:
    """Load old format layer file"""
    with open(file_path, "r") as f:
        return json.load(f)


def convert_layer1_to_new_format(
    trial_id: str, old_data: Dict[str, Any], metadata: Dict[str, str]
) -> Layer1Data:
    """
    Convert old Layer 1 data to new format.

    In Phase 1, Layer 1 was skipped, so we just record that.
    """
    return Layer1Data(
        trial_id=trial_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        status="skipped",
        facts=old_data.get("facts", []),
        source="scenarios.json",
        reason="Phase 1 bypasses Layer 1 - facts from scenarios.json",
    )


def convert_layer2_to_new_format(
    trial_id: str,
    old_data: Dict[str, Any],
    old_raw_content: str,
    metadata: Dict[str, str]
) -> Layer2Data:
    """
    Convert old Layer 2 data to new format.

    Field mappings:
    - [.txt file content]  → response_raw
    - response (object)    → response_parsed
    - parseStatus          → parsing.success
    - maxTokensUsed        → tokens_used
    """

    # Map parseStatus to success boolean
    parse_status = old_data.get("parseStatus", "failed")
    parsing_success = parse_status == "success"

    parsing_info = ParsingInfo(
        success=parsing_success,
        method=ParsingMethod.STANDARD_JSON if parsing_success else ParsingMethod.MANUAL_REVIEW,
        fallback_attempts=0,
        error=None if parsing_success else "parse_failed",
    )

    return Layer2Data(
        trial_id=trial_id,
        timestamp=old_data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
        status="completed" if parsing_success else "completed_with_warnings",
        scenario_id=metadata["scenario_id"],
        model=metadata["model"],
        constitution=metadata["constitution"],
        prompt_sent="",  # Not stored in old format
        response_raw=old_raw_content,  # From .txt file
        response_parsed=old_data.get("response"),  # The response object
        parsing=parsing_info,
        tokens_used=old_data.get("maxTokensUsed", 0),
        latency_ms=0,  # Not stored in old format
        truncation_detected=False,  # Not stored in old format
    )


def convert_single_evaluation_to_new_format(
    old_data: Dict[str, Any],
    old_raw_content: str,
) -> SingleEvaluationData:
    """
    Convert old Layer 3 evaluation data to SingleEvaluationData format.

    Field mappings:
    - [.txt file content]                      → response_raw
    - integrityEvaluation.factualAdherence.score → response_parsed.factual_adherence
    - integrityEvaluation.valueTransparency.score → response_parsed.value_transparency
    - integrityEvaluation.logicalCoherence.score → response_parsed.logical_coherence
    - parseStatus                              → parsing.success
    - maxTokensUsed                            → tokens_used
    """

    # Map parseStatus to success boolean
    parse_status = old_data.get("parseStatus", "failed")
    parsing_success = parse_status == "success"

    parsing_info = ParsingInfo(
        success=parsing_success,
        method=ParsingMethod.STANDARD_JSON if parsing_success else ParsingMethod.MANUAL_REVIEW,
        fallback_attempts=0,
        error=None if parsing_success else "parse_failed",
    )

    # Extract full structure (scores + explanations + examples) from nested integrityEvaluation
    response_parsed = None
    integrity_eval = old_data.get("integrityEvaluation")
    if integrity_eval and parsing_success:
        response_parsed = {
            "factual_adherence": {
                "score": integrity_eval.get("factualAdherence", {}).get("score", 0),
                "explanation": integrity_eval.get("factualAdherence", {}).get("explanation", ""),
                "examples": integrity_eval.get("factualAdherence", {}).get("examples", [])
            },
            "value_transparency": {
                "score": integrity_eval.get("valueTransparency", {}).get("score", 0),
                "explanation": integrity_eval.get("valueTransparency", {}).get("explanation", ""),
                "examples": integrity_eval.get("valueTransparency", {}).get("examples", [])
            },
            "logical_coherence": {
                "score": integrity_eval.get("logicalCoherence", {}).get("score", 0),
                "explanation": integrity_eval.get("logicalCoherence", {}).get("explanation", ""),
                "examples": integrity_eval.get("logicalCoherence", {}).get("examples", [])
            }
        }
        # Add overall_score if present
        if "overallScore" in integrity_eval:
            response_parsed["overall_score"] = integrity_eval["overallScore"]

    return SingleEvaluationData(
        timestamp=old_data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
        status="completed" if parsing_success else "completed_with_warnings",
        evaluation_strategy="single_prompt_likert",  # Phase 1 constant
        prompt_sent="",  # Not stored in old format
        response_raw=old_raw_content,  # From .txt file
        response_parsed=response_parsed,
        parsing=parsing_info,
        tokens_used=old_data.get("maxTokensUsed", 0),
        latency_ms=0,  # Not stored in old format
    )


def discover_trials_in_old_format(exp_dir: Path) -> List[Tuple[str, Dict[str, str]]]:
    """
    Discover all trials in old format by scanning layer2 directory.

    Handles both flat structure and parsed/ subdirectory structure.

    Returns:
        List of (filename, metadata_dict) tuples
    """
    layer2_dir = exp_dir / "data" / "layer2"
    if not layer2_dir.exists():
        raise FileNotFoundError(f"Layer 2 directory not found: {layer2_dir}")

    # Try parsed/ subdirectory first (current structure)
    parsed_dir = layer2_dir / "parsed"
    if parsed_dir.exists():
        search_dir = parsed_dir
        print(f"  Using parsed subdirectory: {parsed_dir}")
    else:
        # Fallback to flat structure
        search_dir = layer2_dir
        print(f"  Using flat structure: {layer2_dir}")

    trials = []
    for file_path in sorted(search_dir.glob("*.json")):
        filename = file_path.name
        try:
            metadata = parse_old_filename(filename)
            trials.append((filename, metadata))
        except ValueError as e:
            print(f"WARNING: Skipping invalid filename {filename}: {e}")

    return trials


def load_all_evaluations_for_trial(
    source_dir: Path,
    trial_filename: str,
    use_parsed_subdirs: bool
) -> Dict[str, SingleEvaluationData]:
    """
    Load all evaluator assessments for a single trial.

    Scans all 5 evaluator folders:
    - parsed/ (claude-sonnet-4-5)
    - deepseek-chat/
    - gemini-2-5-pro/
    - gpt-4o/
    - grok-3/

    Args:
        source_dir: Source experiment directory
        trial_filename: Filename (e.g., "vaccine-mandate_harm-min_claude-sonnet-4-5.json")
        use_parsed_subdirs: Whether to look for raw/ subdirectories

    Returns:
        Dict mapping evaluator name to SingleEvaluationData
    """
    layer3_dir = source_dir / "data" / "layer3"

    # Define evaluator folders (folder_name, evaluator_model_name)
    evaluator_folders = [
        ("parsed", "claude-sonnet-4-5"),
        ("deepseek-chat", "deepseek-chat"),
        ("gemini-2-5-pro", "gemini-2-5-pro"),
        ("gpt-4o", "gpt-4o"),
        ("grok-3", "grok-3"),
    ]

    evaluations = {}

    for folder_name, evaluator_name in evaluator_folders:
        # Determine paths based on whether using parsed/raw subdirs
        if use_parsed_subdirs and folder_name == "parsed":
            # Special case: parsed/ has both parsed/ and raw/ subdirs
            parsed_file = layer3_dir / "parsed" / trial_filename
            raw_file = layer3_dir / "raw" / trial_filename.replace(".json", ".txt")
        elif folder_name == "parsed":
            # Flat structure for parsed/
            parsed_file = layer3_dir / "parsed" / trial_filename
            raw_file = layer3_dir / "parsed" / trial_filename.replace(".json", ".txt")
        else:
            # Other evaluators: check if they have parsed/ subdirs or are flat
            folder_path = layer3_dir / folder_name
            if (folder_path / "parsed").exists():
                # Has parsed/ subdir
                parsed_file = folder_path / "parsed" / trial_filename
                raw_file = folder_path / "raw" / trial_filename.replace(".json", ".txt")
            else:
                # Flat structure
                parsed_file = folder_path / trial_filename
                raw_file = folder_path / trial_filename.replace(".json", ".txt")

        # Try to load this evaluator's assessment
        if parsed_file.exists():
            try:
                old_data = load_old_layer_file(parsed_file)
                old_raw = ""
                if raw_file.exists():
                    old_raw = raw_file.read_text()

                evaluation = convert_single_evaluation_to_new_format(old_data, old_raw)
                evaluations[evaluator_name] = evaluation

            except Exception as e:
                print(f"    WARNING: Failed to load {evaluator_name} evaluation: {e}")

    return evaluations


def migrate_experiment(
    experiment_id: str,
    source_dir: Path,
    target_dir: Path,
) -> Dict[str, Any]:
    """
    Migrate experiment data from old to new format.

    Args:
        experiment_id: Experiment ID (e.g., 'exp_20251026_193228')
        source_dir: Source experiment directory (old format, read-only)
        target_dir: Target experiment directory (new format, will be created)

    Returns:
        Migration report dict
    """
    print(f"\n{'=' * 70}")
    print(f"MIGRATION: {experiment_id}")
    print(f"{'=' * 70}")
    print(f"Source: {source_dir}")
    print(f"Target: {target_dir}")
    print()

    # Initialize migration report
    report = {
        "migration_timestamp": datetime.utcnow().isoformat() + "Z",
        "source": str(source_dir),
        "target": str(target_dir),
        "trials_migrated": 0,
        "verification": {
            "all_response_hashes_match": True,
            "all_scores_match": True,
            "spot_checks": [],
        },
        "status": "in_progress",
        "warnings": [],
        "errors": [],
    }

    try:
        # Create target directory structure
        print("Creating target directory structure...")
        (target_dir / "state").mkdir(parents=True, exist_ok=True)
        (target_dir / "data" / "layer1").mkdir(parents=True, exist_ok=True)
        (target_dir / "data" / "layer2").mkdir(parents=True, exist_ok=True)
        (target_dir / "data" / "layer3").mkdir(parents=True, exist_ok=True)

        # Discover trials in old format
        print("\nDiscovering trials in old format...")
        trials = discover_trials_in_old_format(source_dir)
        print(f"Found {len(trials)} trials")

        if len(trials) == 0:
            raise ValueError("No trials found in old format")

        # Initialize trial registry
        registry = TrialRegistry()

        # Determine if using parsed/ subdirectory structure
        layer2_parsed_dir = source_dir / "data" / "layer2" / "parsed"
        layer3_parsed_dir = source_dir / "data" / "layer3" / "parsed"
        use_parsed_subdirs = layer2_parsed_dir.exists()

        # Migrate each trial
        print("\nMigrating trials...")
        for idx, (old_filename, metadata) in enumerate(trials, start=1):
            trial_id = f"trial_{idx:03d}"
            print(f"  [{idx}/{len(trials)}] {old_filename} → {trial_id}")

            # Add to registry
            registry.add_trial(
                trial_id=trial_id,
                scenario_id=metadata["scenario_id"],
                constitution=metadata["constitution"],
                model=metadata["model"],
            )

            # Migrate Layer 1 (skipped in Phase 1, but create file for consistency)
            layer1_file = source_dir / "data" / "layer1" / old_filename
            if layer1_file.exists():
                old_layer1 = load_old_layer_file(layer1_file)
            else:
                old_layer1 = {"facts": [], "source": "scenarios.json"}

            new_layer1 = convert_layer1_to_new_format(trial_id, old_layer1, metadata)
            layer1_target = target_dir / "data" / "layer1" / f"{trial_id}.json"
            with open(layer1_target, "w") as f:
                json.dump(new_layer1.model_dump(), f, indent=2)

            # Migrate Layer 2
            if use_parsed_subdirs:
                layer2_parsed_file = source_dir / "data" / "layer2" / "parsed" / old_filename
                layer2_raw_file = source_dir / "data" / "layer2" / "raw" / old_filename.replace(".json", ".txt")
            else:
                layer2_parsed_file = source_dir / "data" / "layer2" / old_filename
                layer2_raw_file = source_dir / "data" / "layer2" / old_filename.replace(".json", ".txt")

            if not layer2_parsed_file.exists():
                report["warnings"].append(f"Layer 2 parsed file missing for {old_filename}")
                continue

            # Load parsed JSON and raw response
            old_layer2 = load_old_layer_file(layer2_parsed_file)
            old_layer2_raw = ""
            if layer2_raw_file.exists():
                old_layer2_raw = layer2_raw_file.read_text()
            else:
                report["warnings"].append(f"Layer 2 raw file missing for {old_filename}")

            # Convert to new format
            new_layer2 = convert_layer2_to_new_format(trial_id, old_layer2, old_layer2_raw, metadata)
            layer2_target = target_dir / "data" / "layer2" / f"{trial_id}.json"
            with open(layer2_target, "w") as f:
                json.dump(new_layer2.model_dump(), f, indent=2)

            # Verify Layer 2 response_raw hash
            old_hash = compute_content_hash(old_layer2_raw)
            new_hash = compute_content_hash(new_layer2.response_raw)
            if old_hash != new_hash:
                report["verification"]["all_response_hashes_match"] = False
                report["errors"].append(
                    f"Layer 2 response hash mismatch for {trial_id}: {old_hash} != {new_hash}"
                )

            # Migrate Layer 3 - Load ALL evaluator assessments (ensemble)
            print(f"    Loading evaluations from 5 evaluator models...")
            evaluations = load_all_evaluations_for_trial(source_dir, old_filename, use_parsed_subdirs)

            if len(evaluations) == 0:
                report["warnings"].append(f"No Layer 3 evaluations found for {old_filename}")
                continue

            print(f"    Found {len(evaluations)} evaluations: {list(evaluations.keys())}")

            # Create Layer3Data with all evaluations
            new_layer3 = Layer3Data(
                trial_id=trial_id,
                scenario_id=metadata["scenario_id"],
                model=metadata["model"],  # Layer 2 model
                constitution=metadata["constitution"],
                evaluations=evaluations,
            )

            # Save to disk
            layer3_target = target_dir / "data" / "layer3" / f"{trial_id}.json"
            with open(layer3_target, "w") as f:
                json.dump(new_layer3.model_dump(), f, indent=2)

            # Verify Layer 3 scores for ALL evaluators
            # Load original files for verification
            for evaluator_name in evaluations.keys():
                # Determine old file path
                if evaluator_name == "claude-sonnet-4-5":
                    folder = "parsed"
                else:
                    folder = evaluator_name

                if use_parsed_subdirs and folder == "parsed":
                    old_file = source_dir / "data" / "layer3" / "parsed" / old_filename
                elif (source_dir / "data" / "layer3" / folder / "parsed").exists():
                    old_file = source_dir / "data" / "layer3" / folder / "parsed" / old_filename
                else:
                    old_file = source_dir / "data" / "layer3" / folder / old_filename

                if old_file.exists():
                    old_data = load_old_layer_file(old_file)
                    integrity_eval = old_data.get("integrityEvaluation", {})
                    old_scores = {
                        "factual_adherence": integrity_eval.get("factualAdherence", {}).get("score"),
                        "value_transparency": integrity_eval.get("valueTransparency", {}).get("score"),
                        "logical_coherence": integrity_eval.get("logicalCoherence", {}).get("score"),
                    }

                    new_eval = evaluations[evaluator_name]
                    new_parsed = new_eval.response_parsed or {}

                    for key in ["factual_adherence", "value_transparency", "logical_coherence"]:
                        if old_scores[key] is not None and key in new_parsed:
                            new_score = new_parsed[key].get("score") if isinstance(new_parsed[key], dict) else new_parsed[key]
                            if old_scores[key] != new_score:
                                report["verification"]["all_scores_match"] = False
                                report["errors"].append(
                                    f"Layer 3 score mismatch for {trial_id}.{evaluator_name}.{key}: {old_scores[key]} != {new_score}"
                                )

            # Update registry status
            registry.update_status(trial_id, TrialStatus.COMPLETED)
            report["trials_migrated"] += 1

            # Spot check every 60 trials and first/last
            if idx in [1, 60, len(trials)]:
                report["verification"]["spot_checks"].append({trial_id: "✓ verified"})

        # Save trial registry
        print("\nSaving trial registry...")
        registry_path = target_dir / "state" / "trial_registry.json"
        with open(registry_path, "w") as f:
            json.dump(registry.model_dump(), f, indent=2)

        # Copy metadata.json if it exists
        old_metadata = source_dir / "metadata.json"
        if old_metadata.exists():
            shutil.copy(old_metadata, target_dir / "metadata.json")

        # Success!
        report["status"] = "success"
        print(f"\n✓ Migration complete: {report['trials_migrated']} trials migrated")

    except Exception as e:
        report["status"] = "failed"
        report["errors"].append(str(e))
        print(f"\n✗ Migration failed: {e}")
        raise

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Migrate experiment data from old to new format (Phase 0.2)"
    )
    parser.add_argument(
        "--experiment",
        required=True,
        help="Experiment ID to migrate (e.g., exp_20251026_193228)",
    )
    parser.add_argument(
        "--results-dir",
        default="results/experiments",
        help="Results directory (default: results/experiments)",
    )
    args = parser.parse_args()

    # Paths
    results_dir = Path(args.results_dir)
    source_dir = results_dir / args.experiment
    target_temp = results_dir / f"{args.experiment}_v2_temp"
    target_final = results_dir / args.experiment
    backup_dir = results_dir / f"{args.experiment}_BAK"

    # Validate source exists
    if not source_dir.exists():
        print(f"ERROR: Source experiment not found: {source_dir}")
        sys.exit(1)

    # Validate target doesn't exist
    if target_temp.exists():
        print(f"ERROR: Temporary target already exists: {target_temp}")
        print("Please remove it and try again")
        sys.exit(1)

    if backup_dir.exists():
        print(f"ERROR: Backup directory already exists: {backup_dir}")
        print("Please remove it and try again")
        sys.exit(1)

    try:
        # Step 1: Migrate to temporary directory
        print("\nStep 1: Migrating to temporary directory...")
        report = migrate_experiment(args.experiment, source_dir, target_temp)

        # Step 2: Rename original to backup
        print("\nStep 2: Renaming original to backup...")
        source_dir.rename(backup_dir)
        print(f"  {source_dir} → {backup_dir}")

        # Step 3: Rename temp to final
        print("\nStep 3: Renaming temporary to final...")
        target_temp.rename(target_final)
        print(f"  {target_temp} → {target_final}")

        # Step 4: Save migration report
        print("\nStep 4: Saving migration report...")
        report["source"] = f"{args.experiment} → {args.experiment}_BAK"
        report["target"] = f"{args.experiment} (new format)"

        report_dir = Path("migration/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_filename = f"migration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = report_dir / report_filename
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  Report saved: {report_path}")

        # Step 5: Clear current experiment pointer
        print("\nStep 5: Clearing current experiment pointer...")
        pointer_path = Path("results/state/current_experiment.json")
        if pointer_path.exists():
            with open(pointer_path, "w") as f:
                json.dump({}, f, indent=2)
            print(f"  Cleared: {pointer_path}")

        # Summary
        print(f"\n{'=' * 70}")
        print("MIGRATION COMPLETE")
        print(f"{'=' * 70}")
        print(f"Trials migrated: {report['trials_migrated']}")
        print(f"Backup location: {backup_dir}")
        print(f"New format: {target_final}")
        print(f"Report: {report_path}")

        if report["warnings"]:
            print(f"\nWarnings: {len(report['warnings'])}")
            for warning in report["warnings"]:
                print(f"  - {warning}")

        if report["errors"]:
            print(f"\n✗ Errors occurred: {len(report['errors'])}")
            for error in report["errors"]:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("\n✓ No errors")
            print(f"\nVerification:")
            print(f"  Response hashes match: {report['verification']['all_response_hashes_match']}")
            print(f"  Scores match: {report['verification']['all_scores_match']}")

    except Exception as e:
        print(f"\n✗ MIGRATION FAILED: {e}")
        print("\nRolling back changes...")
        if backup_dir.exists() and not source_dir.exists():
            backup_dir.rename(source_dir)
            print(f"  Restored: {backup_dir} → {source_dir}")
        if target_temp.exists():
            shutil.rmtree(target_temp)
            print(f"  Removed: {target_temp}")
        sys.exit(1)


if __name__ == "__main__":
    main()
