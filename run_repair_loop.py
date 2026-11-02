"""
DevAgents Self-Repair Pipeline with Full Requirements 1, 2, 7, 8 & 9 Integration.

Features:
- Req 1: Centralized Blackboard shared-state coordination.
- Req 2: MCP Tool Integration (AST File Parser & SQLite Metadata lookup).
- Req 7: Dual Framework Architecture (Google ADK Architecture Agent + CrewAI Repair Agents).
- Req 8: Security Guardrails (PromptGuard injection/toxic scanner, validation callbacks, prompt variance).
- Req 9: OpenTelemetry distributed tracing with provenance metadata and JSON file export.
"""

import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, TypeVar

from src.adk_architecture_agent import generate_adk_architecture
from src.audit_logger import AuditLogger
from src.blackboard import Blackboard
from src.debugging_agent import diagnose_failure
from src.mcp.client import McpClientBridge
from src.models import ArchitecturePlan, ProjectRequest
from src.observability.tracer import init_tracer
from src.patch_applier import apply_patch
from src.patch_validator import validate_patch
from src.prompts.variance_manager import (
    PromptArchitecture,
    PromptPersona,
    PromptVarianceConfig,
)
from src.repair_agent import propose_repair
from src.security.prompt_guard import PromptGuard
from src.security.validation_callbacks import DataValidationCallback, ToolReturnValidator
from src.testing_agent import run_project_tests
from src.trace_context import TraceContext


MAX_REPAIR_ATTEMPTS = 3
AUDIT_LOG_PATH = Path("logs/devagents_audit.jsonl")
TRACE_LOG_PATH = Path("logs/devagents_traces.jsonl")

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

    # Initialize OpenTelemetry Tracer (Req 9)
    otel_tracer = init_tracer(TRACE_LOG_PATH)

    # Initialize Security Guardrail (Req 8)
    guard = PromptGuard()

    # Initialize MCP Client Bridge (Req 2)
    mcp_client = McpClientBridge()

    # Initialize Validation Callback (Req 8)
    validation_callback = DataValidationCallback()

    blackboard, workspace, code_files = create_demo_workflow()
    task_id = blackboard.get_state().task_id
    project_request = blackboard.get_state().request

    logger = AuditLogger(AUDIT_LOG_PATH)
    trace = TraceContext(task_id)
    attempt_history: list[dict[str, Any]] = []

    print(f"Workflow trace ID: {trace.trace_id}")

    # Root OpenTelemetry Span (Req 9)
    with otel_tracer.start_span(
        name="workflow_execution",
        stage="pipeline",
        framework="dual (google-adk + crewai)",
        input_data=project_request.model_dump_json(),
        attributes={
            "task_id": task_id,
            "project_name": project_request.project_name,
            "max_repair_attempts": MAX_REPAIR_ATTEMPTS,
        },
    ):
        # 1. Input Guardrail Verification (Req 8)
        with otel_tracer.start_span(
            name="guardrail_scan",
            stage="security_screening",
            framework="rule_guardrail",
            input_data=project_request.description,
        ) as guard_span:
            guard_result = guard.validate_prompt(project_request.description)
            guard_span.set_attribute("security.is_safe", guard_result.is_safe)
            guard_span.set_attribute("security.risk_level", guard_result.risk_level)

            if not guard_result.is_safe:
                blackboard.record_error(f"Guardrail rejected input: {guard_result.reason}")
                raise ValueError(f"Security Guardrail Violation: {guard_result.reason}")

        print("Security Guardrail: Input description validated successfully.")

        # 2. MCP Metadata Lookup Pre-Check (Req 2)
        with otel_tracer.start_span(
            name="mcp_knowledge_lookup",
            stage="tool_execution",
            framework="mcp",
            attributes={"mcp.tool_name": "sqlite_metadata_lookup"},
        ):
            metadata = mcp_client.lookup_metadata(category="pytest")
            validation_callback.handle_tool_return("sqlite_metadata_lookup", metadata, dict)
            print(f"MCP Tool: Retrieved {metadata.get('found_count', 0)} pytest reference items.")

        # 3. Log workflow started event
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

            with otel_tracer.start_span(
                name="initial_testing",
                stage="testing",
                framework="pytest",
            ):
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
                        current_attempt["reason"] = "No failing test result available."
                        break

                    # Debugging Agent (CrewAI)
                    with otel_tracer.start_span(
                        name=f"debugging_attempt_{attempt_number}",
                        stage="debugging",
                        framework="crewai",
                        model="groq/qwen/qwen3.8-27b",
                        input_data=test_result.summary,
                    ):
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
                        current_attempt["reason"] = "Debugger did not produce a report."
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

                    # MCP AST Tool Inspection before proposing repair (Req 2)
                    with otel_tracer.start_span(
                        name="mcp_ast_inspection",
                        stage="tool_execution",
                        framework="mcp",
                        attributes={"mcp.tool_name": "ast_file_parser"},
                    ):
                        for target_rel in debug_report.affected_files:
                            ast_info = mcp_client.parse_python_ast(file_path=str(workspace / target_rel))
                            validation_callback.handle_tool_return("ast_file_parser", ast_info, dict)
                            print(f"MCP Tool: AST verified for '{target_rel}' (valid_syntax={ast_info.get('is_valid_syntax')})")

                    # Repair Agent (CrewAI)
                    with otel_tracer.start_span(
                        name=f"repair_proposal_attempt_{attempt_number}",
                        stage="repair_proposal",
                        framework="crewai",
                        model="groq/qwen/qwen3.8-27b",
                        input_data=debug_report.model_dump_json(),
                    ):
                        patch, proposal_duration = _run_timed(
                            trace,
                            "repair_proposal",
                            propose_repair,
                            debug_report,
                            workspace,
                            code_files,
                        )
                    current_attempt["timings"]["repair_proposal"] = proposal_duration

                    _safe_audit_event(
                        logger,
                        task_id=task_id,
                        trace_id=trace.trace_id,
                        event_type="patch_proposed",
                        stage="repair_proposal",
                        status="success",
                        details={
                            "attempt": attempt_number,
                            "path": patch.file_path,
                            "duration_seconds": proposal_duration,
                        },
                    )

                    # Validate Patch
                    with otel_tracer.start_span(
                        name=f"patch_validation_attempt_{attempt_number}",
                        stage="patch_validation",
                        framework="deterministic_guardrail",
                    ):
                        _, validation_duration = _run_timed(
                            trace,
                            "patch_validation",
                            validate_patch,
                            patch,
                            workspace,
                            code_files,
                        )
                    current_attempt["timings"]["patch_validation"] = validation_duration

                    _safe_audit_event(
                        logger,
                        task_id=task_id,
                        trace_id=trace.trace_id,
                        event_type="patch_validated",
                        stage="patch_validation",
                        status="success",
                        details={
                            "attempt": attempt_number,
                            "path": patch.file_path,
                            "duration_seconds": validation_duration,
                        },
                    )

                    # Apply Patch (Correct parameter order: patch, workspace, code_files)
                    with otel_tracer.start_span(
                        name=f"patch_application_attempt_{attempt_number}",
                        stage="patch_application",
                        framework="atomic_file_guard",
                    ):
                        _, application_duration = _run_timed(
                            trace,
                            "patch_application",
                            apply_patch,
                            patch,
                            workspace,
                            code_files,
                        )
                    current_attempt["timings"]["patch_application"] = application_duration

                    _safe_audit_event(
                        logger,
                        task_id=task_id,
                        trace_id=trace.trace_id,
                        event_type="patch_applied",
                        stage="patch_application",
                        status="success",
                        details={
                            "attempt": attempt_number,
                            "path": patch.file_path,
                            "duration_seconds": application_duration,
                        },
                    )

                    # Retest Workspace
                    with otel_tracer.start_span(
                        name=f"retesting_attempt_{attempt_number}",
                        stage="repair_retesting",
                        framework="pytest",
                    ):
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
                    print(f"Repair attempt {attempt_number} did not fix all tests.")

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
