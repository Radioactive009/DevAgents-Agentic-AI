
from threading import RLock

from src.models import (
    ArchitecturePlan,
    ProjectRequest,
    ProjectState,
    TestResult,
)


class Blackboard:
    def __init__(self, task_id: str, request: ProjectRequest):
        self._lock = RLock()
        self._state = ProjectState(
            task_id=task_id,
            request=request,
        )

    def get_state(self) -> ProjectState:
        with self._lock:
            return self._state.model_copy(deep=True)

    def update_architecture(
        self,
        plan: ArchitecturePlan,
    ) -> ProjectState:
        with self._lock:
            if plan.project_name != self._state.request.project_name:
                raise ValueError(
                    "Architecture plan project name does not match "
                    "the project request."
                )

            self._state.architecture_plan = plan
            self._state.status = "coding"

            return self._state.model_copy(deep=True)

    def record_code_files(
        self,
        file_paths: list[str],
    ) -> ProjectState:
        if not file_paths:
            raise ValueError(
                "At least one generated file path is required."
            )

        cleaned_paths = [
            path.strip().replace("\\", "/")
            for path in file_paths
        ]

        if any(not path for path in cleaned_paths):
            raise ValueError("File paths cannot be empty.")

        if len(cleaned_paths) != len(set(cleaned_paths)):
            raise ValueError("Duplicate file paths are not allowed.")

        with self._lock:
            if self._state.status not in ("coding",):
                raise ValueError(
                    "Code files can only be recorded while coding."
                )

            self._state.code_files = cleaned_paths

            return self._state.model_copy(deep=True)

    def update_status(self, status: str) -> ProjectState:
        with self._lock:
            self._state.status = status
            return self._state.model_copy(deep=True)

    def record_test_result(
        self,
        result: TestResult,
    ) -> ProjectState:
        with self._lock:
            self._state.test_result = result

            if result.failed > 0:
                self._state.status = "debugging"
            else:
                self._state.status = "verifying"

            return self._state.model_copy(deep=True)

    def record_error(self, error: str) -> ProjectState:
        cleaned_error = error.strip()

        if not cleaned_error:
            raise ValueError("Error message cannot be empty.")

        with self._lock:
            self._state.errors.append(cleaned_error)
            self._state.status = "failed"

            return self._state.model_copy(deep=True)
