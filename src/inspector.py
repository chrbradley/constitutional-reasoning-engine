"""
Experiment Inspector - View and manage experiment state
"""
import sys
import json
from pathlib import Path

from src.core.experiment_state import ExperimentManager


def print_progress_bar(completed: int, total: int, width: int = 50) -> str:
    """Create a text progress bar"""
    if total == 0:
        return "No trials"
    
    progress = completed / total
    filled = int(width * progress)
    bar = "█" * filled + "░" * (width - filled)
    percentage = progress * 100
    return f"[{bar}] {percentage:.1f}% ({completed}/{total})"


def main():
    print("Constitutional Reasoning Engine - Experiment Inspector")
    print("=" * 60)
    
    # Initialize experiment manager
    experiment_manager = ExperimentManager()
    
    # Get progress summary
    progress = experiment_manager.get_progress_summary()
    
    if progress.get("status") == "No active experiment":
        print("❌ No active experiment found.")
        print("\nTo start an experiment:")
        print("  python robust_experiment_runner.py")
        return
    
    # Display experiment info
    print(f"Experiment ID: {progress['experiment_id']}")
    print(f"Status: {progress['status']}")
    print(f"Created: {progress['created_at']}")
    print(f"Updated: {progress['updated_at']}")
    print()
    
    # Display progress
    prog_data = progress['progress']
    print("PROGRESS:")
    print(f"  Overall: {print_progress_bar(prog_data['completed'], prog_data['total'])}")
    print(f"  Completed: {prog_data['completed']:4d}")
    print(f"  Failed:    {prog_data['failed']:4d}")
    print(f"  Pending:   {prog_data['pending']:4d}")
    print(f"  Total:     {prog_data['total']:4d}")
    print()
    
    # Show pending trials
    pending_trials = experiment_manager.get_pending_trials()
    if pending_trials:
        print(f"NEXT {min(10, len(pending_trials))} PENDING TRIALS:")
        for i, trial in enumerate(pending_trials[:10]):
            print(f"  {i+1:2d}. {trial.trial_id}")
        if len(pending_trials) > 10:
            print(f"     ... and {len(pending_trials) - 10} more")
        print()
    
    # Show failed trials that can be retried
    failed_trials = experiment_manager.get_failed_trials(max_retries=3)
    if failed_trials:
        print(f"RETRYABLE FAILED TRIALS ({len(failed_trials)}):")
        for i, trial in enumerate(failed_trials[:5]):
            retry_count = experiment_manager.trial_registry[trial.trial_id].retry_count
            error = experiment_manager.trial_registry[trial.trial_id].error_message
            print(f"  {i+1}. {trial.trial_id} (retry {retry_count})")
            print(f"     Error: {error[:60]}...")
        if len(failed_trials) > 5:
            print(f"     ... and {len(failed_trials) - 5} more")
        print()
    
    # Show completed trials breakdown
    if prog_data['completed'] > 0:
        print("RECENT COMPLETED TRIALS:")
        completed_trials = [
            (trial_id, result) for trial_id, result in experiment_manager.trial_registry.items()
            if result.status.value == "completed"
        ]
        
        # Sort by timestamp, show last 5
        completed_trials.sort(key=lambda x: x[1].timestamp, reverse=True)
        
        for trial_id, result in completed_trials[:5]:
            score = "N/A"
            if result.result_data and 'integrityEvaluation' in result.result_data:
                score = f"{result.result_data['integrityEvaluation'].get('overallScore', 'N/A')}/100"
            print(f"  ✅ {trial_id} - Score: {score}")
        
        if len(completed_trials) > 5:
            print(f"     ... and {len(completed_trials) - 5} more")
        print()
    
    # Show summary by model and constitution
    if prog_data['completed'] > 0:
        print("COMPLETION BY MODEL:")
        model_stats = {}
        constitution_stats = {}
        
        for trial_id, result in experiment_manager.trial_registry.items():
            # Model stats
            model_id = result.model_id
            if model_id not in model_stats:
                model_stats[model_id] = {"completed": 0, "total": 0}
            model_stats[model_id]["total"] += 1
            if result.status.value == "completed":
                model_stats[model_id]["completed"] += 1
            
            # Constitution stats
            const_id = result.constitution_id
            if const_id not in constitution_stats:
                constitution_stats[const_id] = {"completed": 0, "total": 0}
            constitution_stats[const_id]["total"] += 1
            if result.status.value == "completed":
                constitution_stats[const_id]["completed"] += 1
        
        for model_id, stats in model_stats.items():
            progress_bar = print_progress_bar(stats["completed"], stats["total"], 30)
            print(f"  {model_id:<20} {progress_bar}")
        
        print("\nCOMPLETION BY CONSTITUTION:")
        for const_id, stats in constitution_stats.items():
            progress_bar = print_progress_bar(stats["completed"], stats["total"], 30)
            print(f"  {const_id:<20} {progress_bar}")
    
    print("\nCOMMANDS:")
    print("  python robust_experiment_runner.py  - Resume experiment")
    print("  python experiment_inspector.py      - View this status")


if __name__ == "__main__":
    main()