
import pytest

from src.blackboard import Blackboard
from src.models import (
    ArchitecturePlan,
    DebugReport,
    ProjectRequest,
    TestResult,
)


def create_debugging_blackboard():
    request = ProjectRequest(
        project_name="Task Tracker",
        description="A simple task tracker with create and list operations.",
        language="Python",
        features=["Create tasks", "List tasks"],
        acceptance_criteria=["Tasks can be created and listed."],
    )

    blackboard = Blackboard(
        task_id="test-task-001",
        request=request,
    )

    plan = ArchitecturePlan(
        project_name="Task Tracker",
        summary="A small task tracking application.",
        components=["Application", "Task storage"],
        proposed_files=["app.py", "store.py", "tests/test_app.py"],
        implementation_steps=["Implement storage", "Implement application"],
        acceptance_criteria=["Tasks can be created and listed."],
    )

    blackboard.update_architecture(plan)

    blackboard.record_code_files(
        ["app.py", "store.py", "tests/test_app.py"]
    )

    blackboard.record_test_result(
        TestResult(
            passed=2,
            failed=1,
            summary="Two tests passed and one failed.",
            error_details=["AssertionError: expected 200, got 500"],
        )
    )

    return blackboard


def create_debug_report():
    return DebugReport(
        diagnosis="A task creation request fails.",
        root_cause="The application may not handle invalid input correctly.",
        severity="medium",
        affected_files=["app.py", "tests/test_app.py"],
        recommended_fixes=[
            "Inspect the task creation handler.",
            "Add a regression test for invalid input.",
        ],
        confidence=0.75,
        needs_more_information=False,
    )


def test_record_debug_report_saves_report():
    blackboard = create_debugging_blackboard()
    report = create_debug_report()

    state = blackboard.record_debug_report(report)

    assert state.debug_report == report
    assert state.status == "debugging"


def test_record_debug_report_does_not_modify_returned_state():
    blackboard = create_debugging_blackboard()

    returned_state = blackboard.record_debug_report(
        create_debug_report()
    )
    returned_state.debug_report.diagnosis = "Changed outside the Blackboard"

    actual_state = blackboard.get_state()

    assert actual_state.debug_report.diagnosis == (
        "A task creation request fails."
    )


def test_record_debug_report_rejects_unregistered_file():
    blackboard = create_debugging_blackboard()

    report = create_debug_report()
    report.affected_files = ["secret.py"]

    with pytest.raises(ValueError, match="files not recorded"):
        blackboard.record_debug_report(report)


def test_record_debug_report_rejects_when_not_debugging():
    blackboard = create_debugging_blackboard()

    blackboard.record_test_result(
        TestResult(
            passed=3,
            failed=0,
            summary="All tests passed.",
        )
    )

    with pytest.raises(ValueError, match="only be recorded while debugging"):
        blackboard.record_debug_report(create_debug_report())
