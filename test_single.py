"""
Quick end-to-end test: Run one random scenario/constitution/model through the pipeline
Tests the refactored Phase 1 setup with Layer 1 bypass and layer-based output
"""
import asyncio
import random
from pathlib import Path

from src.core.scenarios import load_scenarios
from src.core.constitutions import CONSTITUTIONS
from src.core.models import MODELS
from src.runner import run_single_test
from src.core.experiment_state import ExperimentManager


async def main():
    print("=" * 70)
    print("SINGLE TEST - End-to-End Pipeline Validation")
    print("=" * 70)

    # Load data
    scenarios = load_scenarios()
    constitutions = CONSTITUTIONS
    models = MODELS

    # Randomly select one of each
    scenario = random.choice(scenarios)
    constitution = random.choice(constitutions)
    model = random.choice(models)

    print(f"\nRandomly selected test:")
    print(f"  Scenario:     {scenario.id} - {scenario.title}")
    print(f"  Constitution: {constitution.id}")
    print(f"  Model:        {model['id']}")
    print()

    # Create fresh test experiment (delete existing state first)
    from pathlib import Path
    import shutil
    state_dir = Path("results/state")
    if state_dir.exists():
        print("Clearing existing experiment state for fresh test...")
        shutil.rmtree(state_dir)

    experiment_manager = ExperimentManager()
    experiment_id = experiment_manager.create_experiment([scenario], [constitution], [model])

    print(f"Created test experiment: {experiment_id}")
    print()

    # Get the test definition
    from src.core.experiment_state import TestDefinition
    test_def = TestDefinition(
        scenario_id=scenario.id,
        constitution_id=constitution.id,
        model_id=model['id']
    )

    # Run the test
    try:
        success = await run_single_test(
            test_def=test_def,
            scenario_data=scenario,
            constitution_data=constitution,
            model_data=model,
            experiment_manager=experiment_manager
        )

        if success:
            print("\n" + "=" * 70)
            print("✅ TEST PASSED - End-to-end pipeline successful!")
            print("=" * 70)

            # Verify layer files exist
            base_dir = Path(f"results/experiments/{experiment_id}/data")
            test_id = f"{scenario.id}_{constitution.id}_{model['id']}"

            layer1_file = base_dir / "layer1" / f"{test_id}.json"
            layer2_file = base_dir / "layer2" / f"{test_id}.json"
            layer3_file = base_dir / "layer3" / f"{test_id}.json"

            print("\nVerifying layer files:")
            print(f"  Layer 1: {'✅' if layer1_file.exists() else '❌'} {layer1_file}")
            print(f"  Layer 2: {'✅' if layer2_file.exists() else '❌'} {layer2_file}")
            print(f"  Layer 3: {'✅' if layer3_file.exists() else '❌'} {layer3_file}")

            # Check for README files
            readme1 = base_dir / "layer1" / "README.txt"
            readme2 = base_dir / "layer2" / "README.txt"
            readme3 = base_dir / "layer3" / "README.txt"

            print("\nVerifying README files:")
            print(f"  Layer 1: {'✅' if readme1.exists() else '❌'} {readme1}")
            print(f"  Layer 2: {'✅' if readme2.exists() else '❌'} {readme2}")
            print(f"  Layer 3: {'✅' if readme3.exists() else '❌'} {readme3}")

            print(f"\nTest results saved to: results/experiments/{experiment_id}/")

        else:
            print("\n" + "=" * 70)
            print("❌ TEST FAILED - Check error messages above")
            print("=" * 70)
            return 1

    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED - Exception: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
