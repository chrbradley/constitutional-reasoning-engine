"""
Fix experiment state - reset stuck in-progress tests and retry failed tests
"""
import json
import sys
from pathlib import Path

sys.path.append('experiments/src')
from experiment_state import ExperimentManager


def fix_experiment_state():
    """Fix stuck experiment state"""
    print("Fixing Experiment State")
    print("=" * 40)
    
    # Load current registry
    registry_file = Path("results/state/test_registry.json")
    if not registry_file.exists():
        print("❌ No test registry found")
        return
    
    with open(registry_file, 'r') as f:
        registry = json.load(f)
    
    # Find stuck in-progress tests
    stuck_tests = []
    failed_tests = []
    
    for test_id, data in registry.items():
        if data['status'] == 'in_progress':
            stuck_tests.append(test_id)
        elif data['status'] == 'failed':
            failed_tests.append(test_id)
    
    print(f"Found {len(stuck_tests)} stuck in-progress tests:")
    for test_id in stuck_tests:
        print(f"  🔄 {test_id}")
    
    print(f"\nFound {len(failed_tests)} failed tests:")
    for test_id in failed_tests:
        retry_count = registry[test_id].get('retry_count', 0)
        print(f"  ❌ {test_id} (retry {retry_count})")
    
    # Reset stuck tests to pending
    for test_id in stuck_tests:
        registry[test_id]['status'] = 'pending'
        registry[test_id]['timestamp'] = ''
        print(f"  ✅ Reset {test_id} to pending")
    
    # Reset failed tests retry count to allow retries
    for test_id in failed_tests:
        registry[test_id]['status'] = 'pending'
        registry[test_id]['retry_count'] = 0
        registry[test_id]['error_message'] = None
        registry[test_id]['timestamp'] = ''
        print(f"  ✅ Reset {test_id} for retry")
    
    # Save updated registry
    with open(registry_file, 'w') as f:
        json.dump(registry, f, indent=2)
    
    # Update experiment state counts
    state_file = Path("results/state/experiment_state.json")
    if state_file.exists():
        with open(state_file, 'r') as f:
            exp_state = json.load(f)
        
        # Recalculate counts
        completed_count = len([t for t in registry.values() if t['status'] == 'completed'])
        failed_count = 0  # Reset since we're retrying failed tests
        pending_count = len([t for t in registry.values() if t['status'] == 'pending'])
        
        exp_state['completed_count'] = completed_count
        exp_state['failed_count'] = failed_count  
        exp_state['pending_count'] = pending_count
        
        with open(state_file, 'w') as f:
            json.dump(exp_state, f, indent=2)
        
        print(f"\n✅ Updated experiment state:")
        print(f"  Completed: {completed_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Pending: {pending_count}")
    
    print(f"\n🎉 State fixed! Ready to resume experiment.")


if __name__ == "__main__":
    fix_experiment_state()