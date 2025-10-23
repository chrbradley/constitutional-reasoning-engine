"""
Test script to validate state management fixes
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from experiment_state import ExperimentManager
from data_types import Scenario, Constitution

# Create test data
scenarios = [Scenario(
    id="test-scenario",
    title="Test",
    description="Test scenario",
    category="personal",
    established_facts=["fact1"],
    ambiguous_elements=["ambig1"],
    decision_point="What to do?"
)]
constitutions = [Constitution(id="test-const", name="Test", description="Test", system_prompt="Test", core_values=["value1"])]
models = [
    {"id": "model-1", "provider": "test"},
    {"id": "model-2", "provider": "test"},
    {"id": "model-3", "provider": "test"}
]

# Initialize fresh experiment
manager = ExperimentManager(base_dir="results_test")
exp_id = manager.create_experiment(scenarios, constitutions, models)

print(f"\n{'='*60}")
print(f"Testing State Management - Experiment: {exp_id}")
print(f"{'='*60}\n")

# Initial state
print("Initial state:")
progress = manager.get_progress_summary()
print(f"  Total: {progress['progress']['total']}")
print(f"  Completed: {progress['progress']['completed']}")
print(f"  Failed: {progress['progress']['failed']}")
print(f"  Pending: {progress['progress']['pending']}")
assert progress['progress']['total'] == 3, "Should have 3 total tests"
assert progress['progress']['pending'] == 3, "Should have 3 pending"
assert progress['progress']['completed'] == 0, "Should have 0 completed"
assert progress['progress']['failed'] == 0, "Should have 0 failed"
print("  ✓ Initial state correct\n")

# Test 1: Successful completion (PENDING → IN_PROGRESS → COMPLETED)
print("Test 1: Successful completion (PENDING → IN_PROGRESS → COMPLETED)")
test_id_1 = "test-scenario_test-const_model-1"
manager.mark_test_in_progress(test_id_1)
progress = manager.get_progress_summary()
print(f"  After IN_PROGRESS: pending={progress['progress']['pending']}")
assert progress['progress']['pending'] == 2, f"Should have 2 pending after marking one in progress, got {progress['progress']['pending']}"

manager.mark_test_completed(test_id_1, {"test": "data"})
progress = manager.get_progress_summary()
print(f"  After COMPLETED: completed={progress['progress']['completed']}, pending={progress['progress']['pending']}")
assert progress['progress']['completed'] == 1, "Should have 1 completed"
assert progress['progress']['pending'] == 2, "Should still have 2 pending"
print("  ✓ Test 1 passed\n")

# Test 2: Failure then retry success (PENDING → IN_PROGRESS → FAILED → IN_PROGRESS → COMPLETED)
print("Test 2: Failure then retry (PENDING → IN_PROGRESS → FAILED → IN_PROGRESS → COMPLETED)")
test_id_2 = "test-scenario_test-const_model-2"
manager.mark_test_in_progress(test_id_2)
progress = manager.get_progress_summary()
print(f"  After IN_PROGRESS: pending={progress['progress']['pending']}")
assert progress['progress']['pending'] == 1, f"Should have 1 pending, got {progress['progress']['pending']}"

manager.mark_test_failed(test_id_2, "Test failure")
progress = manager.get_progress_summary()
print(f"  After FAILED: failed={progress['progress']['failed']}, pending={progress['progress']['pending']}")
assert progress['progress']['failed'] == 1, "Should have 1 failed"
assert progress['progress']['pending'] == 1, "Should still have 1 pending"

# Retry
manager.mark_test_in_progress(test_id_2)
progress = manager.get_progress_summary()
print(f"  After retry IN_PROGRESS: failed={progress['progress']['failed']}, pending={progress['progress']['pending']}")
assert progress['progress']['pending'] == 1, "Pending should not change on retry"

manager.mark_test_completed(test_id_2, {"test": "retry data"})
progress = manager.get_progress_summary()
print(f"  After COMPLETED: completed={progress['progress']['completed']}, failed={progress['progress']['failed']}, pending={progress['progress']['pending']}")
assert progress['progress']['completed'] == 2, "Should have 2 completed"
assert progress['progress']['failed'] == 0, "Failed count should decrement to 0"
assert progress['progress']['pending'] == 1, "Should have 1 pending left"
print("  ✓ Test 2 passed\n")

# Test 3: Final test completes successfully
print("Test 3: Final test (PENDING → IN_PROGRESS → COMPLETED)")
test_id_3 = "test-scenario_test-const_model-3"
manager.mark_test_in_progress(test_id_3)
manager.mark_test_completed(test_id_3, {"test": "final data"})
progress = manager.get_progress_summary()
print(f"  Final state: completed={progress['progress']['completed']}, failed={progress['progress']['failed']}, pending={progress['progress']['pending']}")
assert progress['progress']['completed'] == 3, "Should have 3 completed"
assert progress['progress']['failed'] == 0, "Should have 0 failed"
assert progress['progress']['pending'] == 0, "Should have 0 pending"
print("  ✓ Test 3 passed\n")

print(f"{'='*60}")
print("✅ ALL STATE MANAGEMENT TESTS PASSED!")
print(f"{'='*60}\n")

# Cleanup
import shutil
shutil.rmtree("results_test")
