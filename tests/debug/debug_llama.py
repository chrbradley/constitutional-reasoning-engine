"""
Debug Llama JSON response issues
"""
import asyncio
import json
import sys

sys.path.append('experiments/src')

from models import get_model_response
from scenarios import get_scenario_by_id
from constitutions import CONSTITUTIONS
from prompts import build_constitutional_reasoning_prompt


async def debug_llama_response():
    print("Debugging Llama JSON Response Issues")
    print("=" * 50)
    
    # Load test data
    scenario = get_scenario_by_id("parking-lot-altercation")
    constitution = next(c for c in CONSTITUTIONS if c.id == "harm-minimization")
    
    # Mock facts from Layer 1 (to skip that step)
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
    
    # Build constitutional reasoning prompt
    reasoning_prompt = build_constitutional_reasoning_prompt(
        scenario=scenario,
        constitution=constitution,
        established_facts=mock_facts,
        ambiguous_elements=mock_ambiguities
    )
    
    print("Testing Llama with constitutional reasoning prompt...")
    print(f"Constitution: {constitution.name}")
    print()
    
    try:
        # Get raw response from Llama
        response = await get_model_response(
            model_id="llama-3-8b",
            prompt=reasoning_prompt,
            system_prompt=constitution.system_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        print("RAW LLAMA RESPONSE:")
        print("-" * 40)
        print(repr(response))  # Use repr to show control characters
        print("-" * 40)
        print()
        
        print("FORMATTED RESPONSE:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        print()
        
        # Try different cleaning approaches
        print("TRYING DIFFERENT CLEANING METHODS:")
        
        # Method 1: Our current cleaning
        print("1. Current cleaning method:")
        try:
            clean1 = response.strip()
            if clean1.startswith('```json'):
                clean1 = clean1[7:]
            if clean1.endswith('```'):
                clean1 = clean1[:-3]
            clean1 = clean1.strip()
            
            parsed1 = json.loads(clean1)
            print("   ✅ SUCCESS with current method")
            print(f"   Keys: {list(parsed1.keys())}")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            print(f"   Clean text: {repr(clean1[:100])}")
        
        # Method 2: Remove control characters
        print("2. Remove control characters:")
        try:
            import re
            clean2 = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response)
            clean2 = clean2.strip()
            if clean2.startswith('```json'):
                clean2 = clean2[7:]
            if clean2.endswith('```'):
                clean2 = clean2[:-3]
            clean2 = clean2.strip()
            
            parsed2 = json.loads(clean2)
            print("   ✅ SUCCESS with control character removal")
            print(f"   Keys: {list(parsed2.keys())}")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            print(f"   Clean text: {repr(clean2[:100])}")
        
        # Method 3: Extract JSON block
        print("3. Extract JSON block with regex:")
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                clean3 = json_match.group(0)
                # Remove control characters
                clean3 = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', clean3)
                
                parsed3 = json.loads(clean3)
                print("   ✅ SUCCESS with JSON extraction")
                print(f"   Keys: {list(parsed3.keys())}")
            else:
                print("   ❌ No JSON block found")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            print(f"   Clean text: {repr(clean3[:100])}")
        
        # Method 4: Character-by-character analysis
        print("4. Character analysis (first 200 chars):")
        for i, char in enumerate(response[:200]):
            if ord(char) < 32 or ord(char) > 126:
                print(f"   Position {i}: {repr(char)} (ord {ord(char)})")
        
    except Exception as e:
        print(f"❌ Error getting response from Llama: {e}")


if __name__ == "__main__":
    asyncio.run(debug_llama_response())