#!/usr/bin/env python3
"""Quick verification script to test the reorganized experiment system."""

import asyncio
from datetime import datetime
from pathlib import Path

from src.core.scenarios import load_scenarios
from src.core.constitutions import CONSTITUTIONS
from src.core.models import MODELS, get_model_response
from src.core.prompts import (
    build_fact_establishment_prompt,
    build_constitutional_reasoning_prompt,
    build_integrity_evaluation_prompt
)

async def verify_single_test():
    """Run a single complete test through all 3 layers."""

    print("=" * 70)
    print("Constitutional Reasoning Engine - System Verification")
    print("=" * 70)

    # Load test data
    scenarios = load_scenarios()
    print(f"\n✅ Loaded {len(scenarios)} scenarios")

    constitution_name = "harm-minimization"
    constitution = next(c for c in CONSTITUTIONS if c.name == constitution_name)
    print(f"✅ Loaded constitution: {constitution_name}")

    model_name = "gpt-4o"
    print(f"✅ Using model: {model_name}")

    scenario = scenarios[0]
    print(f"✅ Test scenario: {scenario['id']}")

    # Layer 1: Fact Establishment
    print("\n" + "-" * 70)
    print("LAYER 1: Fact Establishment (GPT-4o)")
    print("-" * 70)

    fact_prompt = build_fact_establishment_prompt(scenario)
    print(f"Prompt length: {len(fact_prompt)} chars")

    facts_response = await get_model_response(
        model="gpt-4o",
        prompt=fact_prompt,
        max_tokens=2000
    )

    print(f"✅ Got facts response ({len(facts_response)} chars)")
    print(f"Preview: {facts_response[:200]}...")

    # Layer 2: Constitutional Reasoning
    print("\n" + "-" * 70)
    print(f"LAYER 2: Constitutional Reasoning ({model_name})")
    print("-" * 70)

    reasoning_prompt = build_constitutional_reasoning_prompt(
        scenario=scenario,
        constitution=constitution,
        facts={"raw": facts_response}  # Simplified for verification
    )
    print(f"Prompt length: {len(reasoning_prompt)} chars")

    reasoning_response = await get_model_response(
        model=model_name,
        prompt=reasoning_prompt,
        max_tokens=4000
    )

    print(f"✅ Got reasoning response ({len(reasoning_response)} chars)")
    print(f"Preview: {reasoning_response[:200]}...")

    # Layer 3: Integrity Evaluation
    print("\n" + "-" * 70)
    print("LAYER 3: Integrity Evaluation (Claude Sonnet 4.5)")
    print("-" * 70)

    integrity_prompt = build_integrity_evaluation_prompt(
        scenario=scenario,
        constitution_name=constitution_name,
        facts={"raw": facts_response},
        response={"raw": reasoning_response}
    )
    print(f"Prompt length: {len(integrity_prompt)} chars")

    integrity_response = await get_model_response(
        model="claude-sonnet-4-5",
        prompt=integrity_prompt,
        max_tokens=3000
    )

    print(f"✅ Got integrity evaluation ({len(integrity_response)} chars)")
    print(f"Preview: {integrity_response[:200]}...")

    # Success summary
    print("\n" + "=" * 70)
    print("✅ VERIFICATION SUCCESSFUL!")
    print("=" * 70)
    print("\nAll 3 layers executed successfully:")
    print("  ✅ Layer 1: Fact Establishment")
    print("  ✅ Layer 2: Constitutional Reasoning")
    print("  ✅ Layer 3: Integrity Evaluation")
    print("\nThe reorganized experiment system is working correctly!")
    print("=" * 70)

    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(verify_single_test())
        exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
