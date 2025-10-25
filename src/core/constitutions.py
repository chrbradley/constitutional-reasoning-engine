"""
Constitutional frameworks for the Constitutional Reasoning Engine
"""
import json
from pathlib import Path
from typing import List
from src.core.data_types import Constitution


def load_constitutions() -> List[Constitution]:
    """
    Load constitutions from JSON file

    Returns:
        List of Constitution objects

    Raises:
        FileNotFoundError: If constitutions.json not found
        ValueError: If JSON is malformed
    """
    json_path = Path(__file__).parent.parent / "data" / "constitutions.json"

    with open(json_path, 'r') as f:
        data = json.load(f)

    constitutions = []
    for const_data in data['constitutions']:
        constitution = Constitution(
            id=const_data['id'],
            name=const_data['name'],
            description=const_data['description'],
            core_values=const_data['core_values'],
            system_prompt=const_data['system_prompt']
        )
        constitutions.append(constitution)

    return constitutions


def get_constitution_by_id(constitution_id: str, constitutions: List[Constitution] = None) -> Constitution:
    """
    Get a constitution by its ID

    Args:
        constitution_id: The ID of the constitution to retrieve
        constitutions: Optional list of constitutions to search. If None, loads from JSON.

    Returns:
        Constitution object

    Raises:
        ValueError: If constitution_id not found
    """
    if constitutions is None:
        constitutions = load_constitutions()

    for constitution in constitutions:
        if constitution.id == constitution_id:
            return constitution

    raise ValueError(f"Constitution ID '{constitution_id}' not found")


def list_constitution_ids(constitutions: List[Constitution] = None) -> List[str]:
    """
    Get list of all constitution IDs

    Args:
        constitutions: Optional list of constitutions. If None, loads from JSON.

    Returns:
        List of constitution IDs
    """
    if constitutions is None:
        constitutions = load_constitutions()

    return [c.id for c in constitutions]


def list_constitution_names(constitutions: List[Constitution] = None) -> List[str]:
    """
    Get list of all constitution names

    Args:
        constitutions: Optional list of constitutions. If None, loads from JSON.

    Returns:
        List of constitution names
    """
    if constitutions is None:
        constitutions = load_constitutions()

    return [c.name for c in constitutions]