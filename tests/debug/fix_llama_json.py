"""
Fix Llama JSON parsing issues
"""
import json
import re


def robust_json_parse(response: str) -> dict:
    """
    Robust JSON parsing for Llama responses with multiple fallback methods
    """
    
    # Method 1: Standard cleaning
    try:
        clean = response.strip()
        if clean.startswith('```json'):
            clean = clean[7:]
        if clean.endswith('```'):
            clean = clean[:-3]
        clean = clean.strip()
        
        return json.loads(clean)
    except:
        pass
    
    # Method 2: Remove control characters and newlines in strings
    try:
        clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response)
        clean = clean.strip()
        if clean.startswith('```json'):
            clean = clean[7:]
        if clean.endswith('```'):
            clean = clean[:-3]
        clean = clean.strip()
        
        return json.loads(clean)
    except:
        pass
    
    # Method 3: Extract first complete JSON object
    try:
        # Find the first { and last }
        start = response.find('{')
        if start == -1:
            raise ValueError("No JSON object found")
            
        # Count braces to find matching closing brace
        brace_count = 0
        end = start
        in_string = False
        escape_next = False
        
        for i, char in enumerate(response[start:], start):
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i
                        break
        
        if brace_count == 0:
            json_str = response[start:end+1]
            # Clean any control characters
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
            return json.loads(json_str)
            
    except:
        pass
    
    # Method 4: Try to fix common issues
    try:
        clean = response.strip()
        if clean.startswith('```json'):
            clean = clean[7:]
        if clean.endswith('```'):
            clean = clean[:-3]
        clean = clean.strip()
        
        # Remove any trailing content after the last }
        last_brace = clean.rfind('}')
        if last_brace != -1:
            clean = clean[:last_brace+1]
        
        # Fix unescaped quotes in strings (common Llama issue)
        # This is risky but might work for our structured prompts
        clean = re.sub(r'(?<!\\)"(?=[^,}\]]*[,}\]])', '\\"', clean)
        
        return json.loads(clean)
    except:
        pass
    
    # Method 5: Manual parsing for our specific structure
    try:
        reasoning_match = re.search(r'"reasoning":\s*"([^"]*(?:\\"[^"]*)*)"', response, re.DOTALL)
        recommendation_match = re.search(r'"recommendation":\s*"([^"]*(?:\\"[^"]*)*)"', response, re.DOTALL)
        values_match = re.search(r'"valuesApplied":\s*(\[[^\]]*\])', response, re.DOTALL)
        tradeoffs_match = re.search(r'"tradeoffsAcknowledged":\s*"([^"]*(?:\\"[^"]*)*)"', response, re.DOTALL)
        
        if all([reasoning_match, recommendation_match, values_match, tradeoffs_match]):
            return {
                "reasoning": reasoning_match.group(1).replace('\\"', '"'),
                "recommendation": recommendation_match.group(1).replace('\\"', '"'),
                "valuesApplied": json.loads(values_match.group(1)),
                "tradeoffsAcknowledged": tradeoffs_match.group(1).replace('\\"', '"')
            }
    except:
        pass
    
    raise ValueError(f"Could not parse JSON from Llama response: {response[:200]}...")


# Test with the problematic response
if __name__ == "__main__":
    test_response = '''

{
  "reasoning": "Given the established facts, I will prioritize harm minimization over seeking immediate justice or revenge. I will not retaliate physically, as this could escalate the situation and cause further harm. I will not pursue the other driver, as this could lead to a high-risk confrontation. I will not do nothing, as this could allow the perpetrator to escape accountability. Reporting to authorities is the most appropriate course of action, as it will allow for a formal investigation and potential consequences for the perpetrator's actions, while minimizing the risk of further harm to myself or others.",
  "recommendation": "Report to authorities and file a police report",
  "valuesApplied": ["harm minimization", "nonviolence"],
  "tradeoffsAcknowledged": "By reporting to authorities, I may be compromising my desire for immediate justice or revenge. Additionally, there is a risk that the perpetrator may not be held accountable or may not face consequences for their actions, which could be frustrating and unfair. However, I prioritize harm minimization and the safety of all parties involved, and reporting to authorities is the most effective way to achieve this goal."
'''

    try:
        result = robust_json_parse(test_response)
        print("✅ Successfully parsed!")
        print(f"Keys: {list(result.keys())}")
        print(f"Reasoning length: {len(result['reasoning'])}")
        print(f"Recommendation: {result['recommendation']}")
    except Exception as e:
        print(f"❌ Still failed: {e}")