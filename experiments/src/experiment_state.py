"""
Experiment state management for Constitutional Reasoning Engine
Handles job tracking, resumption, and incremental execution
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from data_types import Scenario, Constitution, Model


class TestStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class TestDefinition:
    """Definition of a single test to be run"""
    scenario_id: str
    constitution_id: str
    model_id: str
    
    @property
    def test_id(self) -> str:
        """Generate unique test ID"""
        return f"{self.scenario_id}_{self.constitution_id}_{self.model_id}"


@dataclass
class TestResult:
    """Result of a completed test"""
    test_id: str
    scenario_id: str
    constitution_id: str
    model_id: str
    timestamp: str
    status: TestStatus
    result_data: Optional[Dict] = None
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class ExperimentState:
    """Overall experiment state"""
    experiment_id: str
    created_at: str
    updated_at: str
    status: str  # "in_progress", "completed", "failed", "paused"
    total_tests: int
    completed_count: int
    failed_count: int
    pending_count: int
    scenarios: List[str]
    constitutions: List[str]
    models: List[str]


class ExperimentManager:
    """Manages experiment state, tracking, and resumption"""
    
    def __init__(self, base_dir: str = "results", experiment_id: Optional[str] = None):
        self.base_dir = Path(base_dir)
        self.state_dir = self.base_dir / "state"

        # Use experiment_id to organize results by run
        # If experiment_id is provided, use it; otherwise will be set in create_experiment
        self.experiment_id = experiment_id
        if experiment_id:
            self.results_dir = self.base_dir / "runs" / experiment_id / "raw"
            self.charts_dir = self.base_dir / "runs" / experiment_id / "charts"
        else:
            # Fallback to legacy structure
            self.results_dir = self.base_dir / "raw"
            self.charts_dir = self.base_dir / "charts"

        # Create directories
        for dir_path in [self.state_dir, self.results_dir, self.charts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.state_dir / "experiment_state.json"
        self.test_registry_file = self.state_dir / "test_registry.json"
        
        # Load or initialize state
        self.experiment_state = self._load_experiment_state()
        self.test_registry = self._load_test_registry()
    
    def create_experiment(
        self,
        scenarios: List[Scenario],
        constitutions: List[Constitution],
        models: List[Dict]
    ) -> str:
        """Create a new experiment or resume existing one"""

        # Generate experiment ID if new
        if not self.experiment_state:
            experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Update experiment_id and results directories
            self.experiment_id = experiment_id
            self.results_dir = self.base_dir / "runs" / experiment_id / "raw"
            self.charts_dir = self.base_dir / "runs" / experiment_id / "charts"

            # Create new directories for this experiment run
            for dir_path in [self.results_dir, self.charts_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)

            # Generate all test combinations
            test_definitions = self._generate_test_combinations(scenarios, constitutions, models)

            # Initialize experiment state
            self.experiment_state = ExperimentState(
                experiment_id=experiment_id,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                status="in_progress",
                total_tests=len(test_definitions),
                completed_count=0,
                failed_count=0,
                pending_count=len(test_definitions),
                scenarios=[s.id for s in scenarios],
                constitutions=[c.id for c in constitutions],
                models=[m['id'] for m in models]
            )
            
            # Initialize test registry
            self.test_registry = {
                test_def.test_id: TestResult(
                    test_id=test_def.test_id,
                    scenario_id=test_def.scenario_id,
                    constitution_id=test_def.constitution_id,
                    model_id=test_def.model_id,
                    timestamp="",
                    status=TestStatus.PENDING,
                    retry_count=0
                ) for test_def in test_definitions
            }
            
            self._save_state()
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
        
        # Generate combinations for new models only
        new_test_count = 0
        for scenario in scenarios:
            for constitution in constitutions:
                for model in new_models:
                    if model['id'] in new_model_ids:
                        test_def = TestDefinition(scenario.id, constitution.id, model['id'])
                        
                        if test_def.test_id not in self.test_registry:
                            self.test_registry[test_def.test_id] = TestResult(
                                test_id=test_def.test_id,
                                scenario_id=test_def.scenario_id,
                                constitution_id=test_def.constitution_id,
                                model_id=test_def.model_id,
                                timestamp="",
                                status=TestStatus.PENDING,
                                retry_count=0
                            )
                            new_test_count += 1
        
        # Update experiment state
        self.experiment_state.models.extend(new_model_ids)
        self.experiment_state.total_tests += new_test_count
        self.experiment_state.pending_count += new_test_count
        self.experiment_state.updated_at = datetime.now().isoformat()
        
        self._save_state()
        print(f"Added {new_test_count} new tests for {len(new_model_ids)} new models")
        return new_test_count
    
    def get_pending_tests(self) -> List[TestDefinition]:
        """Get list of all pending tests"""
        pending = []
        for test_result in self.test_registry.values():
            if test_result.status == TestStatus.PENDING:
                pending.append(TestDefinition(
                    scenario_id=test_result.scenario_id,
                    constitution_id=test_result.constitution_id,
                    model_id=test_result.model_id
                ))
        return pending
    
    def get_failed_tests(self, max_retries: int = 3) -> List[TestDefinition]:
        """Get list of failed tests that can be retried"""
        retryable = []
        for test_result in self.test_registry.values():
            if (test_result.status == TestStatus.FAILED and 
                test_result.retry_count < max_retries):
                retryable.append(TestDefinition(
                    scenario_id=test_result.scenario_id,
                    constitution_id=test_result.constitution_id,
                    model_id=test_result.model_id
                ))
        return retryable
    
    def mark_test_in_progress(self, test_id: str) -> None:
        """Mark a test as currently running"""
        if test_id in self.test_registry:
            previous_status = self.test_registry[test_id].status
            self.test_registry[test_id].status = TestStatus.IN_PROGRESS
            self.test_registry[test_id].timestamp = datetime.now().isoformat()

            # Decrement pending count when moving from PENDING to IN_PROGRESS
            if previous_status == TestStatus.PENDING:
                self.experiment_state.pending_count -= 1
                self.experiment_state.updated_at = datetime.now().isoformat()
                self._save_experiment_state()

            self._save_test_registry()
    
    def mark_test_completed(self, test_id: str, result_data: Dict) -> None:
        """Mark a test as completed and save result"""
        if test_id in self.test_registry:
            # Get test info to check if this was a retry
            test_result = self.test_registry[test_id]
            was_retry = test_result.retry_count > 0

            # Update registry
            test_result.status = TestStatus.COMPLETED
            test_result.result_data = result_data
            test_result.timestamp = datetime.now().isoformat()

            # Save individual result file
            result_file = self.results_dir / f"{test_id}.json"
            with open(result_file, 'w') as f:
                json.dump(result_data, f, indent=2)

            # Update experiment state
            self.experiment_state.completed_count += 1

            # If this was a retry (test had previously failed), decrement failed count
            if was_retry:
                self.experiment_state.failed_count -= 1

            self.experiment_state.updated_at = datetime.now().isoformat()

            self._save_state()
            print(f"✅ Completed: {test_id}")
    
    def mark_test_failed(self, test_id: str, error_message: str) -> None:
        """Mark a test as failed"""
        if test_id in self.test_registry:
            test_result = self.test_registry[test_id]
            test_result.status = TestStatus.FAILED
            test_result.error_message = error_message
            test_result.retry_count += 1
            test_result.timestamp = datetime.now().isoformat()

            # Update experiment state
            # Only increment failed_count on first failure
            # pending_count was already decremented when test went PENDING → IN_PROGRESS
            if test_result.retry_count == 1:
                self.experiment_state.failed_count += 1

            self.experiment_state.updated_at = datetime.now().isoformat()

            self._save_state()
            print(f"❌ Failed: {test_id} (retry {test_result.retry_count})")
    
    def test_exists(self, test_id: str) -> bool:
        """Check if a test has been completed"""
        return (test_id in self.test_registry and 
                self.test_registry[test_id].status == TestStatus.COMPLETED)
    
    def get_progress_summary(self) -> Dict:
        """Get current experiment progress"""
        if not self.experiment_state:
            return {"status": "No active experiment"}
        
        return {
            "experiment_id": self.experiment_state.experiment_id,
            "status": self.experiment_state.status,
            "progress": {
                "total": self.experiment_state.total_tests,
                "completed": self.experiment_state.completed_count,
                "failed": self.experiment_state.failed_count,
                "pending": self.experiment_state.pending_count,
                "completion_rate": f"{(self.experiment_state.completed_count / self.experiment_state.total_tests * 100):.1f}%"
            },
            "created_at": self.experiment_state.created_at,
            "updated_at": self.experiment_state.updated_at
        }
    
    def _generate_test_combinations(
        self, 
        scenarios: List[Scenario], 
        constitutions: List[Constitution], 
        models: List[Dict]
    ) -> List[TestDefinition]:
        """Generate all test combinations"""
        combinations = []
        for scenario in scenarios:
            for constitution in constitutions:
                for model in models:
                    combinations.append(TestDefinition(
                        scenario_id=scenario.id,
                        constitution_id=constitution.id,
                        model_id=model['id']
                    ))
        return combinations
    
    def _load_experiment_state(self) -> Optional[ExperimentState]:
        """Load experiment state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return ExperimentState(**data)
            except Exception as e:
                print(f"Warning: Could not load experiment state: {e}")
        return None
    
    def _load_test_registry(self) -> Dict[str, TestResult]:
        """Load test registry from file"""
        if self.test_registry_file.exists():
            try:
                with open(self.test_registry_file, 'r') as f:
                    data = json.load(f)
                registry = {}
                for test_id, test_data in data.items():
                    test_data['status'] = TestStatus(test_data['status'])
                    registry[test_id] = TestResult(**test_data)
                return registry
            except Exception as e:
                print(f"Warning: Could not load test registry: {e}")
        return {}
    
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
        """Save test registry to file"""
        if self.test_registry:
            # Convert to serializable format
            serializable_registry = {}
            for test_id, test_result in self.test_registry.items():
                test_dict = asdict(test_result)
                test_dict['status'] = test_result.status.value  # Convert enum to string
                serializable_registry[test_id] = test_dict
            
            with open(self.test_registry_file, 'w') as f:
                json.dump(serializable_registry, f, indent=2)