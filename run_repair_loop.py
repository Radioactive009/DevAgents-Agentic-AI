
import json
from pathlib import Path
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

AUDIT_LOG_PATH = (
    Path(__file__).resolve().parent
    / "logs"
    / "devagents_audit.jsonl"
)

T = TypeVar("T")


def create_demo_workflow():
    task_id = "6d4515a7-eb77-45c5-ae7a-cd7d14e7bd55"

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
        acceptance_criteria=request.acceptance_criteria,
    )

    blackboard = Blackboard(task_id=task_id, request=request)
    blackboard.update_architecture(plan)

    generated_files = [
        "app.py",
        "models.py",
        "store.py",
        "tests/test_api.py",
        "requirements.txt",
    ]
    blackboard.record_code_files(generated_files)

    workspace = (
        Path(__file__).resolve().parent
        / "generated_projects"
        / task_id
    )

    return blackboard, workspace


def _print_attempt_history(attempts: list[dict[str, Any]]) -> None:
    print("\n=== REPAIR ATTEMPT HISTORY ===")
    print(json.dumps(attempts, indent=2, default=str))


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
    """Record a trace-linked audit event without masking workflow errors."""
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
    except Exception as audit_error:
        print(
            "WARNING: Audit logging failed:",
            f"{type(audit_error).__name__}: {audit_error}",
        )


def _run_timed(
    trace: TraceContext,
    stage: str,
    operation: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> tuple[T, float]:
    """Run an operation and return its result and elapsed seconds."""
    with trace.measure(stage) as timing:
        result = operation(*args, **kwargs)

    return result, float(timing["duration_seconds"])


def main():
    blackboard, workspace = create_demo_workflow()
    task_id = blackboard.get_state().task_id
    logger = AuditLogger(AUDIT_LOG_PATH)

    trace = TraceContext(task_id)
    trace_id = trace.trace_id

    attempts: list[dict[str, Any]] = []
    current_attempt = None

    print(f"Workflow trace ID: {trace_id}")

    _safe_audit_event(
        logger,
        task_id=task_id,
        trace_id=trace_id,
        event_type="workflow_started",
        stage="initialization",
        status="started",
        details={
            "workspace": workspace.name,
            "max_repair_attempts": MAX_REPAIR_ATTEMPTS,
        },
    )

    try:
        print("=== INITIAL TEST RUN ===")

        _safe_audit_event(
            logger,
            task_id=task_id,
            trace_id=trace_id,
            event_type="test_run_started",
            stage="initial_testing",
            status="started",
        )

        result, duration = _run_timed(
            trace,
            "initial_testing",
            run_project_tests,
            workspace,
        )
        blackboard.record_test_result(result)

        _safe_audit_event(
            logger,
            task_id=task_id,
            trace_id=trace_id,
            event_type="test_run_completed",
            stage="initial_testing",
            status="passed" if result.failed == 0 else "failed",
            details={
                "passed": result.passed,
                "failed": result.failed,
                "summary": result.summary,
                "duration_seconds": duration,
            },
        )

        print(result.model_dump_json(indent=2))

        if result.failed == 0:
            print("\nAll tests passed. No repair was needed.")

            _safe_audit_event(
                logger,
                task_id=task_id,
                trace_id=trace_id,
                event_type="workflow_completed",
                stage="finalization",
                status="success",
                details={
                    "repair_attempts": 0,
                    "duration_seconds": None,
                },
            )

        else:
            for attempt_number in range(
                1,
                MAX_REPAIR_ATTEMPTS + 1,
            ):
                state = blackboard.get_state()

                if (
                    state.test_result is None
                    or state.test_result.failed == 0
                ):
                    break

                current_attempt = {
                    "attempt": attempt_number,
                    "trace_id": trace_id,
                    "stage": "diagnosis",
                    "status": "in_progress",
                    "patch": None,
                    "application": None,
                    "test_result": None,
                    "timings": {},
                    "error": None,
                }
                attempts.append(current_attempt)

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="repair_attempt_started",
                    stage="diagnosis",
                    status="started",
                    details={"attempt": attempt_number},
                )

                print(
                    f"\n=== REPAIR ATTEMPT "
                    f"{attempt_number}/{MAX_REPAIR_ATTEMPTS} ==="
                )

                # Step 1: Diagnose the test failures.
                report, duration = _run_timed(
                    trace,
                    "debugging",
                    diagnose_failure,
                    test_result=state.test_result,
                    code_files=state.code_files,
                    workspace=workspace,
                )
                current_attempt["timings"]["debugging_seconds"] = duration

                if report is None:
                    raise RuntimeError(
                        "Tests failed, but the Debugging Agent "
                        "returned no diagnosis."
                    )

                blackboard.record_debug_report(report)
                current_attempt["debug_report"] = report.model_dump()
                current_attempt["stage"] = "repair_proposal"

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="diagnosis_completed",
                    stage="debugging",
                    status="success",
                    details={
                        "attempt": attempt_number,
                        "severity": report.severity,
                        "confidence": report.confidence,
                        "affected_files": report.affected_files,
                        "duration_seconds": duration,
                    },
                )

                print("\nDebug report:")
                print(report.model_dump_json(indent=2))

                # Step 2: Ask the Repair Agent for a patch.
                patch, duration = _run_timed(
                    trace,
                    "repair_proposal",
                    propose_repair,
                    debug_report=report,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )
                current_attempt["timings"]["repair_proposal_seconds"] = (
                    duration
                )

                current_attempt["patch"] = {
                    "file_path": patch.file_path,
                    "explanation": patch.explanation,
                }
                current_attempt["stage"] = "patch_validation"

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="repair_proposed",
                    stage="repair_proposal",
                    status="success",
                    details={
                        "attempt": attempt_number,
                        "file_path": patch.file_path,
                        "duration_seconds": duration,
                    },
                )

                print("\nProposed patch:")
                print(patch.model_dump_json(indent=2))

                # Step 3: Validate immediately before application.
                _, duration = _run_timed(
                    trace,
                    "patch_validation",
                    validate_patch,
                    patch=patch,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )
                current_attempt["timings"]["patch_validation_seconds"] = (
                    duration
                )

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="patch_validated",
                    stage="patch_validation",
                    status="success",
                    details={
                        "attempt": attempt_number,
                        "file_path": patch.file_path,
                        "duration_seconds": duration,
                    },
                )

                current_attempt["stage"] = "patch_application"

                # Step 4: Apply the patch and preserve a backup.
                application_result, duration = _run_timed(
                    trace,
                    "patch_application",
                    apply_patch,
                    patch=patch,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )
                current_attempt["timings"]["patch_application_seconds"] = (
                    duration
                )

                current_attempt["application"] = application_result
                current_attempt["stage"] = "retesting"

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="patch_applied",
                    stage="patch_application",
                    status="success",
                    details={
                        "attempt": attempt_number,
                        "file_path": patch.file_path,
                        "backup_path": application_result.get(
                            "backup_path"
                        ),
                        "duration_seconds": duration,
                    },
                )

                # Step 5: Rerun tests after the patch.
                print("\nRerunning project tests...")

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="test_run_started",
                    stage="retesting",
                    status="started",
                    details={"attempt": attempt_number},
                )

                result, duration = _run_timed(
                    trace,
                    "retesting",
                    run_project_tests,
                    workspace,
                )
                blackboard.record_test_result(result)

                current_attempt["test_result"] = result.model_dump()
                current_attempt["timings"]["retesting_seconds"] = duration

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="test_run_completed",
                    stage="retesting",
                    status="passed" if result.failed == 0 else "failed",
                    details={
                        "attempt": attempt_number,
                        "passed": result.passed,
                        "failed": result.failed,
                        "summary": result.summary,
                        "duration_seconds": duration,
                    },
                )

                print("\nTest result after repair:")
                print(result.model_dump_json(indent=2))

                if result.failed == 0:
                    current_attempt["status"] = "succeeded"
                    current_attempt["stage"] = "completed"

                    _safe_audit_event(
                        logger,
                        task_id=task_id,
                        trace_id=trace_id,
                        event_type="repair_attempt_completed",
                        stage="repair",
                        status="success",
                        details={
                            "attempt": attempt_number,
                            "timings": current_attempt["timings"],
                        },
                    )

                    print("\nRepair succeeded: all tests now pass.")
                    current_attempt = None
                    break

                current_attempt["status"] = "unsuccessful"
                current_attempt["stage"] = "retesting"

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="repair_attempt_completed",
                    stage="repair",
                    status="unsuccessful",
                    details={
                        "attempt": attempt_number,
                        "remaining_failures": result.failed,
                        "timings": current_attempt["timings"],
                    },
                )

                print(
                    "\nTests still failing; another attempt "
                    "may be needed."
                )

                current_attempt = None

            else:
                print(
                    "\nRepair limit reached. "
                    "The workflow will not attempt further repairs."
                )

                _safe_audit_event(
                    logger,
                    task_id=task_id,
                    trace_id=trace_id,
                    event_type="repair_limit_reached",
                    stage="repair",
                    status="unresolved",
                    details={
                        "max_attempts": MAX_REPAIR_ATTEMPTS,
                    },
                )

            final_state = blackboard.get_state()

            if (
                final_state.test_result
                and final_state.test_result.failed > 0
            ):
                final_status = "unresolved"
            else:
                final_status = "success"

            _safe_audit_event(
                logger,
                task_id=task_id,
                trace_id=trace_id,
                event_type="workflow_completed",
                stage="finalization",
                status=final_status,
                details={
                    "repair_attempts": len(attempts),
                    "passed": (
                        final_state.test_result.passed
                        if final_state.test_result
                        else None
                    ),
                    "failed": (
                        final_state.test_result.failed
                        if final_state.test_result
                        else None
                    ),
                },
            )

        final_state = blackboard.get_state()

        _print_attempt_history(attempts)

        print("\n=== FINAL BLACKBOARD STATE ===")
        print(final_state.model_dump_json(indent=2))

        if (
            final_state.test_result
            and final_state.test_result.failed > 0
        ):
            print("\nFinal outcome: unresolved test failures.")
        elif final_state.test_result:
            print("\nFinal outcome: all tests passed.")

    except Exception as error:
        error_message = f"{type(error).__name__}: {error}"

        if current_attempt is not None:
            current_attempt["status"] = "failed"
            current_attempt["error"] = error_message

        _safe_audit_event(
            logger,
            task_id=task_id,
            trace_id=trace_id,
            event_type="workflow_error",
            stage=(
                current_attempt["stage"]
                if current_attempt is not None
                else "initial_testing"
            ),
            status="failed",
            details={
                "error_type": type(error).__name__,
                "attempt": (
                    current_attempt["attempt"]
                    if current_attempt is not None
                    else None
                ),
            },
        )

        try:
            blackboard.record_error(error_message)
        except Exception as state_error:
            print(
                "WARNING: Could not record error in Blackboard:",
                f"{type(state_error).__name__}: {state_error}",
            )

        print("\nRepair workflow stopped.")
        print("Error:", error_message)

        _print_attempt_history(attempts)

        print("\n=== FINAL BLACKBOARD STATE ===")
        print(blackboard.get_state().model_dump_json(indent=2))

        raise


if __name__ == "__main__":
    main()
