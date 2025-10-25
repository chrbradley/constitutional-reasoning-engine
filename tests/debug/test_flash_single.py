"""
Test single scenario with Flash through production pipeline
"""
import asyncio
import json
from pathlib import Path
from src.core.models import get_model_response
from src.core.scenarios import load_scenarios
from src.core.constitutions import CONSTITUTIONS
from src.core.prompts import (
    build_fact_establishment_prompt,
    build_constitutional_reasoning_prompt,
    build_integrity_evaluation_prompt
)
from src.core.graceful_parser import GracefulJsonParser

async def test_flash_pipeline():
    """Run one complete test with Flash"""

    # Test setup
    scenarios = load_scenarios()
    scenario = scenarios[0]  # First scenario
    constitution = CONSTITUTIONS[0]  # First constitution
    model_id = "gemini-2-5-flash"

    parser = GracefulJsonParser()

    print(f"\n{'='*80}")
    print(f"Testing Flash: {scenario.id} + {constitution.id}")
    print(f"{'='*80}\n")

    # Layer 1: Fact Establishment (using Claude)
    print("Layer 1: Fact Establishment (Claude)...")
    fact_prompt = build_fact_establishment_prompt(scenario)
    fact_response = await get_model_response(
        model_id="claude-sonnet-4-5",
        prompt=fact_prompt,
        temperature=0.3,
        max_tokens=4000
    )

    print(f"Claude Layer 1 response length: {len(fact_response) if fact_response else 0} chars")
    print(f"First 200 chars: {fact_response[:200] if fact_response else 'EMPTY'}...")

    if not fact_response or fact_response.strip() == "":
        print("❌ Claude returned EMPTY content for Layer 1")
        return

    # Strip markdown blocks
    fact_response_clean = fact_response.strip()
    if fact_response_clean.startswith("```json"):
        fact_response_clean = fact_response_clean.split("```json")[1].split("```")[0].strip()
    elif fact_response_clean.startswith("```"):
        fact_response_clean = fact_response_clean.split("```")[1].split("```")[0].strip()

    fact_data = json.loads(fact_response_clean)
    print(f"✅ Facts established: {len(fact_data.get('establishedFacts', []))} facts")

    # Layer 2: Constitutional Reasoning (using Flash)
    print("\nLayer 2: Constitutional Reasoning (Flash)...")
    constitutional_prompt = build_constitutional_reasoning_prompt(
        scenario=scenario,
        constitution=constitution,
        established_facts=fact_data.get('establishedFacts', [])
    )

    constitutional_response = await get_model_response(
        model_id=model_id,
        prompt=constitutional_prompt,
        system_prompt=constitution.system_prompt,
        temperature=0.7,
        max_tokens=8000
    )

    print(f"Raw Flash Layer 2 response length: {len(constitutional_response)} chars")
    print(f"First 200 chars: {constitutional_response[:200]}...")

    response_data, status = parser.parse_constitutional_response(
        constitutional_response,
        f"test_flash_{scenario.id}_{constitution.id}"
    )

    print(f"Parse status: {status.name}")
    if status.name == "SUCCESS":
        print(f"✅ Flash Layer 2 successful")
        print(f"   Recommendation: {response_data.get('recommendation', '')[:100]}...")
    else:
        print(f"❌ Flash Layer 2 failed: {status.name}")
        return

    # Layer 3: Integrity Evaluation (using Flash)
    print("\nLayer 3: Integrity Evaluation (Flash)...")
    integrity_prompt = build_integrity_evaluation_prompt(
        established_facts=fact_data.get('establishedFacts', []),
        ambiguous_elements=fact_data.get('ambiguousElements', []),
        constitutional_response=response_data
    )

    print(f"Integrity prompt length: {len(integrity_prompt)} chars")

    integrity_response = await get_model_response(
        model_id=model_id,
        prompt=integrity_prompt,
        temperature=0.3,
        max_tokens=2000
    )

    print(f"Raw Flash Layer 3 response length: {len(integrity_response)} chars")
    print(f"First 200 chars: {integrity_response[:200] if integrity_response else 'EMPTY'}...")

    if not integrity_response or integrity_response.strip() == "":
        print("❌ Flash returned EMPTY content for Layer 3")
        return

    integrity_data, integrity_status = parser.parse_integrity_response(
        integrity_response,
        f"test_flash_integrity_{scenario.id}_{constitution.id}"
    )

    print(f"Parse status: {integrity_status.name}")
    if integrity_status.name == "SUCCESS":
        overall_score = (
            integrity_data['factualAdherence']['score'] +
            integrity_data['valueTransparency']['score'] +
            integrity_data['logicalCoherence']['score']
        ) / 3
        print(f"✅ Flash Layer 3 successful: {overall_score:.1f}/100")
    else:
        print(f"❌ Flash Layer 3 failed: {integrity_status.name}")

    print(f"\n{'='*80}")
    print("Test Complete!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(test_flash_pipeline())
