"""
Test Gemini 2.5 Pro with one complete experiment run
"""
import asyncio
import json
import sys
sys.path.insert(0, 'experiments/src')

from models import get_model_response
from scenarios import load_scenarios
from constitutions import CONSTITUTIONS
from prompts import build_fact_establishment_prompt, build_constitutional_reasoning_prompt, build_integrity_evaluation_prompt
from graceful_parser import GracefulJsonParser, ParseStatus

async def test_gemini_pipeline():
    """Run one complete test with Gemini to check JSON parsing"""

    # Load data
    scenarios = load_scenarios()
    scenario = scenarios[0]  # Parking lot altercation
    constitution = CONSTITUTIONS[0]  # Harm Minimization
    model_id = "gemini-2-5-flash"

    parser = GracefulJsonParser()

    print(f"\n{'='*80}")
    print(f"Testing: {scenario.id} + {constitution.id} + {model_id}")
    print(f"{'='*80}\n")

    # Layer 1: Fact Establishment
    print("Layer 1: Fact Establishment...")
    fact_prompt = build_fact_establishment_prompt(scenario)
    fact_response = await get_model_response(
        model_id="claude-sonnet-4-5",
        prompt=fact_prompt,
        system_prompt=None,
        temperature=0.3
    )

    # Parse facts (using simple JSON since facts come from Claude)
    try:
        fact_data = json.loads(fact_response)
        print(f"✅ Facts parsed successfully")
    except json.JSONDecodeError:
        print(f"⚠️  Facts parsing issue - using fallback")
        fact_data = {
            "establishedFacts": [],
            "ambiguousElements": [],
            "keyQuestions": []
        }

    # Layer 2: Constitutional Reasoning (with Gemini)
    print("\nLayer 2: Constitutional Reasoning (Gemini)...")
    constitutional_prompt = build_constitutional_reasoning_prompt(
        scenario=scenario,
        established_facts=fact_data.get("establishedFacts", []),
        ambiguous_elements=fact_data.get("ambiguousElements", []),
        constitution=constitution
    )

    constitutional_response = await get_model_response(
        model_id=model_id,
        prompt=constitutional_prompt,
        system_prompt=constitution.system_prompt,
        temperature=0.7,
        max_tokens=4000  # Increased to allow complete responses
    )

    print("\n--- Raw Gemini Response ---")
    if constitutional_response:
        print(constitutional_response[:500] + "..." if len(constitutional_response) > 500 else constitutional_response)
    else:
        print("⚠️  WARNING: Gemini returned None/empty response!")
    print("--- End Raw Response ---\n")

    response_data, constitutional_status = parser.parse_constitutional_response(
        constitutional_response,
        f"test_gemini_constitutional"
    )

    print(f"Constitutional parsing status: {constitutional_status.name}")
    if constitutional_status != ParseStatus.SUCCESS:
        print(f"⚠️  Constitutional parsing issue - check manual_review directory")
    else:
        print(f"✅ Successfully parsed constitutional response")
        print(f"   Recommendation: {response_data.get('recommendation', 'N/A')[:100]}...")

    # Layer 3: Integrity Evaluation
    print("\nLayer 3: Integrity Evaluation...")
    integrity_prompt = build_integrity_evaluation_prompt(
        established_facts=fact_data.get("establishedFacts", []),
        ambiguous_elements=fact_data.get("ambiguousElements", []),
        constitutional_response=response_data
    )

    integrity_response = await get_model_response(
        model_id="claude-sonnet-4-5",
        prompt=integrity_prompt,
        system_prompt=None,
        temperature=0.3
    )

    integrity_data, integrity_status = parser.parse_integrity_response(
        integrity_response,
        f"test_gemini_integrity"
    )

    print(f"Integrity parsing status: {integrity_status.name}")
    if integrity_status != ParseStatus.SUCCESS:
        print(f"⚠️  Integrity parsing issue")
    else:
        overall_score = (
            integrity_data['factualAdherence']['score'] +
            integrity_data['valueTransparency']['score'] +
            integrity_data['logicalCoherence']['score']
        ) / 3
        print(f"✅ Overall integrity score: {overall_score:.1f}/100")

    print(f"\n{'='*80}")
    print(f"Test Complete!")
    print(f"Parsing Results: Constitutional={constitutional_status.name}, Integrity={integrity_status.name}")
    print(f"{'='*80}\n")

    return {
        "constitutional_status": constitutional_status,
        "integrity_status": integrity_status
    }

if __name__ == "__main__":
    result = asyncio.run(test_gemini_pipeline())

    # Exit with success only if all parsing was successful
    if all(status == ParseStatus.SUCCESS for status in result.values()):
        print("✅ All parsing successful - Gemini ready for production!")
        sys.exit(0)
    else:
        print("⚠️  Some parsing issues detected - review before production use")
        sys.exit(1)
