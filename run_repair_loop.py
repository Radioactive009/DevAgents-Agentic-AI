
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, TypeVar

from src.audit_logger import AuditLogger
from src.blackboard import Blackboard
from src.debugging_agent import diagnose_failure
from src.models import ArchitecturePlan, ProjectRequest
from src.patch_applier import apply_patch
from src.patch_validator import validate_patch
from src.repair_agent import propose_repair
from src.testing_agent import run_project_tests
from src.trace_context import TraceContext


MAX_REPAIR_ATTEMPTS = 3
AUDIT_LOG_PATH = Path("logs/devagents_audit.jsonl")

T = TypeVar("T")


def _workflow_duration(started_at: float) -> float:
    """Calculate total elapsed workflow time in seconds."""
    return round(perf_counter() - started_at, 6)


def _safe_audit_event(
    logger: AuditLogger,
    *,
    task_id: str,
    trace_id: str,
    event_type: str,
    stage: str,
    status: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Write an audit event without hiding the original workflow error."""
    event_details = dict(details or {})
    event_details["trace_id"] = trace_id

    try:
        logger.log_event(
            task_id=task_id,
            event_type=event_type,
            stage=stage,
            status=status,
            details=event_details,
        )
    except Exception as exc:
        print(f"Warning: audit logging failed for {event_type}: {exc}")


def _run_timed(
    trace: TraceContext,
    stage: str,
    operation: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> tuple[T, float]:
    """Run an operation and return its result and duration."""
    with trace.measure(stage) as timing:
        result = operation(*args, **kwargs)

    return result, float(timing["duration_seconds"])


def _print_attempt_history(
    attempt_history: list[dict[str, Any]],
) -> None:
    """Print a compact summary of repair attempts."""
    print("\n=== REPAIR ATTEMPT HISTORY ===")

    if not attempt_history:
        print("No repair attempts were needed.")
        return

    for attempt in attempt_history:
        print(
            f"Attempt {attempt['attempt']}: "
            f"status={attempt['status']}, "
            f"timings={attempt.get('timings', {})}"
        )


def create_demo_workflow() -> tuple[Blackboard, Path, list[str]]:
    """Prepare the existing Todo API for the repair-loop demonstration."""
    task_id = "6d4515a7-eb77-45c5-ae7a-cd7d14e7bd55"
    workspace = (Path("generated_projects") / task_id).resolve()

    if not workspace.is_dir():
        raise FileNotFoundError(
            f"Demo workspace does not exist: {workspace}"
        )

    request = ProjectRequest(
        project_name="Todo API",
        description=(
            "Build a Python REST API for creating, listing, "
            "updating, and deleting todo tasks."
        ),
        language="Python",
        features=[
            "Create a task",
            "List all tasks",
            "Update a task",
            "Delete a task",
        ],
        acceptance_criteria=[
            "Tasks have an ID, title, and completion status.",
            "Creating a task requires a non-empty title.",
            "Tasks can be listed, updated, and deleted.",
        ],
    )

    plan = ArchitecturePlan(
        project_name="Todo API",
        summary="A FastAPI Todo API with an in-memory task store.",
        components=[
            "FastAPI endpoints",
            "Pydantic models",
            "In-memory store",
            "Pytest tests",
        ],
        proposed_files=[
            "app.py",
            "models.py",
            "store.py",
            "tests/test_api.py",
            "requirements.txt",
        ],
        implementation_steps=[
            "Define models",
            "Implement the store",
            "Add API endpoints",
            "Write tests",
        ],
        acceptance_criteria=[
            "Tasks have an ID, title, and completion status.",
            "Creating a task requires a non-empty title.",
            "Tasks can be listed, updated, and deleted.",
        ],
        risks=[],
    )

    code_files = [
        "app.py",
        "models.py",
        "store.py",
        "tests/test_api.py",
        "requirements.txt",
    ]

    blackboard = Blackboard(task_id=task_id, request=request)
    blackboard.update_architecture(plan)
    blackboard.record_code_files(code_files)

    return blackboard, workspace, code_files


def main() -> None:
    workflow_started_at = perf_counter()

    blackboard, workspace, code_files = create_demo_workflow()
    task_id = blackboard.get_state().task_id

    logger = AuditLogger(AUDIT_LOG_PATH)
    trace = TraceContext(task_id)
    attempt_history: list[dict[str, Any]] = []

    print(f"Workflow trace ID: {trace.trace_id}")

    _safe_audit_event(
        logger,
        task_id=task_id,
        trace_id=trace.trace_id,
        event_type="workflow_started",
        stage="initialization",
        status="started",
        details={
            "workspace": workspace.name,
            "max_repair_attempts": MAX_REPAIR_ATTEMPTS,
        },
    )

    try:
        print("\n=== INITIAL TEST RUN ===")

        _safe_audit_event(
            logger,
            task_id=task_id,
            trace_id=trace.trace_id,
            event_type="test_run_started",
            stage="initial_testing",
            status="started",
        )

        initial_result, initial_duration = _run_timed(
            trace,
            "initial_testing",
            run_project_tests,
            workspace,
        )

        blackboard.record_test_result(initial_result)

        _safe_audit_event(
            logger,
            task_id=task_id,
            trace_id=trace.trace_id,
            event_type="test_run_completed",
            stage="initial_testing",
            status="passed" if initial_result.failed == 0 else "failed",
            details={
                "passed": initial_result.passed,
                "failed": initial_result.failed,
                "summary": initial_result.summary,
                "duration_seconds": initial_duration,
            },
        )

        print(initial_result.model_dump_json(indent=2))

        if initial_result.failed == 0:
            print("\nAll tests passed. No repair was needed.")
        else:
            for attempt_number in range(1, MAX_REPAIR_ATTEMPTS + 1):
                current_attempt: dict[str, Any] = {
                    "attempt": attempt_number,
                    "status": "started",
                    "timings": {},
                }
                attempt_history.append(current_attempt)

                print(f"\n=== REPAIR ATTEMPT {attempt_number} ===")

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace.trace_id,
                    event_type="repair_attempt_started",
                    stage="repair",
                    status="started",
                    details={"attempt": attempt_number},
                )

                state = blackboard.get_state()
                test_result = state.test_result

                if test_result is None or test_result.failed == 0:
                    current_attempt["status"] = "skipped"
                    current_attempt["reason"] = (
                        "No failing test result available."
                    )
                    break

                debug_report, debug_duration = _run_timed(
                    trace,
                    "debugging",
                    diagnose_failure,
                    test_result,
                    code_files,
                    workspace,
                )
                current_attempt["timings"]["debugging"] = debug_duration

                if debug_report is None:
                    current_attempt["status"] = "failed"
                    current_attempt["reason"] = (
                        "Debugger did not produce a report."
                    )
                    break

                blackboard.record_debug_report(debug_report)

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace.trace_id,
                    event_type="debug_report_created",
                    stage="debugging",
                    status="success",
                    details={
                        "attempt": attempt_number,
                        "severity": debug_report.severity,
                        "affected_files": debug_report.affected_files,
                        "duration_seconds": debug_duration,
                    },
                )

                patch, proposal_duration = _run_timed(
                    trace,
                    "repair_proposal",
                    propose_repair,
                    debug_report,
                    workspace,
                    code_files,
                )
                current_attempt["timings"]["repair_proposal"] = (
                    proposal_duration
                )

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace.trace_id,
                    event_type="patch_proposed",
                    stage="repair_proposal",
                    status="success",
                    details={
                        "attempt": attempt_number,
                        "path": patch.path,
                        "duration_seconds": proposal_duration,
                    },
                )

                _, validation_duration = _run_timed(
                    trace,
                    "patch_validation",
                    validate_patch,
                    patch,
                    code_files,
                )
                current_attempt["timings"]["patch_validation"] = (
                    validation_duration
                )

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace.trace_id,
                    event_type="patch_validated",
                    stage="patch_validation",
                    status="success",
                    details={
                        "attempt": attempt_number,
                        "path": patch.path,
                        "duration_seconds": validation_duration,
                    },
                )

                _, application_duration = _run_timed(
                    trace,
                    "patch_application",
                    apply_patch,
                    workspace,
                    patch,
                    code_files,
                )
                current_attempt["timings"]["patch_application"] = (
                    application_duration
                )

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace.trace_id,
                    event_type="patch_applied",
                    stage="patch_application",
                    status="success",
                    details={
                        "attempt": attempt_number,
                        "path": patch.path,
                        "duration_seconds": application_duration,
                    },
                )

                new_result, retest_duration = _run_timed(
                    trace,
                    "repair_retesting",
                    run_project_tests,
                    workspace,
                )
                current_attempt["timings"]["retesting"] = retest_duration

                blackboard.record_test_result(new_result)

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace.trace_id,
                    event_type="repair_retest_completed",
                    stage="repair_retesting",
                    status="passed" if new_result.failed == 0 else "failed",
                    details={
                        "attempt": attempt_number,
                        "passed": new_result.passed,
                        "failed": new_result.failed,
                        "summary": new_result.summary,
                        "duration_seconds": retest_duration,
                    },
                )

                print(new_result.model_dump_json(indent=2))

                if new_result.failed == 0:
                    current_attempt["status"] = "success"
                    print(f"Repair attempt {attempt_number} succeeded.")
                    break

                current_attempt["status"] = "failed"
                print(
                    f"Repair attempt {attempt_number} did not fix all tests."
                )

        _print_attempt_history(attempt_history)

        final_state = blackboard.get_state()
        final_result = final_state.test_result
        success = final_result is not None and final_result.failed == 0
        total_duration = _workflow_duration(workflow_started_at)

        _safe_audit_event(
            logger,
            task_id=task_id,
            trace_id=trace.trace_id,
            event_type="workflow_completed",
            stage="finalization",
            status="success" if success else "failed",
            details={
                "repair_attempts": len(attempt_history),
                "duration_seconds": total_duration,
                "passed": final_result.passed if final_result else 0,
                "failed": final_result.failed if final_result else 0,
            },
        )

        print("\n=== FINAL BLACKBOARD STATE ===")
        print(final_state.model_dump_json(indent=2))
        print(f"\nTotal workflow duration: {total_duration:.6f} seconds")
        print(
            "Final outcome: "
            + ("all tests passed." if success else "some tests are still failing.")
        )

    except Exception as exc:
        total_duration = _workflow_duration(workflow_started_at)

        _safe_audit_event(
            logger,
            task_id=task_id,
            trace_id=trace.trace_id,
            event_type="workflow_error",
            stage="workflow",
            status="error",
            details={
                "error_type": type(exc).__name__,
                "error": str(exc),
                "duration_seconds": total_duration,
            },
        )

        try:
            blackboard.record_error(f"{type(exc).__name__}: {exc}")
        except Exception as state_exc:
            print(f"Warning: could not update workflow state: {state_exc}")

        print(f"\nWorkflow failed after {total_duration:.6f} seconds.")
        raise


if __name__ == "__main__":
    main()
