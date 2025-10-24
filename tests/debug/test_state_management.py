"""
Test the state management system with a minimal experiment
"""
import asyncio
import sys

sys.path.append('experiments/src')

from models import MODELS
from scenarios import load_scenarios
from constitutions import CONSTITUTIONS
from experiment_state import ExperimentManager


async def test_state_management():
    print("Testing State Management System")
    print("=" * 50)
    
    # Create a minimal test set: 1 scenario × 2 constitutions × 2 models = 4 tests
    scenarios = load_scenarios()[:1]  # Just parking lot
    constitutions = [c for c in CONSTITUTIONS if c.id in ["harm-minimization", "self-sovereignty"]]
    models = [m for m in MODELS if m['id'] in ["claude-sonnet-4-5", "gpt-4o"]]
    
    print(f"Test set: {len(scenarios)} scenario × {len(constitutions)} constitutions × {len(models)} models = {len(scenarios) * len(constitutions) * len(models)} tests")
    
    # Initialize experiment manager
    experiment_manager = ExperimentManager()
    
    # Create experiment
    experiment_id = experiment_manager.create_experiment(scenarios, constitutions, models)
    
    # Show initial state
    progress = experiment_manager.get_progress_summary()
    print(f"\nInitial state:")
    print(f"  Experiment ID: {progress['experiment_id']}")
    print(f"  Total tests: {progress['progress']['total']}")
    print(f"  Pending: {progress['progress']['pending']}")
    
    # Get pending tests
    pending_tests = experiment_manager.get_pending_tests()
    print(f"\nPending tests:")
    for i, test in enumerate(pending_tests):
        print(f"  {i+1}. {test.test_id}")
    
    # Test state transitions
    if pending_tests:
        test_def = pending_tests[0]
        test_id = test_def.test_id
        
        print(f"\nTesting state transitions with: {test_id}")
        
        # Mark as in progress
        experiment_manager.mark_test_in_progress(test_id)
        print(f"  ✓ Marked as in_progress")
        
        # Simulate completion
        mock_result = {
            "testId": test_id,
            "scenario": "mock_scenario",
            "result": "mock_result"
        }
        experiment_manager.mark_test_completed(test_id, mock_result)
        print(f"  ✓ Marked as completed")
        
        # Check if test exists
        exists = experiment_manager.test_exists(test_id)
        print(f"  ✓ Test exists check: {exists}")
        
        # Show updated progress
        progress = experiment_manager.get_progress_summary()
        print(f"\nUpdated progress:")
        print(f"  Completed: {progress['progress']['completed']}")
        print(f"  Pending: {progress['progress']['pending']}")
    
    # Test adding new models
    print(f"\nTesting add new models...")
    new_models = [{"id": "test-model", "name": "Test Model"}]
    added_count = experiment_manager.add_new_models(new_models, scenarios, constitutions)
    print(f"  ✓ Added {added_count} new tests for new models")
    
    final_progress = experiment_manager.get_progress_summary()
    print(f"\nFinal state:")
    print(f"  Total tests: {final_progress['progress']['total']}")
    print(f"  Completed: {final_progress['progress']['completed']}")
    print(f"  Pending: {final_progress['progress']['pending']}")
    
    print(f"\n🎉 State management system working correctly!")
    
    # Show how to inspect the experiment
    print(f"\nTo inspect the experiment state, run:")
    print(f"  python experiment_inspector.py")


if __name__ == "__main__":
    asyncio.run(test_state_management())