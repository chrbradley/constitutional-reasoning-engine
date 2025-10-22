"""
Simple test runner for the Constitutional Reasoning Engine
Tests the parking lot scenario with 3 models and 2 constitutions
"""
import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add experiments/src to path
sys.path.append('experiments/src')

from models import get_model_response, MODELS
from scenarios import get_scenario_by_id
from constitutions import CONSTITUTIONS
from prompts import (
    build_fact_establishment_prompt,
    build_constitutional_reasoning_prompt,
    build_integrity_evaluation_prompt
)
from data_types import Scenario


async def run_single_test(scenario, constitution, model):
    """
    Run a single test: scenario × constitution × model through 3-layer system
    """
    print(f"\n{'='*80}")
    print(f"Testing: {scenario.title} | {constitution.name} | {model['name']}")
    print(f"{'='*80}")
    
    try:
        # Layer 1: Establish facts (using Claude for consistency)
        print("Layer 1: Establishing facts...")
        fact_prompt = build_fact_establishment_prompt(scenario)
        fact_response = await get_model_response(
            model_id="claude-sonnet-4-5",
            prompt=fact_prompt,
            temperature=0.3,
            max_tokens=1000
        )
        
        try:
            # Clean JSON response (remove markdown code blocks if present)
            clean_response = fact_response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            facts = json.loads(clean_response)
            print(f"✓ Facts established: {len(facts.get('establishedFacts', []))} facts, {len(facts.get('ambiguousElements', []))} ambiguities")
        except json.JSONDecodeError:
            print(f"✗ Failed to parse facts JSON: {fact_response[:100]}...")
            return None
        
        # Layer 2: Constitutional reasoning
        print(f"Layer 2: Applying {constitution.name} framework...")
        reasoning_prompt = build_constitutional_reasoning_prompt(
            scenario=scenario,
            constitution=constitution,
            established_facts=facts['establishedFacts'],
            ambiguous_elements=facts['ambiguousElements']
        )
        
        constitutional_response = await get_model_response(
            model_id=model['id'],
            prompt=reasoning_prompt,
            system_prompt=constitution.system_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        try:
            # Clean JSON response
            clean_response = constitutional_response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            response_data = json.loads(clean_response)
            print(f"✓ Constitutional reasoning complete")
            print(f"  Recommendation: {response_data.get('recommendation', 'N/A')[:80]}...")
        except json.JSONDecodeError:
            print(f"✗ Failed to parse constitutional response JSON: {constitutional_response[:100]}...")
            return None
        
        # Layer 3: Integrity evaluation (using Claude for consistency)
        print("Layer 3: Evaluating integrity...")
        eval_prompt = build_integrity_evaluation_prompt(
            established_facts=facts['establishedFacts'],
            ambiguous_elements=facts['ambiguousElements'],
            constitutional_response=response_data
        )
        
        integrity_response = await get_model_response(
            model_id="claude-sonnet-4-5",
            prompt=eval_prompt,
            temperature=0.3,
            max_tokens=2000
        )
        
        try:
            # Clean JSON response
            clean_response = integrity_response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            integrity_data = json.loads(clean_response)
            overall_score = (
                integrity_data['factualAdherence']['score'] +
                integrity_data['valueTransparency']['score'] +
                integrity_data['logicalCoherence']['score']
            ) / 3
            integrity_data['overallScore'] = round(overall_score)
            
            print(f"✓ Integrity evaluation complete")
            print(f"  Factual Adherence: {integrity_data['factualAdherence']['score']}/100")
            print(f"  Value Transparency: {integrity_data['valueTransparency']['score']}/100")
            print(f"  Logical Coherence: {integrity_data['logicalCoherence']['score']}/100")
            print(f"  Overall Score: {integrity_data['overallScore']}/100")
            
        except json.JSONDecodeError:
            print(f"✗ Failed to parse integrity evaluation JSON: {integrity_response[:100]}...")
            return None
        
        # Compile complete result
        result = {
            "testId": f"{scenario.id}_{constitution.id}_{model['id']}",
            "timestamp": datetime.now().isoformat(),
            "scenario": scenario.model_dump(),
            "constitution": constitution.id,
            "model": model['id'],
            "facts": facts,
            "constitutionalResponse": response_data,
            "integrityEvaluation": integrity_data
        }
        
        print(f"✅ Test completed successfully!")
        return result
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return None


async def main():
    """
    Main test function - run parking lot scenario with 3 models × 2 constitutions
    """
    print("Constitutional Reasoning Engine - Simple Test")
    print("=" * 60)
    
    # Load scenario
    scenario = get_scenario_by_id("parking-lot-altercation")
    print(f"Scenario: {scenario.title}")
    
    # Select 2 constitutions for testing
    test_constitutions = [
        next(c for c in CONSTITUTIONS if c.id == "harm-minimization"),
        next(c for c in CONSTITUTIONS if c.id == "self-sovereignty")
    ]
    print(f"Constitutions: {[c.name for c in test_constitutions]}")
    
    # Use 2 fastest models for initial test
    test_models = [
        next(m for m in MODELS if m['id'] == 'claude-sonnet-4-5'),
        next(m for m in MODELS if m['id'] == 'gpt-4o')
    ]
    print(f"Models: {[m['name'] for m in test_models]}")
    
    print(f"\nRunning {len(test_constitutions)} × {len(test_models)} = {len(test_constitutions) * len(test_models)} tests...")
    
    # Run all combinations
    results = []
    for constitution in test_constitutions:
        for model in test_models:
            result = await run_single_test(scenario, constitution, model)
            if result:
                results.append(result)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(2)
    
    # Save results
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Completed: {len(results)}/{len(test_constitutions) * len(test_models)} tests")
    
    if results:
        # Show summary of integrity scores
        print("\nIntegrity Scores by Constitution & Model:")
        for result in results:
            const_name = next(c.name for c in test_constitutions if c.id == result['constitution'])
            model_name = next(m['name'] for m in test_models if m['id'] == result['model'])
            score = result['integrityEvaluation']['overallScore']
            print(f"  {const_name} × {model_name}: {score}/100")
        
        # Save to file
        output_dir = Path("results/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"simple_test_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "scenario": scenario.id,
                    "constitutions": [c.id for c in test_constitutions],
                    "models": [m['id'] for m in test_models],
                    "totalTests": len(results)
                },
                "results": results
            }, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
    
    print("\n🎉 Simple test complete!")


if __name__ == "__main__":
    asyncio.run(main())