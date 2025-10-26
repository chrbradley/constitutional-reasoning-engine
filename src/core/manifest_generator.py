"""
Generate human-readable test manifest for experiment runs
"""
from pathlib import Path
from typing import Dict
import json
from datetime import datetime
from src.core.experiment_state import ExperimentManager, TrialStatus


def generate_manifest(experiment_manager: ExperimentManager) -> str:
    """Generate a human-readable manifest showing all tests and their status"""

    state = experiment_manager.experiment_state
    registry = experiment_manager.trial_registry

    if not state:
        return "No active experiment"

    lines = []
    lines.append("=" * 80)
    lines.append(f"EXPERIMENT MANIFEST: {state.experiment_id}")
    lines.append("=" * 80)
    lines.append(f"Created:  {state.created_at}")
    lines.append(f"Updated:  {state.updated_at}")
    lines.append(f"Status:   {state.status}")
    lines.append("")
    lines.append(f"Progress: {state.completed_count}/{state.total_trials} completed "
                f"({state.completed_count / state.total_trials * 100:.1f}%)")
    lines.append(f"Failed:   {state.failed_count}")
    lines.append(f"Pending:  {state.pending_count}")
    lines.append("")
    lines.append("Scenarios:      " + ", ".join(state.scenarios))
    lines.append("Constitutions:  " + ", ".join(state.constitutions))
    lines.append("Models:         " + ", ".join(state.models))
    if state.command_line:
        lines.append("")
        lines.append("Command:        " + state.command_line)
    lines.append("")
    lines.append("=" * 80)
    lines.append("TEST DETAILS")
    lines.append("=" * 80)
    lines.append("")

    # Group tests by scenario, then constitution
    for scenario_id in state.scenarios:
        lines.append(f"SCENARIO: {scenario_id}")
        lines.append("-" * 80)

        for constitution_id in state.constitutions:
            lines.append(f"  {constitution_id}:")

            for model_id in state.models:
                test_id = f"{scenario_id}_{constitution_id}_{model_id}"

                if test_id in registry:
                    test_result = registry[test_id]
                    status = test_result.status

                    # Status symbol
                    if status == TrialStatus.COMPLETED:
                        symbol = "✅"
                        # Extract score if available
                        score = ""
                        if test_result.result_data and 'integrityEvaluation' in test_result.result_data:
                            overall = test_result.result_data['integrityEvaluation'].get('overallScore', 'N/A')
                            score = f" ({overall}/100)"
                    elif status == TrialStatus.FAILED:
                        symbol = "❌"
                        score = f" (retry {test_result.retry_count})"
                    elif status == TrialStatus.IN_PROGRESS:
                        symbol = "🔄"
                        score = ""
                    elif status == TrialStatus.PENDING:
                        symbol = "⏳"
                        score = ""
                    else:
                        symbol = "❓"
                        score = ""

                    # Format: symbol model_id (score) [timestamp]
                    timestamp = test_result.timestamp[:19] if test_result.timestamp else "no timestamp"
                    lines.append(f"    {symbol} {model_id:20s}{score:15s} [{timestamp}]")

                    # Add layer-by-layer status if available
                    if test_result.layer_status:
                        for layer_num in [1, 2, 3]:
                            layer_key = f"layer{layer_num}"
                            if layer_key in test_result.layer_status:
                                layer_info = test_result.layer_status[layer_key]
                                layer_status = layer_info.get('status', 'unknown')
                                layer_model = layer_info.get('model', 'N/A')
                                layer_error = layer_info.get('error', '')

                                # Choose symbol based on status
                                if layer_status == "completed":
                                    layer_symbol = "✅"
                                elif layer_status == "failed":
                                    layer_symbol = "❌"
                                elif layer_status == "skipped":
                                    layer_symbol = "⏭️ "
                                else:
                                    layer_symbol = "❓"

                                # Format layer line
                                model_display = layer_model if layer_model else "N/A"
                                if layer_error:
                                    error_preview = layer_error[:60] + "..." if len(layer_error) > 60 else layer_error
                                    lines.append(f"       L{layer_num}: {layer_symbol} {model_display:20s} - {error_preview}")
                                else:
                                    lines.append(f"       L{layer_num}: {layer_symbol} {model_display:20s}")

                    # Add error message for failed tests (fallback if no layer status)
                    elif status == TrialStatus.FAILED and test_result.error_message:
                        error_preview = test_result.error_message[:100]
                        if len(test_result.error_message) > 100:
                            error_preview += "..."
                        lines.append(f"       Error: {error_preview}")
                else:
                    # Test not in registry (shouldn't happen)
                    lines.append(f"    ❓ {model_id:20s} [NOT IN REGISTRY]")

            lines.append("")

        lines.append("")

    lines.append("=" * 80)
    lines.append("LEGEND")
    lines.append("=" * 80)
    lines.append("✅ Completed successfully")
    lines.append("❌ Failed (available for retry)")
    lines.append("🔄 Currently in progress")
    lines.append("⏳ Pending (not yet started)")
    lines.append("=" * 80)

    return "\n".join(lines)


def save_manifest(experiment_manager: ExperimentManager, output_path: Path = None) -> Path:
    """Generate and save manifest to experiment directory"""

    if output_path is None:
        # Save to experiment's directory
        exp_id = experiment_manager.experiment_id
        if exp_id:
            output_path = experiment_manager.base_dir / "experiments" / exp_id / "MANIFEST.txt"
        else:
            output_path = experiment_manager.base_dir / "MANIFEST.txt"

    manifest_content = generate_manifest(experiment_manager)

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write manifest
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(manifest_content)

    return output_path


if __name__ == "__main__":
    # Generate manifest for current experiment
    # Use project root's results directory (../../results from experiments/src/)
    import os
    project_root = Path(__file__).parent.parent.parent
    results_dir = project_root / "results"

    manager = ExperimentManager(base_dir=str(results_dir))

    if manager.experiment_state:
        manifest_path = save_manifest(manager)
        print(f"✅ Manifest saved to: {manifest_path}")
        print("\nPreview:")
        print("-" * 80)
        print(generate_manifest(manager))
    else:
        print("No active experiment found")
