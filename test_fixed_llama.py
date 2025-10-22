"""
Test the fixed Llama JSON parsing
"""
import asyncio
import json
import sys

sys.path.append('experiments/src')

from models import get_model_response
from scenarios import get_scenario_by_id
from constitutions import CONSTITUTIONS
from prompts import build_constitutional_reasoning_prompt

# Import our robust parser
sys.path.append('.')
from robust_experiment_runner import robust_json_parse


async def test_fixed_llama():
    print("Testing Fixed Llama JSON Parsing")
    print("=" * 40)
    
    # Load test data
    scenario = get_scenario_by_id("parking-lot-altercation")
    constitution = next(c for c in CONSTITUTIONS if c.id == "harm-minimization")
    
    # Mock facts from Layer 1
    mock_facts = [
        "Both drivers arrived at approximately the same time",
        "You pulled into the parking spot",
        "The other driver physically assaulted you",
        "You were not seriously injured",
        "The other driver is now leaving the scene"
    ]
    
    mock_ambiguities = [
        "Who actually arrived first",
        "Whether pulling into the spot constituted initial aggression",
        "The other driver's emotional state and motivation"
    ]
    
    try:
        # Build constitutional reasoning prompt
        reasoning_prompt = build_constitutional_reasoning_prompt(
            scenario=scenario,
            constitution=constitution,
            established_facts=mock_facts,
            ambiguous_elements=mock_ambiguities
        )
        
        print("Getting Llama response...")
        response = await get_model_response(
            model_id="llama-3-8b",
            prompt=reasoning_prompt,
            system_prompt=constitution.system_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        print("Testing robust JSON parser...")
        parsed_data = robust_json_parse(response)
        
        print("✅ SUCCESS! Llama JSON parsed correctly")
        print(f"Keys: {list(parsed_data.keys())}")
        print(f"Recommendation: {parsed_data.get('recommendation', 'N/A')}")
        
        # Verify all required fields
        required_fields = ['reasoning', 'recommendation', 'valuesApplied', 'tradeoffsAcknowledged']
        missing_fields = [field for field in required_fields if field not in parsed_data]
        
        if missing_fields:
            print(f"⚠️  Missing fields: {missing_fields}")
        else:
            print("✅ All required fields present")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"Response preview: {response[:200] if 'response' in locals() else 'No response'}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_fixed_llama())
    if success:
        print("\n🎉 Llama JSON parsing fixed! Ready to resume experiment.")
    else:
        print("\n❌ Still having issues with Llama parsing.")