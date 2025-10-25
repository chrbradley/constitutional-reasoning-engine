"""
Test Haiku as Layer 3 evaluator on existing Layer 2 results

This test validates whether Haiku can replace Sonnet as the integrity evaluator
by loading existing Layer 2 constitutional reasoning from another model and
evaluating it with Haiku.
"""
import asyncio
import json
from pathlib import Path
from src.core.models import get_model_response
from src.core.prompts import build_integrity_evaluation_prompt
from src.core.graceful_parser import GracefulJsonParser

async def test_haiku_evaluator():
    """Test Haiku as Layer 3 evaluator on existing Layer 2 result"""

    # Load existing Layer 2 result from experiment
    EXP_ID = "exp_20251025_133622"
    BASE_DIR = Path("results/experiments") / EXP_ID
    LAYER1_DIR = BASE_DIR / "data" / "layer1"
    LAYER2_DIR = BASE_DIR / "data" / "layer2"

    # Pick first available Layer 2 result
    layer2_files = sorted(LAYER2_DIR.glob("*.json"))
    if not layer2_files:
        print("❌ No Layer 2 results found in experiment!")
        return

    test_file = layer2_files[0]
    test_id = test_file.stem

    print(f"\n{'='*80}")
    print(f"Testing Haiku as Layer 3 Evaluator")
    print(f"Test ID: {test_id}")
    print(f"{'='*80}\n")

    # Load Layer 1 (facts)
    layer1_path = LAYER1_DIR / f"{test_id}.json"
    if not layer1_path.exists():
        print(f"❌ Missing Layer 1 for {test_id}")
        return

    with open(layer1_path, 'r') as f:
        layer1_data = json.load(f)

    # Extract facts from nested structure
    facts = layer1_data.get('facts', {})
    established_facts = facts.get('establishedFacts', [])
    ambiguous_elements = facts.get('ambiguousElements', [])

    print(f"Layer 1: Loaded {len(established_facts)} facts")

    # Load Layer 2 (constitutional reasoning from another model)
    with open(test_file, 'r') as f:
        layer2_data = json.load(f)

    response_data = layer2_data.get('response', {})
    model_tested = layer2_data.get('model', 'unknown')

    print(f"Layer 2: Loaded reasoning from {model_tested}")
    print(f"   Recommendation: {response_data.get('recommendation', '')[:100]}...")

    # Build integrity evaluation prompt
    print(f"\nLayer 3: Evaluating with Haiku...")
    integrity_prompt = build_integrity_evaluation_prompt(
        established_facts=established_facts,
        ambiguous_elements=ambiguous_elements,
        constitutional_response=response_data
    )

    print(f"Prompt length: {len(integrity_prompt)} chars")

    # Call Haiku for evaluation
    model_id = "claude-3-5-haiku-20241022"
    integrity_response = await get_model_response(
        model_id=model_id,
        prompt=integrity_prompt,
        temperature=0.3,
        max_tokens=2000
    )

    print(f"Raw Haiku response length: {len(integrity_response)} chars")
    print(f"First 200 chars: {integrity_response[:200] if integrity_response else 'EMPTY'}...")

    if not integrity_response or integrity_response.strip() == "":
        print("❌ Haiku returned EMPTY content")
        return

    # Parse response using GracefulJsonParser
    parser = GracefulJsonParser()
    integrity_data, integrity_status = parser.parse_integrity_response(
        integrity_response,
        f"test_haiku_eval_{test_id}"
    )

    print(f"\nParse status: {integrity_status.name}")
    if integrity_status.name == "SUCCESS":
        overall_score = (
            integrity_data['factualAdherence']['score'] +
            integrity_data['valueTransparency']['score'] +
            integrity_data['logicalCoherence']['score']
        ) / 3
        print(f"✅ Haiku evaluation successful!")
        print(f"   Overall Score: {overall_score:.1f}/100")
        print(f"   Factual Adherence: {integrity_data['factualAdherence']['score']}/100")
        print(f"   Value Transparency: {integrity_data['valueTransparency']['score']}/100")
        print(f"   Logical Coherence: {integrity_data['logicalCoherence']['score']}/100")
    elif integrity_status.name == "PARTIAL_SUCCESS":
        print(f"⚠️  Haiku evaluation partially successful")
        print(f"   Some scores extracted, see raw response for details")
    else:
        print(f"❌ Haiku evaluation failed: {integrity_status.name}")

    print(f"\n{'='*80}")
    print("Test Complete!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(test_haiku_evaluator())
