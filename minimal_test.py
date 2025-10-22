"""
Minimal test: 1 scenario × 1 constitution × 1 model through 3-layer pipeline
"""
import asyncio
import json
import sys

sys.path.append('experiments/src')

from models import get_model_response
from scenarios import get_scenario_by_id
from constitutions import CONSTITUTIONS
from prompts import (
    build_fact_establishment_prompt,
    build_constitutional_reasoning_prompt,
    build_integrity_evaluation_prompt
)


def clean_json_response(response: str) -> str:
    """Clean JSON response by removing markdown code blocks"""
    clean = response.strip()
    if clean.startswith('```json'):
        clean = clean[7:]
    if clean.endswith('```'):
        clean = clean[:-3]
    return clean.strip()


async def minimal_test():
    print("Minimal Test: 1 scenario × 1 constitution × 1 model")
    print("=" * 60)
    
    # Load components
    scenario = get_scenario_by_id("parking-lot-altercation")
    constitution = next(c for c in CONSTITUTIONS if c.id == "harm-minimization")
    model_id = "claude-sonnet-4-5"  # Use Claude for everything
    
    print(f"Scenario: {scenario.title}")
    print(f"Constitution: {constitution.name}")
    print(f"Model: {model_id}")
    print()
    
    try:
        # Layer 1: Facts
        print("Layer 1: Establishing facts...")
        fact_prompt = build_fact_establishment_prompt(scenario)
        fact_response = await get_model_response(model_id, fact_prompt, temperature=0.3, max_tokens=800)
        
        facts = json.loads(clean_json_response(fact_response))
        print(f"✓ Facts: {len(facts['establishedFacts'])} established, {len(facts['ambiguousElements'])} ambiguous")
        
        # Layer 2: Constitutional reasoning
        print("Layer 2: Constitutional reasoning...")
        reasoning_prompt = build_constitutional_reasoning_prompt(
            scenario, constitution, facts['establishedFacts'], facts['ambiguousElements']
        )
        reasoning_response = await get_model_response(
            model_id, reasoning_prompt, system_prompt=constitution.system_prompt, temperature=0.7, max_tokens=1200
        )
        
        reasoning_data = json.loads(clean_json_response(reasoning_response))
        print(f"✓ Recommendation: {reasoning_data['recommendation'][:60]}...")
        
        # Layer 3: Integrity evaluation
        print("Layer 3: Integrity evaluation...")
        eval_prompt = build_integrity_evaluation_prompt(
            facts['establishedFacts'], facts['ambiguousElements'], reasoning_data
        )
        eval_response = await get_model_response(model_id, eval_prompt, temperature=0.3, max_tokens=1500)
        
        eval_data = json.loads(clean_json_response(eval_response))
        overall_score = (
            eval_data['factualAdherence']['score'] +
            eval_data['valueTransparency']['score'] +
            eval_data['logicalCoherence']['score']
        ) / 3
        
        print("✓ Integrity scores:")
        print(f"  Factual Adherence: {eval_data['factualAdherence']['score']}/100")
        print(f"  Value Transparency: {eval_data['valueTransparency']['score']}/100")
        print(f"  Logical Coherence: {eval_data['logicalCoherence']['score']}/100")
        print(f"  Overall Score: {round(overall_score)}/100")
        
        print(f"\n🎉 SUCCESS! Complete 3-layer pipeline working!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(minimal_test())
    if success:
        print("\n✅ Ready to scale up the experiment!")
    else:
        print("\n❌ Fix issues before scaling up.")