"""
Experiment state management for Constitutional Reasoning Engine
Handles job tracking, resumption, and incremental execution
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from src.core.data_types import Scenario, Constitution, Model
from src.core.schemas import TrialRegistry, TrialMetadata, TrialStatus


@dataclass
class TrialDefinition:
    """Definition of a single experimental trial to be run"""
    trial_id: str  # Sequential ID: trial_001, trial_002, etc.
    scenario_id: str
    constitution_id: str
    model_id: str


@dataclass
class ExperimentState:
    """Overall experiment state"""
    experiment_id: str
    created_at: str
    updated_at: str
    status: str  # "in_progress", "completed", "failed", "paused"
    total_trials: int
    completed_count: int
    failed_count: int
    pending_count: int
    scenarios: List[str]
    constitutions: List[str]
    models: List[str]
    layer3_evaluators: List[str]
    command_line: Optional[str] = None  # Command used to start experiment


class ExperimentManager:
    """Manages experiment state, tracking, and resumption"""

    def __init__(self, base_dir: str = "results", experiment_id: Optional[str] = None, force_new: bool = False):
        self.base_dir = Path(base_dir)
        self.global_state_dir = self.base_dir / "state"
        self.current_experiment_file = self.global_state_dir / "current_experiment.json"

        # Create global state directory
        self.global_state_dir.mkdir(parents=True, exist_ok=True)

        # Determine which experiment to load
        if force_new:
            # Force new experiment - ignore pointer
            self.experiment_id = None
        elif experiment_id:
            # Explicit experiment_id provided (e.g., --resume flag)
            self.experiment_id = experiment_id
        else:
            # Check for current experiment pointer
            current_exp = self._load_current_experiment_pointer()
            if current_exp:
                self.experiment_id = current_exp
            else:
                self.experiment_id = None

        # Set up per-experiment state paths
        if self.experiment_id:
            # State files live INSIDE the experiment directory
            exp_dir = self.base_dir / "experiments" / self.experiment_id
            self.state_dir = exp_dir / "state"
            self.state_file = self.state_dir / "experiment_state.json"
            self.trial_registry_file = self.state_dir / "trial_registry.json"

            # Create experiment state directory
            self.state_dir.mkdir(parents=True, exist_ok=True)

            # Load state from experiment-specific location
            self.experiment_state = self._load_experiment_state()
            self.trial_registry = self._load_test_registry()

            # Set up layer directories
            data_dir = exp_dir / "data"
            self.layer1_dir = data_dir / "layer1"
            self.layer2_dir = data_dir / "layer2"
            self.layer3_dir = data_dir / "layer3"
            self.charts_dir = exp_dir / "visualizations"

            # Create flat layer directories (no subdirectories)
            self._create_layer_subdirectories()

            # Copy README files
            self._copy_layer_readmes()

            # Backward compatibility
            self.results_dir = self.layer2_dir
        else:
            # No experiment loaded yet
            self.state_dir = None
            self.state_file = None
            self.trial_registry_file = None
            self.experiment_state = None
            self.trial_registry = TrialRegistry()
            self.layer1_dir = None
            self.layer2_dir = None
            self.layer3_dir = None
            self.results_dir = None
            self.charts_dir = None
    
    def create_experiment(
        self,
        scenarios: List[Scenario],
        constitutions: List[Constitution],
        models: List[Dict],
        layer3_evaluators: List[str]
    ) -> str:
        """Create a new experiment or resume existing one"""

        # Generate experiment ID if new
        if not self.experiment_state:
            experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Update experiment_id and set up per-experiment state paths
            self.experiment_id = experiment_id
            exp_dir = self.base_dir / "experiments" / experiment_id

            # Set up state directory inside experiment
            self.state_dir = exp_dir / "state"
            self.state_file = self.state_dir / "experiment_state.json"
            self.trial_registry_file = self.state_dir / "trial_registry.json"
            self.state_dir.mkdir(parents=True, exist_ok=True)

            # Set up data and visualization directories
            data_dir = exp_dir / "data"
            self.layer1_dir = data_dir / "layer1"
            self.layer2_dir = data_dir / "layer2"
            self.layer3_dir = data_dir / "layer3"
            self.charts_dir = exp_dir / "visualizations"
            self.results_dir = self.layer2_dir  # Backward compatibility

            # Create flat layer directories (no subdirectories)
            self._create_layer_subdirectories()

            # Copy README files to layer directories
            self._copy_layer_readmes()

            # Generate all trial combinations
            trial_definitions = self._generate_trial_combinations(scenarios, constitutions, models)

            # Initialize experiment state
            import sys
            self.experiment_state = ExperimentState(
                experiment_id=experiment_id,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                status="in_progress",
                total_trials=len(trial_definitions),
                completed_count=0,
                failed_count=0,
                pending_count=len(trial_definitions),
                scenarios=[s.id for s in scenarios],
                constitutions=[c.id for c in constitutions],
                models=[m['id'] for m in models],
                layer3_evaluators=layer3_evaluators,
                command_line=" ".join(sys.argv)
            )

            # Initialize trial registry
            self.trial_registry = TrialRegistry()
            for trial_def in trial_definitions:
                self.trial_registry.add_trial(
                    trial_id=trial_def.trial_id,
                    scenario_id=trial_def.scenario_id,
                    constitution=trial_def.constitution_id,
                    model=trial_def.model_id
                )

            # Save state to per-experiment location
            self._save_state()

            # Update global pointer to this experiment
            self._save_current_experiment_pointer(experiment_id)

            print(f"Created new experiment: {experiment_id}")
        else:
            experiment_id = self.experiment_state.experiment_id
            print(f"Resuming experiment: {experiment_id}")

        return experiment_id
    
    def add_new_models(self, new_models: List[Dict], scenarios: List[Scenario], constitutions: List[Constitution]) -> int:
        """Add new models to existing experiment without rerunning existing tests"""
        if not self.experiment_state:
            raise ValueError("No active experiment. Create one first.")

        # Find truly new models
        existing_models = set(self.experiment_state.models)
        new_model_ids = [m['id'] for m in new_models if m['id'] not in existing_models]

        if not new_model_ids:
            print("No new models to add.")
            return 0

        # Find highest existing trial number to continue sequence
        max_trial_num = 0
        for trial_id in self.trial_registry.trials.keys():
            if trial_id.startswith("trial_"):
                try:
                    num = int(trial_id.split("_")[1])
                    max_trial_num = max(max_trial_num, num)
                except (IndexError, ValueError):
                    pass

        # Generate combinations for new models only
        new_trial_count = 0
        trial_counter = max_trial_num + 1
        for scenario in scenarios:
            for constitution in constitutions:
                for model in new_models:
                    if model['id'] in new_model_ids:
                        trial_id = f"trial_{trial_counter:03d}"
                        trial_def = TrialDefinition(
                            trial_id=trial_id,
                            scenario_id=scenario.id,
                            constitution_id=constitution.id,
                            model_id=model['id']
                        )

                        if trial_def.trial_id not in self.trial_registry.trials:
                            self.trial_registry.add_trial(
                                trial_id=trial_def.trial_id,
                                scenario_id=trial_def.scenario_id,
                                constitution=trial_def.constitution_id,
                                model=trial_def.model_id
                            )
                            new_trial_count += 1
                            trial_counter += 1

        # Update experiment state
        self.experiment_state.models.extend(new_model_ids)
        self.experiment_state.total_trials += new_trial_count
        self.experiment_state.pending_count += new_trial_count
        self.experiment_state.updated_at = datetime.now().isoformat()

        self._save_state()
        print(f"Added {new_trial_count} new trials for {len(new_model_ids)} new models")
        return new_trial_count
    
    def get_pending_trials(self) -> List[TrialDefinition]:
        """Get list of all pending tests"""
        pending = []
        for trial_id, metadata in self.trial_registry.trials.items():
            if metadata.status == TrialStatus.PENDING:
                pending.append(TrialDefinition(
                    trial_id=trial_id,
                    scenario_id=metadata.scenario_id,
                    constitution_id=metadata.constitution,
                    model_id=metadata.model
                ))
        return pending
    
    def get_failed_trials(self, max_retries: int = 3) -> List[TrialDefinition]:
        """Get list of failed tests"""
        failed = []
        for trial_id, metadata in self.trial_registry.trials.items():
            if metadata.status == TrialStatus.FAILED:
                failed.append(TrialDefinition(
                    trial_id=trial_id,
                    scenario_id=metadata.scenario_id,
                    constitution_id=metadata.constitution,
                    model_id=metadata.model
                ))
        return failed
    
    def mark_test_in_progress(self, trial_id: str) -> None:
        """Mark a trial as currently running"""
        if trial_id in self.trial_registry.trials:
            previous_status = self.trial_registry.trials[trial_id].status
            self.trial_registry.update_status(trial_id, TrialStatus.IN_PROGRESS)

            # Decrement pending count when moving from PENDING to IN_PROGRESS
            if previous_status == TrialStatus.PENDING:
                self.experiment_state.pending_count -= 1
                self.experiment_state.updated_at = datetime.now().isoformat()
                self._save_experiment_state()

            self._save_test_registry()

    def update_layer_status(self, trial_id: str, layer_num: int, status: str, model_id: str = None, error: str = None) -> None:
        """Update status for a specific layer of a trial

        Note: Layer status is now tracked in individual layer files, not in trial registry.
        This method is kept for backward compatibility but does minimal validation.

        Args:
            trial_id: Trial identifier
            layer_num: Layer number (1, 2, or 3)
            status: Status string ("pending", "completed", "failed", "skipped")
            model_id: Model used for this layer (optional)
            error: Error message if failed (optional)
        """
        # Validate trial exists
        if trial_id not in self.trial_registry.trials:
            print(f"Warning: Trial {trial_id} not found in registry")
        # No-op: layer status tracking removed from trial registry

    def mark_test_completed(self, trial_id: str, result_data: Dict = None) -> None:
        """Mark a trial as completed and update registry

        Args:
            trial_id: Trial identifier
            result_data: DEPRECATED - result data now stored in layer files only
        """
        if trial_id in self.trial_registry.trials:
            # Update status in registry
            self.trial_registry.update_status(trial_id, TrialStatus.COMPLETED)

            # Note: Individual layer files are saved via save_layer_result()
            # No need to save a combined file here (was causing layer2/layer3 contamination)

            # Update experiment state
            self.experiment_state.completed_count += 1
            self.experiment_state.updated_at = datetime.now().isoformat()

            self._save_state()
            # Suppress verbose completion log (runner shows compact trial summaries)
            # print(f"✅ Completed: {trial_id}")

    def save_raw_response(self, trial_id: str, layer: int, raw_content: str) -> None:
        """
        DEPRECATED: Raw responses are now stored in the JSON file's response_raw field.
        This method is kept for backward compatibility but does nothing.
        """
        pass

    def save_layer_result(self, trial_id: str, layer: int, layer_data: Dict) -> None:
        """Save result for a specific layer (1, 2, or 3) - flat structure with sequential naming"""
        layer_dirs = {
            1: self.layer1_dir,
            2: self.layer2_dir,
            3: self.layer3_dir
        }

        if layer not in layer_dirs:
            raise ValueError(f"Invalid layer: {layer}. Must be 1, 2, or 3.")

        layer_dir = layer_dirs[layer]
        if layer_dir:
            result_file = layer_dir / f"{trial_id}.json"
            with open(result_file, 'w') as f:
                json.dump(layer_data, f, indent=2)

    def save_evaluator_response(
        self,
        trial_id: str,
        evaluator_id: str,
        is_primary: bool,
        raw_content: str,
        parsed_data: Dict
    ) -> None:
        """
        Save Layer 3 evaluator response (supports primary + re-evaluation runs)

        Args:
            trial_id: Unique trial identifier
            evaluator_id: Model ID of the evaluator
            is_primary: True for primary evaluator, False for re-evaluation runs
            raw_content: Raw API response (stored in parsed_data['response_raw'])
            parsed_data: Complete evaluation data including raw response

        Directory structure:
            - Primary (is_primary=True): layer3/{trial_id}.json
            - Re-evaluation (is_primary=False): layer3/{evaluator_id}/{trial_id}.json
        """
        if is_primary:
            # Primary evaluator uses standard flat structure
            result_file = self.layer3_dir / f"{trial_id}.json"
        else:
            # Re-evaluation runs get their own subdirectories
            evaluator_subdir = self.layer3_dir / evaluator_id
            evaluator_subdir.mkdir(parents=True, exist_ok=True)
            result_file = evaluator_subdir / f"{trial_id}.json"

        # Save complete data (includes both raw and parsed in single JSON)
        with open(result_file, 'w') as f:
            json.dump(parsed_data, f, indent=2)

    def save_evaluator_error(
        self,
        trial_id: str,
        evaluator_id: str,
        is_primary: bool,
        error_details: Dict
    ) -> None:
        """
        Save Layer 3 evaluator error (supports primary + re-evaluation runs)

        Args:
            trial_id: Unique trial identifier
            evaluator_id: Model ID of the evaluator
            is_primary: True for primary evaluator, False for re-evaluation runs
            error_details: Error information dict
        """
        if is_primary:
            # Primary evaluator uses standard flat structure
            error_file = self.layer3_dir / f"{trial_id}.error.json"
        else:
            # Re-evaluation runs get their own subdirectories
            evaluator_subdir = self.layer3_dir / evaluator_id
            evaluator_subdir.mkdir(parents=True, exist_ok=True)
            error_file = evaluator_subdir / f"{trial_id}.error.json"

        # Save error details
        with open(error_file, 'w') as f:
            json.dump(error_details, f, indent=2)
    
    def mark_test_failed(self, trial_id: str, error_message: str) -> None:
        """Mark a trial as failed

        Args:
            trial_id: Trial identifier
            error_message: Error description (saved in layer error files, not registry)
        """
        if trial_id in self.trial_registry.trials:
            # Check if this was already failed (for retry logic)
            was_previously_failed = self.trial_registry.trials[trial_id].status == TrialStatus.FAILED

            # Update status in registry
            self.trial_registry.update_status(trial_id, TrialStatus.FAILED)

            # Update experiment state
            # Only increment failed_count on first failure
            if not was_previously_failed:
                self.experiment_state.failed_count += 1

            self.experiment_state.updated_at = datetime.now().isoformat()

            self._save_state()
            print(f"❌ Failed: {trial_id}")

    def save_error_response(self, trial_id: str, layer: int, error_details: Dict) -> None:
        """
        Save detailed error information when an API call fails

        Args:
            trial_id: Unique trial identifier
            layer: Layer number (1, 2, or 3)
            error_details: Dict containing:
                - error_type: Exception class name
                - error_message: Exception message
                - raw_response: Raw response body (if any)
                - http_status: HTTP status code (if available)
                - timestamp: When the error occurred
                - request_params: Request parameters sent to API
        """
        layer_dirs = {
            1: self.layer1_dir,
            2: self.layer2_dir,
            3: self.layer3_dir
        }
        if layer not in layer_dirs:
            raise ValueError(f"Invalid layer: {layer}. Must be 1, 2, or 3.")

        layer_dir = layer_dirs[layer]
        if layer_dir:
            # Save error file directly to layer directory (flat structure)
            error_file = layer_dir / f"{trial_id}.error.json"

            with open(error_file, 'w') as f:
                json.dump(error_details, f, indent=2)

    def save_api_audit_log(
        self,
        trial_id: str,
        layer: int,
        model_id: str,
        request_params: Dict,
        response: Optional[str] = None,
        error: Optional[Exception] = None,
        http_status: Optional[int] = None,
        retry_attempt: int = 1
    ) -> None:
        """
        Save comprehensive audit log for every API call (success or failure)

        This creates a detailed record of all API interactions for debugging and analysis.

        Args:
            trial_id: Unique trial identifier
            layer: Layer number (1, 2, or 3)
            model_id: Model being called
            request_params: Dict with temperature, max_tokens, prompt_length, etc.
            response: Raw response body (if successful)
            error: Exception object (if failed)
            http_status: HTTP status code
            retry_attempt: Which retry attempt this was (1 = first attempt)
        """
        # Create debug directory structure
        exp_dir = self.base_dir / "experiments" / self.experiment_id
        debug_dir = exp_dir / "debug" / "api_calls"
        debug_dir.mkdir(parents=True, exist_ok=True)

        # Create audit log entry
        audit_entry = {
            "trial_id": trial_id,
            "layer": layer,
            "model_id": model_id,
            "retry_attempt": retry_attempt,
            "timestamp": datetime.now().isoformat(),
            "request": request_params,
            "http_status": http_status,
            "success": error is None
        }

        # Add response or error details
        if error:
            audit_entry["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "module": type(error).__module__
            }
            # Try to extract additional error details
            if hasattr(error, 'response'):
                try:
                    audit_entry["error"]["response_body"] = str(error.response)
                except:
                    pass
        else:
            audit_entry["response_length"] = len(response) if response else 0
            # Don't store full response here (it's in raw/), just metadata

        # Save with timestamp to handle multiple retries
        timestamp_suffix = datetime.now().strftime('%H%M%S_%f')
        audit_file = debug_dir / f"{trial_id}_L{layer}_attempt{retry_attempt}_{timestamp_suffix}.json"

        with open(audit_file, 'w') as f:
            json.dump(audit_entry, f, indent=2)

    def test_exists(self, trial_id: str) -> bool:
        """Check if a trial has been completed"""
        return (trial_id in self.trial_registry.trials and
                self.trial_registry.trials[trial_id].status == TrialStatus.COMPLETED)
    
    def get_progress_summary(self) -> Dict:
        """Get current experiment progress"""
        if not self.experiment_state:
            return {"status": "No active experiment"}

        return {
            "experiment_id": self.experiment_state.experiment_id,
            "status": self.experiment_state.status,
            "progress": {
                "total": self.experiment_state.total_trials,
                "completed": self.experiment_state.completed_count,
                "failed": self.experiment_state.failed_count,
                "pending": self.experiment_state.pending_count,
                "completion_rate": f"{(self.experiment_state.completed_count / self.experiment_state.total_trials * 100):.1f}%"
            },
            "created_at": self.experiment_state.created_at,
            "updated_at": self.experiment_state.updated_at
        }

    def finalize_experiment(self, clear_pointer: bool = True) -> None:
        """Mark experiment as complete and optionally clear pointer"""
        if self.experiment_state:
            self.experiment_state.status = "completed"
            self.experiment_state.updated_at = datetime.now().isoformat()
            self._save_state()

            if clear_pointer:
                self._clear_current_experiment_pointer()
                print(f"✅ Experiment {self.experiment_id} completed and finalized")
            else:
                print(f"✅ Experiment {self.experiment_id} completed (pointer preserved for easy resume)")

    def _generate_trial_combinations(
        self,
        scenarios: List[Scenario],
        constitutions: List[Constitution],
        models: List[Dict]
    ) -> List[TrialDefinition]:
        """Generate all trial combinations with sequential trial IDs"""
        combinations = []
        trial_counter = 1
        for scenario in scenarios:
            for constitution in constitutions:
                for model in models:
                    trial_id = f"trial_{trial_counter:03d}"
                    combinations.append(TrialDefinition(
                        trial_id=trial_id,
                        scenario_id=scenario.id,
                        constitution_id=constitution.id,
                        model_id=model['id']
                    ))
                    trial_counter += 1
        return combinations

    def _load_current_experiment_pointer(self) -> Optional[str]:
        """Load current experiment ID from pointer file"""
        if self.current_experiment_file.exists():
            try:
                with open(self.current_experiment_file, 'r') as f:
                    data = json.load(f)
                return data.get('experiment_id')
            except Exception as e:
                print(f"Warning: Could not load current experiment pointer: {e}")
        return None

    def _save_current_experiment_pointer(self, experiment_id: str) -> None:
        """Save current experiment ID to pointer file"""
        with open(self.current_experiment_file, 'w') as f:
            json.dump({"experiment_id": experiment_id}, f, indent=2)

    def _clear_current_experiment_pointer(self) -> None:
        """Clear current experiment pointer (experiment complete)"""
        if self.current_experiment_file.exists():
            os.remove(self.current_experiment_file)

    def _load_experiment_state(self) -> Optional[ExperimentState]:
        """Load experiment state from file"""
        if self.state_file and self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return ExperimentState(**data)
            except Exception as e:
                print(f"Warning: Could not load experiment state: {e}")
        return None

    def _load_test_registry(self) -> TrialRegistry:
        """Load test registry from file using TrialRegistry.model_validate()"""
        if self.trial_registry_file and self.trial_registry_file.exists():
            try:
                with open(self.trial_registry_file, 'r') as f:
                    data = json.load(f)
                return TrialRegistry.model_validate(data)
            except Exception as e:
                print(f"Warning: Could not load test registry: {e}")
        return TrialRegistry()
    
    def _save_state(self) -> None:
        """Save experiment state and test registry"""
        self._save_experiment_state()
        self._save_test_registry()
    
    def _save_experiment_state(self) -> None:
        """Save experiment state to file"""
        if self.experiment_state:
            with open(self.state_file, 'w') as f:
                json.dump(asdict(self.experiment_state), f, indent=2)
    
    def _save_test_registry(self) -> None:
        """Save test registry to file using TrialRegistry.model_dump()"""
        if self.trial_registry:
            with open(self.trial_registry_file, 'w') as f:
                json.dump(self.trial_registry.model_dump(), f, indent=2)

    def _create_layer_subdirectories(self) -> None:
        """Create flat layer directories (no raw/parsed subdirs in Phase 0.2+)"""
        for layer_dir in [self.layer1_dir, self.layer2_dir, self.layer3_dir]:
            if layer_dir:
                layer_dir.mkdir(parents=True, exist_ok=True)

    def _copy_layer_readmes(self) -> None:
        """Copy README files to layer directories"""
        readme_templates = Path("layer_readme_templates")
        if not readme_templates.exists():
            return  # Skip if templates don't exist

        readme_mappings = {
            self.layer1_dir: readme_templates / "LAYER1_README.txt",
            self.layer2_dir: readme_templates / "LAYER2_README.txt",
            self.layer3_dir: readme_templates / "LAYER3_README.txt"
        }

        for layer_dir, readme_template in readme_mappings.items():
            if layer_dir and readme_template.exists():
                dest = layer_dir / "README.txt"
                if not dest.exists():  # Only copy if doesn't already exist
                    shutil.copy(readme_template, dest)