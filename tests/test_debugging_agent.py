
import unittest

from pydantic import ValidationError

from src.debugging_agent import DebugReport, diagnose_failure
from src.models import TestResult


class TestDebuggingAgent(unittest.TestCase):

    def test_valid_debug_report(self):
        report = DebugReport(
            diagnosis="The update endpoint returns an incorrect status.",
            root_cause="The endpoint does not handle a missing task.",
            severity="medium",
            affected_files=["app.py"],
            recommended_fixes=[
                "Return HTTP 404 when the task does not exist."
            ],
            confidence=0.9,
            needs_more_information=False,
        )

        self.assertEqual(report.severity, "medium")
        self.assertEqual(report.affected_files, ["app.py"])
        self.assertGreaterEqual(report.confidence, 0.0)
        self.assertLessEqual(report.confidence, 1.0)

    def test_invalid_severity_is_rejected(self):
        with self.assertRaises(ValidationError):
            DebugReport(
                diagnosis="A bug exists.",
                root_cause="Unknown.",
                severity="extreme",
                recommended_fixes=["Inspect the failing endpoint."],
                confidence=0.5,
            )

    def test_invalid_confidence_is_rejected(self):
        with self.assertRaises(ValidationError):
            DebugReport(
                diagnosis="A bug exists.",
                root_cause="Unknown.",
                severity="low",
                recommended_fixes=["Inspect the failing endpoint."],
                confidence=1.5,
            )

    def test_passing_tests_skip_diagnosis(self):
        result = TestResult(
            passed=12,
            failed=0,
            summary="All tests passed.",
        )

        report = diagnose_failure(
            test_result=result,
            code_files=["app.py"],
            workspace=".",
        )

        self.assertIsNone(report)

    def test_failed_tests_require_file_paths(self):
        result = TestResult(
            passed=3,
            failed=1,
            summary="One test failed.",
            error_details=["AssertionError"],
        )

        with self.assertRaises(ValueError):
            diagnose_failure(
                test_result=result,
                code_files=[],
                workspace=".",
            )


if __name__ == "__main__":
    unittest.main()
