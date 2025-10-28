"""
Type definitions for the Constitutional Reasoning Engine
"""
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel
from datetime import datetime


class Scenario(BaseModel):
    """Scenario definition"""
    id: str
    title: str
    category: Literal['personal', 'community', 'societal']
    description: str
    established_facts: List[str]
    ambiguous_elements: List[str]
    decision_point: str


class Constitution(BaseModel):
    """Constitutional framework"""
    id: str
    name: str
    description: str
    system_prompt: str
    core_values: List[str]


class Model(BaseModel):
    """Model configuration"""
    id: str
    name: str
    provider: Literal['anthropic', 'openai', 'google', 'xai', 'replicate', 'deepseek']
    api_model: str


class ConstitutionalResponse(BaseModel):
    """Response from a model using a specific constitution"""
    trial_id: str
    scenario_id: str
    model_id: str
    constitution_id: str
    timestamp: str
    reasoning: str
    recommendation: str
    values_applied: List[str]
    tradeoffs_acknowledged: str
    response_time_ms: int


class IntegrityDimension(BaseModel):
    """Individual integrity dimension score"""
    score: int  # 0-100
    explanation: str
    examples: List[str]


class IntegrityScore(BaseModel):
    """Complete integrity evaluation (V2.0 - 2D Rubric)"""
    trial_id: str
    epistemic_integrity: IntegrityDimension
    value_transparency: IntegrityDimension
    overall_score: int  # Average of two dimensions

    # Legacy fields for backward compatibility
    factual_adherence: Optional[IntegrityDimension] = None
    logical_coherence: Optional[IntegrityDimension] = None


class TrialResult(BaseModel):
    """Complete trial result combining response and integrity"""
    response: ConstitutionalResponse
    integrity_score: IntegrityScore


class ModelStats(BaseModel):
    """Statistics for a specific model (V2.0 - 2D Rubric)"""
    model_id: str
    avg_overall_score: float
    avg_epistemic_integrity: float
    avg_value_transparency: float
    trial_count: int

    # Legacy fields for backward compatibility
    avg_factual_adherence: Optional[float] = None
    avg_logical_coherence: Optional[float] = None


class ConstitutionStats(BaseModel):
    """Statistics for a specific constitution (V2.0 - 2D Rubric)"""
    constitution_id: str
    avg_overall_score: float
    avg_epistemic_integrity: float
    avg_value_transparency: float
    trial_count: int

    # Legacy fields for backward compatibility
    avg_factual_adherence: Optional[float] = None
    avg_logical_coherence: Optional[float] = None


class ScenarioStats(BaseModel):
    """Statistics for a specific scenario (V2.0 - 2D Rubric)"""
    scenario_id: str
    avg_overall_score: float
    avg_epistemic_integrity: float
    avg_value_transparency: float
    trial_count: int

    # Legacy fields for backward compatibility
    avg_factual_adherence: Optional[float] = None
    avg_logical_coherence: Optional[float] = None


class ExperimentMetadata(BaseModel):
    """Experiment metadata"""
    timestamp: str
    total_trials: int
    models_trialed: List[str]
    constitutions_trialed: List[str]
    scenarios_trialed: List[str]


class AggregateStats(BaseModel):
    """Aggregated statistics across all dimensions"""
    by_model: List[ModelStats]
    by_constitution: List[ConstitutionStats]
    by_scenario: List[ScenarioStats]


class ExperimentSummary(BaseModel):
    """Complete experiment results"""
    metadata: ExperimentMetadata
    results: List[TrialResult]
    aggregate_stats: AggregateStats