"""
Scenario loading and management for Constitutional Reasoning Engine
"""
import json
from pathlib import Path
from typing import List
from data_types import Scenario


def load_scenarios(scenarios_file: str = "experiments/data/scenarios.json") -> List[Scenario]:
    """
    Load scenarios from JSON file
    
    Args:
        scenarios_file: Path to scenarios JSON file
        
    Returns:
        List of Scenario objects
    """
    scenarios_path = Path(scenarios_file)
    
    if not scenarios_path.exists():
        raise FileNotFoundError(f"Scenarios file not found: {scenarios_file}")
    
    with open(scenarios_path, 'r') as f:
        scenarios_data = json.load(f)
    
    scenarios = []
    for scenario_data in scenarios_data:
        scenario = Scenario(**scenario_data)
        scenarios.append(scenario)
    
    return scenarios


def get_scenario_by_id(scenario_id: str, scenarios_file: str = "experiments/data/scenarios.json") -> Scenario:
    """
    Get a specific scenario by ID
    
    Args:
        scenario_id: The ID of the scenario to retrieve
        scenarios_file: Path to scenarios JSON file
        
    Returns:
        Scenario object
        
    Raises:
        ValueError: If scenario_id not found
    """
    scenarios = load_scenarios(scenarios_file)
    
    for scenario in scenarios:
        if scenario.id == scenario_id:
            return scenario
    
    raise ValueError(f"Scenario ID '{scenario_id}' not found")


def list_scenario_ids(scenarios_file: str = "experiments/data/scenarios.json") -> List[str]:
    """
    Get list of all scenario IDs
    
    Args:
        scenarios_file: Path to scenarios JSON file
        
    Returns:
        List of scenario IDs
    """
    scenarios = load_scenarios(scenarios_file)
    return [s.id for s in scenarios]


def list_scenarios_by_category(category: str, scenarios_file: str = "experiments/data/scenarios.json") -> List[Scenario]:
    """
    Get scenarios filtered by category
    
    Args:
        category: Category to filter by ('personal', 'community', 'societal')
        scenarios_file: Path to scenarios JSON file
        
    Returns:
        List of scenarios in the specified category
    """
    scenarios = load_scenarios(scenarios_file)
    return [s for s in scenarios if s.category == category]