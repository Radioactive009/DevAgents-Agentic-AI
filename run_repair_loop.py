
import json
from pathlib import Path

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


def main():
    blackboard, workspace = create_demo_workflow()
    attempts = []

    try:
        print("=== INITIAL TEST RUN ===")
        result = run_project_tests(workspace)
        state = blackboard.record_test_result(result)
        print(result.model_dump_json(indent=2))

        if result.failed == 0:
            print("\nAll tests passed. No repair was needed.")
        else:
            for attempt_number in range(1, MAX_REPAIR_ATTEMPTS + 1):
                state = blackboard.get_state()

                if state.test_result is None or state.test_result.failed == 0:
                    break

                print(
                    f"\n=== REPAIR ATTEMPT "
                    f"{attempt_number}/{MAX_REPAIR_ATTEMPTS} ==="
                )

                # Step 1: Diagnose the current test failures.
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

                print("\nDebug report:")
                print(report.model_dump_json(indent=2))

                # Step 2: Ask the Repair Agent for a proposed patch.
                patch = propose_repair(
                    debug_report=report,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )

                print("\nProposed patch:")
                print(patch.model_dump_json(indent=2))

                # Step 3: Validate again immediately before applying.
                validate_patch(
                    patch=patch,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )

                # Step 4: Apply the patch and preserve a backup.
                application_result = apply_patch(
                    patch=patch,
                    workspace=workspace,
                    allowed_files=state.code_files,
                )

                attempt_record = {
                    "attempt": attempt_number,
                    "patch": patch.model_dump(),
                    "application": application_result,
                }

                # Step 5: Retest the generated project.
                print("\nRerunning project tests...")
                result = run_project_tests(workspace)
                blackboard.record_test_result(result)

                attempt_record["test_result"] = result.model_dump()
                attempts.append(attempt_record)

                print("\nTest result after repair:")
                print(result.model_dump_json(indent=2))

                if result.failed == 0:
                    print("\nRepair succeeded: all tests now pass.")
                    break

                print("\nTests still failing; another attempt may be needed.")

            else:
                print(
                    "\nRepair limit reached. "
                    "The workflow will not attempt further repairs."
                )

        final_state = blackboard.get_state()

        print("\n=== REPAIR ATTEMPT HISTORY ===")
        print(json.dumps(attempts, indent=2))

        print("\n=== FINAL BLACKBOARD STATE ===")
        print(final_state.model_dump_json(indent=2))

        if final_state.test_result and final_state.test_result.failed > 0:
            print("\nFinal outcome: unresolved test failures.")
        elif final_state.test_result:
            print("\nFinal outcome: all tests passed.")

    except Exception as error:
        blackboard.record_error(
            f"{type(error).__name__}: {error}"
        )

        print("\nRepair workflow stopped.")
        print("Error:", f"{type(error).__name__}: {error}")
        print("\nCurrent Blackboard state:")
        print(blackboard.get_state().model_dump_json(indent=2))
        raise


if __name__ == "__main__":
    main()



