"""
Test script to validate batching logic fixes
"""
import sys
sys.path.insert(0, 'src')

from experiment_state import TestDefinition

# Import the batching function
import importlib.util
spec = importlib.util.spec_from_file_location("runner", "../robust_experiment_runner.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

# Create test data: 3 scenarios × 2 constitutions × 6 models = 36 tests
test_data = []
scenarios = ["scenario-1", "scenario-2", "scenario-3"]
constitutions = ["const-a", "const-b"]
models = ["model-1", "model-2", "model-3", "model-4", "model-5", "model-6"]

for scenario in scenarios:
    for constitution in constitutions:
        for model in models:
            test_data.append(TestDefinition(scenario, constitution, model))

print(f"Created {len(test_data)} test definitions")
print(f"Models: {models}")
print()

# Test batching with batch_size=6
batches = runner.create_batches(test_data, batch_size=6)

print(f"Generated {len(batches)} batches:")
print()

# Validate batching
all_valid = True
for i, batch in enumerate(batches, 1):
    models_in_batch = [test.model_id for test in batch]
    unique_models = set(models_in_batch)

    print(f"Batch {i}: {len(batch)} tests")
    print(f"  Models: {models_in_batch}")
    print(f"  Unique: {len(unique_models)} ({', '.join(sorted(unique_models))})")

    # Check for duplicates
    if len(models_in_batch) != len(unique_models):
        print(f"  ❌ FAIL: Duplicate models in batch!")
        all_valid = False
        duplicates = [m for m in models_in_batch if models_in_batch.count(m) > 1]
        print(f"  Duplicates: {set(duplicates)}")
    else:
        print(f"  ✅ PASS: All models unique")

    print()

# Final validation
if all_valid:
    print("=" * 60)
    print("✅ ALL BATCHES VALID - Round-robin distribution working!")
    print("=" * 60)
else:
    print("=" * 60)
    print("❌ BATCHING FAILED - Fix needed!")
    print("=" * 60)
    sys.exit(1)
