
from pathlib import Path
from unittest.mock import Mock

import pytest

import run_repair_loop
from src.blackboard import Blackboard
from src.models import (
    ArchitecturePlan,
    DebugReport,
    ProjectRequest,
    TestResult,
)
from src.patch_validator import CodePatch


def create_test_workflow(workspace: Path):
    """Create an isolated Blackboard and temporary project workspace."""
    request = ProjectRequest(
        project_name="Repair Test App",
        description="A small Python application used to test automatic repair.",
        language="Python",
        features=["Calculate a value"],
        acceptance_criteria=["The calculation returns the expected value."],
    )

    plan = ArchitecturePlan(
        project_name="Repair Test App",
        summary="A small Python application.",
        components=["Application module", "Pytest tests"],
        proposed_files=["app.py"],
        implementation_steps=["Implement the calculation"],
        acceptance_criteria=request.acceptance_criteria,
    )

    blackboard = Blackboard(
        task_id="repair-integration-test",
        request=request,
    )
    blackboard.update_architecture(plan)
    blackboard.record_code_files(["app.py"])

    (workspace / "app.py").write_text(
        "def calculate():\n    return 1\n",
        encoding="utf-8",
    )

    return blackboard, workspace


def make_failure():
    return TestResult(
        passed=0,
        failed=1,
        summary="One test failed.",
        error_details=["Expected 2 but received 1."],
    )


def make_success():
    return TestResult(
        passed=1,
        failed=0,
        summary="All tests passed.",
        error_details=[],
    )


def make_debug_report():
    return DebugReport(
        diagnosis="The function returns an incorrect value.",
        root_cause="The return value does not match the expected result.",
        severity="low",
        affected_files=["app.py"],
        recommended_fixes=["Correct the return value."],
        confidence=0.95,
        needs_more_information=False,
    )


def make_patch(original_text, replacement_text):
    return CodePatch(
        file_path="app.py",
        original_text=original_text,
        replacement_text=replacement_text,
        explanation="Correct the function's return value.",
    )


def install_test_workflow(monkeypatch, blackboard, workspace):
    """Prevent tests from using the real demo workspace."""
    monkeypatch.setattr(
        run_repair_loop,
        "create_demo_workflow",
        lambda: (blackboard, workspace),
    )


def test_repair_loop_skips_repair_when_initial_tests_pass(
    monkeypatch,
    tmp_path,
    capsys,
):
    blackboard, workspace = create_test_workflow(tmp_path)
    install_test_workflow(monkeypatch, blackboard, workspace)

    run_tests = Mock(return_value=make_success())
    diagnose = Mock()
    propose = Mock()

    monkeypatch.setattr(run_repair_loop, "run_project_tests", run_tests)
    monkeypatch.setattr(run_repair_loop, "diagnose_failure", diagnose)
    monkeypatch.setattr(run_repair_loop, "propose_repair", propose)

    run_repair_loop.main()

    assert run_tests.call_count == 1
    diagnose.assert_not_called()
    propose.assert_not_called()

    final_state = blackboard.get_state()
    assert final_state.status == "verifying"
    assert final_state.test_result.failed == 0

    assert "No repair was needed" in capsys.readouterr().out


def test_repair_loop_applies_patch_and_passes_retest(
    monkeypatch,
    tmp_path,
    capsys,
):
    blackboard, workspace = create_test_workflow(tmp_path)
    install_test_workflow(monkeypatch, blackboard, workspace)

    run_tests = Mock(
        side_effect=[make_failure(), make_success()]
    )
    diagnose = Mock(return_value=make_debug_report())
    propose = Mock(
        return_value=make_patch("return 1", "return 2")
    )

    monkeypatch.setattr(run_repair_loop, "run_project_tests", run_tests)
    monkeypatch.setattr(run_repair_loop, "diagnose_failure", diagnose)
    monkeypatch.setattr(run_repair_loop, "propose_repair", propose)

    run_repair_loop.main()

    # One initial test run and one retest after applying the patch.
    assert run_tests.call_count == 2
    diagnose.assert_called_once()
    propose.assert_called_once()

    # The real patch applier should update the temporary file.
    assert (workspace / "app.py").read_text(
        encoding="utf-8"
    ) == "def calculate():\n    return 2\n"

    # The original file must be preserved in a backup.
    assert (workspace / "app.py.bak").read_text(
        encoding="utf-8"
    ) == "def calculate():\n    return 1\n"

    final_state = blackboard.get_state()
    assert final_state.status == "verifying"
    assert final_state.test_result.failed == 0
    assert final_state.errors == []

    output = capsys.readouterr().out
    assert "Repair succeeded: all tests now pass." in output
    assert "Final outcome: all tests passed." in output


def test_repair_loop_stops_after_maximum_attempts(
    monkeypatch,
    tmp_path,
    capsys,
):
    blackboard, workspace = create_test_workflow(tmp_path)
    install_test_workflow(monkeypatch, blackboard, workspace)

    run_tests = Mock(
        side_effect=[
            make_failure(),
            make_failure(),
            make_failure(),
            make_failure(),
        ]
    )

    diagnose = Mock(return_value=make_debug_report())

    propose = Mock(
        side_effect=[
            make_patch("return 1", "return 2"),
            make_patch("return 2", "return 3"),
            make_patch("return 3", "return 4"),
        ]
    )

    monkeypatch.setattr(run_repair_loop, "run_project_tests", run_tests)
    monkeypatch.setattr(run_repair_loop, "diagnose_failure", diagnose)
    monkeypatch.setattr(run_repair_loop, "propose_repair", propose)

    run_repair_loop.main()

    # One initial run plus exactly three repair retests.
    assert run_tests.call_count == 4
    assert diagnose.call_count == run_repair_loop.MAX_REPAIR_ATTEMPTS
    assert propose.call_count == run_repair_loop.MAX_REPAIR_ATTEMPTS

    final_state = blackboard.get_state()
    assert final_state.status == "debugging"
    assert final_state.test_result.failed == 1

    output = capsys.readouterr().out
    assert "Repair limit reached" in output
    assert "Final outcome: unresolved test failures." in output
