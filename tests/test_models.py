
import unittest

from pydantic import ValidationError

from src.models import ProjectRequest, ProjectState, TestResult


class TestProjectModels(unittest.TestCase):

    def setUp(self):
        self.request = ProjectRequest(
            project_name="Todo API",
            description="Build a Python API for managing tasks.",
            language="Python",
            features=["Create tasks", "List tasks", "Delete tasks"],
            acceptance_criteria=["All API tests pass"],
        )

    def test_valid_project_request(self):
        self.assertEqual(self.request.project_name, "Todo API")
        self.assertEqual(len(self.request.features), 3)

    def test_invalid_project_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProjectRequest(
                project_name="AB",
                description="Build a Python API for tasks.",
                language="Python",
                features=["Create tasks"],
            )

    def test_invalid_iteration_is_rejected(self):
        with self.assertRaises(ValidationError):
            ProjectState(
                task_id="task-001",
                request=self.request,
                iteration=11,
            )

    def test_project_state_defaults(self):
        state = ProjectState(
            task_id="task-001",
            request=self.request,
        )

        self.assertEqual(state.status, "planning")
        self.assertEqual(state.iteration, 0)
        self.assertEqual(state.code_files, [])
        self.assertIsNone(state.test_result)

    def test_test_result(self):
        result = TestResult(
            passed=8,
            failed=2,
            summary="Two tests failed.",
            error_details=["Assertion failed", "Missing response field"],
        )

        self.assertEqual(result.passed, 8)
        self.assertEqual(result.failed, 2)
        self.assertEqual(len(result.error_details), 2)

    def test_state_can_be_exported_as_json(self):
        state = ProjectState(
            task_id="task-001",
            request=self.request,
        )

        exported = state.model_dump_json()
        self.assertIn('"task_id":"task-001"', exported)
        self.assertIn('"status":"planning"', exported)


if __name__ == "__main__":
    unittest.main(verbosity=2)
