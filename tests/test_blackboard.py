
import unittest

from pydantic import ValidationError

from src.blackboard import Blackboard
from src.models import ArchitecturePlan, ProjectRequest, TestResult


def make_request():
    return ProjectRequest(
        project_name="Todo API",
        description=(
            "Build a REST API for creating, listing, updating, "
            "and deleting tasks."
        ),
        language="Python",
        features=[
            "Create tasks",
            "List tasks",
            "Update tasks",
            "Delete tasks",
        ],
        acceptance_criteria=[
            "All task operations work",
            "Invalid requests return errors",
        ],
    )


def make_plan():
    return ArchitecturePlan(
        project_name="Todo API",
        summary="A small REST API for managing tasks.",
        components=["HTTP API", "Task model", "Test suite"],
        proposed_files=[
            "app.py",
            "models.py",
            "tests/test_app.py",
            "run.py",
        ],
        implementation_steps=[
            "Define the task model",
            "Implement the API routes",
            "Validate incoming requests",
            "Test the endpoints",
        ],
        acceptance_criteria=[
            "Task operations work",
            "Invalid requests return errors",
            "Tests cover the endpoints",
        ],
    )


class TestBlackboard(unittest.TestCase):

    def setUp(self):
        self.board = Blackboard("task-001", make_request())

    def test_initial_state(self):
        state = self.board.get_state()

        self.assertEqual(state.task_id, "task-001")
        self.assertEqual(state.status, "planning")
        self.assertIsNone(state.architecture_plan)
        self.assertEqual(state.errors, [])


    def test_record_code_files(self):
        self.board.update_architecture(make_plan())

        state = self.board.record_code_files(
            ["main.py", "tests/test_main.py"]
        )

        self.assertEqual(
            state.code_files,
            ["main.py", "tests/test_main.py"],
        )

    def test_record_code_files_rejects_duplicates(self):
        self.board.update_architecture(make_plan())

        with self.assertRaises(ValueError):
            self.board.record_code_files(
                ["main.py", "main.py"]
            )

    def test_record_code_files_requires_coding_status(self):
        with self.assertRaises(ValueError):
            self.board.record_code_files(["main.py"])


    def test_store_architecture_plan(self):
        state = self.board.update_architecture(make_plan())

        self.assertEqual(state.status, "coding")
        self.assertEqual(
            state.architecture_plan.project_name, "Todo API"
        )

    def test_reject_plan_for_another_project(self):
        plan = make_plan()
        plan.project_name = "Different Project"

        with self.assertRaises(ValueError):
            self.board.update_architecture(plan)

    def test_update_status(self):
        state = self.board.update_status("testing")
        self.assertEqual(state.status, "testing")

        with self.assertRaises(ValidationError):
            self.board.update_status("unknown_status")

    def test_failed_tests_move_to_debugging(self):
        result = TestResult(
            passed=3,
            failed=2,
            summary="Two tests failed.",
            error_details=["Assertion failed"],
        )

        state = self.board.record_test_result(result)

        self.assertEqual(state.status, "debugging")
        self.assertEqual(state.test_result.failed, 2)

    def test_passing_tests_move_to_verifying(self):
        result = TestResult(
            passed=5,
            failed=0,
            summary="All tests passed.",
        )

        state = self.board.record_test_result(result)

        self.assertEqual(state.status, "verifying")

    def test_record_error(self):
        state = self.board.record_error("API generation failed")

        self.assertEqual(state.status, "failed")
        self.assertEqual(state.errors, ["API generation failed"])

    def test_returned_state_is_a_copy(self):
        state = self.board.get_state()
        state.errors.append("External modification")

        actual_state = self.board.get_state()
        self.assertEqual(actual_state.errors, [])

    def test_reject_empty_error(self):
        with self.assertRaises(ValueError):
            self.board.record_error("   ")


if __name__ == "__main__":
    unittest.main()
