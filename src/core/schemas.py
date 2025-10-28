"""
Pydantic schemas for Phase 0.2 data architecture redesign.

Defines the new trial-based data structure with sequential IDs and centralized registry.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TrialStatus(str, Enum):
    """Status of a trial in the experiment"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ParsingMethod(str, Enum):
    """Method used to parse JSON response"""

    STANDARD_JSON = "standard_json"
    MARKDOWN_STRIP = "markdown_strip"
    BRACE_EXTRACTION = "brace_extraction"
    MANUAL_REVIEW = "manual_review"


# ============================================================================
# TRIAL REGISTRY
# ============================================================================


class TrialMetadata(BaseModel):
    """
    Metadata for a single trial, stored in trial_registry.json.

    Maps trial_id → {scenario, constitution, model, timestamps, status}
    """

    scenario_id: str = Field(..., description="Scenario identifier (e.g., 'vaccine-mandate')")
    constitution: str = Field(..., description="Constitution used (e.g., 'harm-minimization')")
    model: str = Field(..., description="Model that performed Layer 2 reasoning")
    created_at: str = Field(..., description="ISO timestamp when trial was created")
    status: TrialStatus = Field(default=TrialStatus.PENDING, description="Current trial status")

    class Config:
        json_schema_extra = {
            "example": {
                "scenario_id": "vaccine-mandate-religious-exemption",
                "constitution": "harm-minimization",
                "model": "claude-sonnet-4-5",
                "created_at": "2025-10-26T19:32:28Z",
                "status": "completed",
            }
        }


class TrialRegistry(BaseModel):
    """
    Complete trial registry mapping trial IDs to metadata.

    Stored in: results/experiments/{exp_id}/state/trial_registry.json
    """

    trials: Dict[str, TrialMetadata] = Field(
        default_factory=dict, description="Map of trial_id to metadata"
    )

    def add_trial(
        self, trial_id: str, scenario_id: str, constitution: str, model: str
    ) -> None:
        """Add a new trial to the registry"""
        self.trials[trial_id] = TrialMetadata(
            scenario_id=scenario_id,
            constitution=constitution,
            model=model,
            created_at=datetime.utcnow().isoformat() + "Z",
            status=TrialStatus.PENDING,
        )

    def update_status(self, trial_id: str, status: TrialStatus) -> None:
        """Update trial status"""
        if trial_id in self.trials:
            self.trials[trial_id].status = status
        else:
            raise KeyError(f"Trial {trial_id} not found in registry")

    def get_trials_by_constitution(self, constitution: str) -> List[str]:
        """Get all trial IDs for a specific constitution"""
        return [
            tid
            for tid, meta in self.trials.items()
            if meta.constitution == constitution
        ]

    def get_trials_by_scenario(self, scenario_id: str) -> List[str]:
        """Get all trial IDs for a specific scenario"""
        return [
            tid for tid, meta in self.trials.items() if meta.scenario_id == scenario_id
        ]

    def get_trials_by_model(self, model: str) -> List[str]:
        """Get all trial IDs for a specific model"""
        return [tid for tid, meta in self.trials.items() if meta.model == model]


# ============================================================================
# PARSING METADATA
# ============================================================================


class ParsingInfo(BaseModel):
    """
    Metadata about JSON parsing for Layer 2/3 responses.

    Tracks whether parsing succeeded and what fallback strategies were used.
    """

    success: bool = Field(..., description="Whether parsing succeeded")
    method: ParsingMethod = Field(
        ..., description="Parsing method that succeeded (or last attempted)"
    )
    fallback_attempts: int = Field(
        default=0, description="Number of fallback strategies attempted"
    )
    error: Optional[str] = Field(default=None, description="Error message if parsing failed")
    manual_review_path: Optional[str] = Field(
        default=None, description="Path to manual review file if parsing failed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "method": "standard_json",
                "fallback_attempts": 0,
                "error": None,
                "manual_review_path": None,
            }
        }


# ============================================================================
# LAYER 1: FACT ESTABLISHMENT
# ============================================================================


class Layer1Data(BaseModel):
    """
    Layer 1 data: Fact establishment.

    In Phase 1: This layer is skipped (facts loaded from scenarios.json)
    Future phases: Will contain RAG results, citations, fact-grounding mechanisms
    """

    trial_id: str = Field(..., description="Trial identifier (e.g., 'trial_001')")
    layer: int = Field(default=1, description="Layer number (always 1)")
    timestamp: str = Field(..., description="ISO timestamp when layer completed")
    status: str = Field(..., description="Layer status: 'completed', 'skipped', 'failed'")

    # Facts
    facts: List[str] = Field(..., description="List of factual statements")
    source: str = Field(..., description="Source of facts: 'scenarios.json', 'rag', 'citations'")
    reason: Optional[str] = Field(
        default=None, description="Reason for skip/failure (e.g., 'Phase 1 bypasses Layer 1')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trial_id": "trial_001",
                "layer": 1,
                "timestamp": "2025-10-26T19:32:28Z",
                "status": "skipped",
                "facts": [
                    "A 2021 CDC study found vaccine reduced infection risk by 85%.",
                    "Religious exemption requests increased 300%.",
                ],
                "source": "scenarios.json",
                "reason": "Phase 1 bypasses Layer 1 - facts from scenarios.json",
            }
        }


# ============================================================================
# LAYER 2: CONSTITUTIONAL REASONING
# ============================================================================


class Layer2Data(BaseModel):
    """
    Layer 2 data: Constitutional reasoning.

    Model applies constitutional framework to established facts.

    CRITICAL: response_raw is ALWAYS captured (saved immediately after API call)
              response_parsed may be None if parsing fails
    """

    trial_id: str = Field(..., description="Trial identifier (e.g., 'trial_001')")
    layer: int = Field(default=2, description="Layer number (always 2)")
    timestamp: str = Field(..., description="ISO timestamp when layer completed")
    status: str = Field(..., description="Layer status: 'completed', 'failed'")

    # Trial metadata (propagated for self-contained files)
    scenario_id: str = Field(..., description="Scenario being reasoned about")
    model: str = Field(..., description="Model that performed reasoning")
    constitution: str = Field(..., description="Constitutional framework applied")

    # Prompt and response
    prompt_sent: str = Field(..., description="Full prompt sent to model")
    response_raw: str = Field(
        ..., description="Raw API response (ALWAYS captured, immutable)"
    )
    response_parsed: Optional[Dict[str, Any]] = Field(
        default=None, description="Parsed response (may be None if parsing failed)"
    )

    # Parsing metadata
    parsing: ParsingInfo = Field(..., description="Parsing metadata")

    # Performance metrics
    tokens_used: int = Field(..., description="Number of tokens used in API call")
    latency_ms: int = Field(..., description="API call latency in milliseconds")
    truncation_detected: bool = Field(
        default=False, description="Whether response was truncated"
    )

    @field_validator("response_parsed")
    @classmethod
    def validate_parsing_consistency(cls, v, info):
        """If parsing succeeded, response_parsed must not be None"""
        if info.data.get("parsing") and info.data["parsing"].success and v is None:
            raise ValueError("If parsing.success=True, response_parsed cannot be None")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "trial_id": "trial_001",
                "layer": 2,
                "timestamp": "2025-10-26T19:32:30Z",
                "status": "completed",
                "scenario_id": "vaccine-mandate-religious-exemption",
                "model": "claude-sonnet-4-5",
                "constitution": "harm-minimization",
                "prompt_sent": "Given the following facts:\n\n1. ...",
                "response_raw": "From a harm-minimization perspective...",
                "response_parsed": {
                    "reasoning": "...",
                    "conclusion": "...",
                },
                "parsing": {
                    "success": True,
                    "method": "standard_json",
                    "fallback_attempts": 0,
                    "error": None,
                },
                "tokens_used": 8234,
                "latency_ms": 4521,
                "truncation_detected": False,
            }
        }


# ============================================================================
# LAYER 3: INTEGRITY EVALUATION
# ============================================================================


class SingleEvaluationData(BaseModel):
    """
    Single evaluation from one evaluator model.

    Layer3Data will contain multiple of these (one per evaluator in ensemble).
    """

    timestamp: str = Field(..., description="ISO timestamp when this evaluation completed")
    status: str = Field(..., description="Evaluation status: 'completed', 'failed'")
    evaluation_strategy: str = Field(
        ..., description="Evaluation strategy: 'single_prompt_likert', 'multi_prompt_binary'"
    )

    # Prompt and response
    prompt_sent: str = Field(..., description="Full evaluation prompt sent to model")
    response_raw: str = Field(
        ..., description="Raw API response (ALWAYS captured, immutable)"
    )
    response_parsed: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parsed evaluation with scores, explanations, and examples (may be None if parsing failed). "
        "Expected structure (V2.0): {'epistemic_integrity': {'score': 72, 'explanation': '...', 'examples': [...]}, "
        "'value_transparency': {...}, 'overall_score': 78}. "
        "Legacy V1.0 structure also supported: {'factual_adherence': {...}, 'value_transparency': {...}, 'logical_coherence': {...}}",
    )

    # Parsing metadata
    parsing: ParsingInfo = Field(..., description="Parsing metadata")

    # Performance metrics
    tokens_used: int = Field(..., description="Number of tokens used in API call")
    latency_ms: int = Field(..., description="API call latency in milliseconds")

    @field_validator("response_parsed")
    @classmethod
    def validate_parsing_consistency(cls, v, info):
        """If parsing succeeded, response_parsed must not be None"""
        if info.data.get("parsing") and info.data["parsing"].success and v is None:
            raise ValueError("If parsing.success=True, response_parsed cannot be None")
        return v


class Layer3Data(BaseModel):
    """
    Layer 3 data: Integrity evaluation (ENSEMBLE SUPPORT).

    Multiple evaluators assess the same Layer 2 response for factual adherence,
    value transparency, and logical coherence.

    UPDATED: Now supports multiple evaluations per trial (ensemble evaluations).
    Each evaluator (claude, gpt-4o, deepseek, grok, gemini) provides independent scores.

    CRITICAL: response_raw is ALWAYS captured for each evaluation
              response_parsed may be None if parsing fails
    """

    trial_id: str = Field(..., description="Trial identifier (e.g., 'trial_001')")
    layer: int = Field(default=3, description="Layer number (always 3)")

    # Trial metadata (propagated from Layer 2 for self-contained files)
    # These apply to ALL evaluations in this trial
    scenario_id: str = Field(..., description="Scenario that was evaluated")
    model: str = Field(..., description="Model whose reasoning was evaluated (from Layer 2)")
    constitution: str = Field(..., description="Constitutional framework that was applied")

    # ENSEMBLE EVALUATIONS: Dict[evaluator_name, evaluation_data]
    evaluations: Dict[str, SingleEvaluationData] = Field(
        ...,
        description="Map of evaluator model name to evaluation data. "
        "Keys: 'claude-sonnet-4-5', 'gpt-4o', 'deepseek-chat', 'grok-3', 'gemini-2-5-pro'. "
        "Each evaluator provides independent integrity scores."
    )

    def get_evaluators(self) -> List[str]:
        """Get list of evaluator models that evaluated this trial"""
        return list(self.evaluations.keys())

    def get_evaluation(self, evaluator: str) -> Optional[SingleEvaluationData]:
        """Get evaluation from specific evaluator"""
        return self.evaluations.get(evaluator)

    def get_scores(self, evaluator: str, dimension: str = "overall_score") -> Optional[float]:
        """
        Get score from specific evaluator for specific dimension.

        Args:
            evaluator: Evaluator model name
            dimension: V2.0: 'overall_score', 'epistemic_integrity', 'value_transparency'
                      V1.0 (legacy): 'factual_adherence', 'logical_coherence'

        Returns: Score (0-100) or None if not available
        """
        eval_data = self.evaluations.get(evaluator)
        if not eval_data or not eval_data.response_parsed:
            return None

        if dimension == "overall_score":
            return eval_data.response_parsed.get("overall_score")
        else:
            dim_data = eval_data.response_parsed.get(dimension, {})
            if isinstance(dim_data, dict):
                return dim_data.get("score")
            return None

    def get_consensus_score(self, dimension: str = "overall_score") -> Optional[float]:
        """
        Get consensus score (mean across all evaluators) for a dimension.

        Args:
            dimension: V2.0: 'overall_score', 'epistemic_integrity', 'value_transparency'
                      V1.0 (legacy): 'factual_adherence', 'logical_coherence'

        Returns: Mean score or None if no evaluations available
        """
        scores = []
        for evaluator in self.evaluations.keys():
            score = self.get_scores(evaluator, dimension)
            if score is not None:
                scores.append(score)

        return sum(scores) / len(scores) if scores else None

    class Config:
        json_schema_extra = {
            "example": {
                "trial_id": "trial_001",
                "layer": 3,
                "scenario_id": "vaccine-mandate-religious-exemption",
                "model": "claude-sonnet-4-5",
                "constitution": "harm-minimization",
                "evaluations": {
                    "claude-sonnet-4-5": {
                        "timestamp": "2025-10-26T19:32:35Z",
                        "status": "completed",
                        "evaluation_strategy": "single_prompt_likert",
                        "prompt_sent": "Evaluate the following...",
                        "response_raw": '{"epistemic_integrity": {...}, ...}',
                        "response_parsed": {
                            "epistemicIntegrity": {"score": 93, "explanation": "...", "examples": [...]},
                            "valueTransparency": {"score": 90, "explanation": "...", "examples": [...]},
                            "overall_score": 92
                        },
                        "parsing": {"success": True, "method": "standard_json", "fallback_attempts": 0, "error": None},
                        "tokens_used": 3421,
                        "latency_ms": 2134
                    },
                    "gpt-4o": {
                        "timestamp": "2025-10-26T19:33:01Z",
                        "status": "completed",
                        "evaluation_strategy": "single_prompt_likert",
                        "prompt_sent": "Evaluate the following...",
                        "response_raw": '{"epistemic_integrity": {...}, ...}',
                        "response_parsed": {
                            "epistemicIntegrity": {"score": 91, "explanation": "...", "examples": [...]},
                            "valueTransparency": {"score": 88, "explanation": "...", "examples": [...]},
                            "overall_score": 90
                        },
                        "parsing": {"success": True, "method": "standard_json", "fallback_attempts": 0, "error": None},
                        "tokens_used": 3205,
                        "latency_ms": 1987
                    }
                }
            }
        }


# ============================================================================
# MIGRATION HELPERS
# ============================================================================


def parse_old_filename(filename: str) -> Dict[str, str]:
    """
    Parse old filename format to extract metadata.

    Old format: vaccine-mandate-religious-exemption_harm-minimization_claude-sonnet-4-5.json
    Returns: {"scenario_id": "...", "constitution": "...", "model": "..."}
    """
    # Remove .json extension
    base = filename.replace(".json", "")

    # Split by underscore (3 parts expected)
    parts = base.rsplit("_", 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid filename format: {filename}. Expected 3 parts separated by '_'")

    scenario_id, constitution, model = parts
    return {"scenario_id": scenario_id, "constitution": constitution, "model": model}
