
from threading import RLock

from src.models import (
    ArchitecturePlan,
    ProjectRequest,
    ProjectState,
    TestResult,
)


class Blackboard:
    """Shared, in-memory state for DevAgents."""

    def __init__(self, task_id: str, request: ProjectRequest):
        self._lock = RLock()
        self._state = ProjectState(
            task_id=task_id,
            request=request,
        )

    def get_state(self) -> ProjectState:
        """Return a separate copy of the current project state."""
        with self._lock:
            return self._state.model_copy(deep=True)

    def update_architecture(
        self, plan: ArchitecturePlan
    ) -> ProjectState:
        """Save the architecture plan and move the project to coding."""
        with self._lock:
            if plan.project_name != self._state.request.project_name:
                raise ValueError(
                    "Architecture plan project name does not match "
                    "the project request."
                )

            self._state.architecture_plan = plan
            self._state.status = "coding"
            return self._state.model_copy(deep=True)

    def update_status(self, status: str) -> ProjectState:
        """Update the workflow status, validating it through Pydantic."""
        with self._lock:
            self._state.status = status
            return self._state.model_copy(deep=True)

    def record_test_result(
        self, result: TestResult
    ) -> ProjectState:
        """Store test results and move to verification or debugging."""
        with self._lock:
            self._state.test_result = result

            if result.failed > 0:
                self._state.status = "debugging"
            else:
                self._state.status = "verifying"

            return self._state.model_copy(deep=True)

    def record_error(self, error: str) -> ProjectState:
        """Record an error without overwriting previous errors."""
        cleaned_error = error.strip()
        if not cleaned_error:
            raise ValueError("Error message cannot be empty.")

        with self._lock:
            self._state.errors.append(cleaned_error)
            self._state.status = "failed"
            return self._state.model_copy(deep=True)
