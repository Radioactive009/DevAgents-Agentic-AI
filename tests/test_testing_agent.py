
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.testing_agent import run_project_tests


class TestTestingAgent(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.project_root = Path(self.temp_dir.name)
        self.allowed_root = self.project_root / "generated_projects"
        self.workspace = self.allowed_root / "test-task"
        self.tests_dir = self.workspace / "tests"

        self.tests_dir.mkdir(parents=True)

        (self.tests_dir / "test_example.py").write_text(
            "def test_example():\n    assert True\n",
            encoding="utf-8",
        )

    def test_rejects_workspace_outside_generated_projects(self):
        outside_workspace = self.project_root / "outside"
        outside_workspace.mkdir()

        with self.assertRaises(ValueError):
            run_project_tests(
                outside_workspace,
                allowed_root=self.allowed_root,
            )

    def test_rejects_invalid_timeout(self):
        with self.assertRaises(ValueError):
            run_project_tests(
                self.workspace,
                timeout_seconds=0,
                allowed_root=self.allowed_root,
            )

    def test_rejects_missing_tests_directory(self):
        empty_workspace = self.allowed_root / "empty-task"
        empty_workspace.mkdir(parents=True)

        with self.assertRaises(FileNotFoundError):
            run_project_tests(
                empty_workspace,
                allowed_root=self.allowed_root,
            )

    def test_rejects_no_test_files(self):
        empty_test_workspace = self.allowed_root / "no-tests"
        (empty_test_workspace / "tests").mkdir(parents=True)

        with self.assertRaises(FileNotFoundError):
            run_project_tests(
                empty_test_workspace,
                allowed_root=self.allowed_root,
            )

    def test_parses_successful_pytest_result(self):
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = "12 passed in 0.65s"
        completed.stderr = ""

        with patch(
            "src.testing_agent.subprocess.run",
            return_value=completed,
        ):
            result = run_project_tests(
                self.workspace,
                allowed_root=self.allowed_root,
            )

        self.assertEqual(result.passed, 12)
        self.assertEqual(result.failed, 0)
        self.assertIn("successfully", result.summary)

    def test_parses_failed_pytest_result(self):
        completed = MagicMock()
        completed.returncode = 1
        completed.stdout = "2 failed, 10 passed in 1.20s"
        completed.stderr = ""

        with patch(
            "src.testing_agent.subprocess.run",
            return_value=completed,
        ):
            result = run_project_tests(
                self.workspace,
                allowed_root=self.allowed_root,
            )

        self.assertEqual(result.passed, 10)
        self.assertEqual(result.failed, 2)
        self.assertTrue(result.error_details)

    def test_handles_timeout(self):
        with patch(
            "src.testing_agent.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                cmd="pytest",
                timeout=1,
            ),
        ):
            result = run_project_tests(
                self.workspace,
                allowed_root=self.allowed_root,
            )

        self.assertEqual(result.passed, 0)
        self.assertEqual(result.failed, 1)
        self.assertIn("timed out", result.summary)


if __name__ == "__main__":
    unittest.main()
