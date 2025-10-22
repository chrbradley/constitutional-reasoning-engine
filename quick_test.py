"""
Quick test of just the fact establishment layer
"""
import asyncio
import json
import sys
import os

sys.path.append('experiments/src')

from models import get_model_response
from scenarios import get_scenario_by_id
from prompts import build_fact_establishment_prompt


async def quick_test():
    print("Quick test: Fact establishment layer")
    
    # Load scenario
    scenario = get_scenario_by_id("parking-lot-altercation")
    print(f"Scenario: {scenario.title}")
    
    # Test fact establishment
    fact_prompt = build_fact_establishment_prompt(scenario)
    print("Testing fact establishment with Claude...")
    
    fact_response = await get_model_response(
        model_id="claude-sonnet-4-5",
        prompt=fact_prompt,
        temperature=0.3,
        max_tokens=1000
    )
    
    print("Raw response:")
    print(fact_response)
    print("\n" + "="*50)
    
    # Try parsing
    try:
        clean_response = fact_response.strip()
        if clean_response.startswith('```json'):
            clean_response = clean_response[7:]
        if clean_response.endswith('```'):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        facts = json.loads(clean_response)
        print("✓ Successfully parsed JSON!")
        print(f"Facts: {len(facts.get('establishedFacts', []))}")
        print(f"Ambiguities: {len(facts.get('ambiguousElements', []))}")
        print(f"Questions: {len(facts.get('keyQuestions', []))}")
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing failed: {e}")


if __name__ == "__main__":
    asyncio.run(quick_test())