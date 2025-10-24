"""
Extract JSON scenarios from SCENARIOS.md and create scenarios.json
"""
import json
import re
from pathlib import Path

# Read SCENARIOS.md
scenarios_md = Path("data/SCENARIOS.md").read_text()

# Extract all JSON code blocks
json_pattern = r'```json\n(.*?)\n```'
matches = re.findall(json_pattern, scenarios_md, re.DOTALL)

print(f"Found {len(matches)} JSON blocks")

# Parse each JSON block and convert to snake_case
scenarios = []
for i, match in enumerate(matches, 1):
    try:
        scenario = json.loads(match)

        # Convert camelCase to snake_case for Pydantic compatibility
        converted = {
            "id": scenario["id"],
            "title": scenario["title"],
            "category": scenario["scale"],  # Use 'scale' as 'category'
            "description": scenario["description"],
            "established_facts": scenario["establishedFacts"],
            "ambiguous_elements": scenario["ambiguousElements"],
            "decision_point": scenario["decisionPoint"]
        }

        scenarios.append(converted)
        print(f"✅ Scenario {i}: {scenario['id']}")
    except json.JSONDecodeError as e:
        print(f"❌ Scenario {i}: JSON parse error - {e}")
        print(f"   First 100 chars: {match[:100]}")
    except KeyError as e:
        print(f"❌ Scenario {i}: Missing field - {e}")
        print(f"   Available keys: {scenario.keys()}")

print(f"\nTotal valid scenarios: {len(scenarios)}")

# Save to scenarios.json
output_path = Path("data/scenarios.json")
with open(output_path, 'w') as f:
    json.dump(scenarios, f, indent=2)

print(f"✅ Saved to {output_path}")
