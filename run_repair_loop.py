
import json
from pathlib import Path
from typing import Any

from src.blackboard import Blackboard
from src.debugging_agent import diagnose_failure
from src.models import ArchitecturePlan, ProjectRequest
from src.patch_applier import apply_patch
from src.patch_validator import validate_patch
from src.repair_agent import propose_repair
from src.testing_agent import run_project_tests


MAX_REPAIR_ATTEMPTS = 3


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
    """Print every repair attempt, including incomplete attempts."""
    print("\n=== REPAIR ATTEMPT HISTORY ===")
    print(json.dumps(attempts, indent=2, default=str))


def main():
    blackboard, workspace = create_demo_workflow()
    attempts: list[dict[str, Any]] = []
    current_attempt = None

    try:
        print("=== INITIAL TEST RUN ===")

        result = run_project_tests(workspace)
        blackboard.record_test_result(result)

        print(result.model_dump_json(indent=2))

        if result.failed == 0:
            print("\nAll tests passed. No repair was needed.")

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

                # Create the record BEFORE starting the attempt.
                # If a later step fails, the attempt is still recorded.
                current_attempt = {
                    "attempt": attempt_number,
                    "stage": "diagnosis",
                    "status": "in_progress",
                    "patch": None,
                    "application": None,
                    "test_result": None,
                    "error": None,
                }
                attempts.append(current_attempt)

                print(
                    f"\n=== REPAIR ATTEMPT "
                    f"{attempt_number}/{MAX_REPAIR_ATTEMPTS} ==="
                )

                # Step 1: Diagnose current test failures.
                report = diagnose_failure(
                    test_result=state.test_result,
                    code_files=state.code_files,
                    workspace=workspace,
                )

                if report is None:
                    raise RuntimeError(
                        "Tests failed, but the Debugging Agent "
                        "returned no diagnosis."
                    )

                blackboard.record_debug_report(report)

                current_attempt["debug_report"] = report.model_dump()
                current_attempt["stage"] = "repair_proposal"

                print("\nDebug report:")
                print(report.model_dump_json(indent=2))

                # Step 2: Ask the Repair Agent for a proposed patch.
                patch = propose_repair(
                    debug_report=report,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )

                current_attempt["patch"] = patch.model_dump()
                current_attempt["stage"] = "patch_validation"

                print("\nProposed patch:")
                print(patch.model_dump_json(indent=2))

                # Step 3: Validate immediately before application.
                validate_patch(
                    patch=patch,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )

                current_attempt["stage"] = "patch_application"

                # Step 4: Apply patch and preserve a backup.
                application_result = apply_patch(
                    patch=patch,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )

                current_attempt["application"] = application_result
                current_attempt["stage"] = "retesting"

                # Step 5: Rerun tests against the patched project.
                print("\nRerunning project tests...")

                result = run_project_tests(workspace)
                blackboard.record_test_result(result)

                current_attempt["test_result"] = result.model_dump()

                print("\nTest result after repair:")
                print(result.model_dump_json(indent=2))

                if result.failed == 0:
                    current_attempt["status"] = "succeeded"
                    current_attempt["stage"] = "completed"

                    print("\nRepair succeeded: all tests now pass.")
                    break

                current_attempt["status"] = "unsuccessful"
                current_attempt["stage"] = "retesting"

                print(
                    "\nTests still failing; another attempt "
                    "may be needed."
                )

                # The next attempt will diagnose the latest result.
                current_attempt = None

            else:
                print(
                    "\nRepair limit reached. "
                    "The workflow will not attempt further repairs."
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

        # Keep the failed attempt in the history.
        if current_attempt is not None:
            current_attempt["status"] = "failed"
            current_attempt["error"] = error_message

        # Blackboard records the error and transitions to failed.
        try:
            blackboard.record_error(error_message)
        except Exception as state_error:
            print(
                "Warning: could not record the error in Blackboard:",
                f"{type(state_error).__name__}: {state_error}",
            )

        print("\nRepair workflow stopped.")
        print("Error:", error_message)

        _print_attempt_history(attempts)

        print("\n=== FINAL BLACKBOARD STATE ===")
        print(blackboard.get_state().model_dump_json(indent=2))

        # Preserve the original exception for debugging.
        raise


if __name__ == "__main__":
    main()
