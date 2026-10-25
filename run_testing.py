
import json
from pathlib import Path

from src.blackboard import Blackboard
from src.debugging_agent import diagnose_failure
from src.models import ArchitecturePlan, ProjectRequest
from src.testing_agent import run_project_tests


def main():
    task_id = "6d4515a7-eb77-45c5-ae7a-cd7d14e7bd55"

    project_root = Path(__file__).resolve().parent
    workspace = project_root / "generated_projects" / task_id

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

    blackboard = Blackboard(
        task_id=task_id,
        request=request,
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

    generated_files = [
        "app.py",
        "models.py",
        "store.py",
        "tests/test_api.py",
        "requirements.txt",
    ]

    try:
        # Step 1: Restore the project state for this demonstration.
        blackboard.update_architecture(plan)
        blackboard.record_code_files(generated_files)

        print("\n=== STEP 1: RUN TESTS ===")
        print("Workspace:", workspace)

        result = run_project_tests(workspace)
        state = blackboard.record_test_result(result)

        print("\n=== TEST RESULT ===")
        print(result.model_dump_json(indent=2))
        print("Current status:", state.status)

        # Step 2: Diagnose failures only.
        if result.failed > 0:
            print("\n=== STEP 2: DEBUGGING AGENT ===")
            print("Tests failed. Requesting a structured diagnosis...")

            report = diagnose_failure(
                test_result=result,
                code_files=state.code_files,
                workspace=workspace,
            )

            if report is None:
                raise RuntimeError(
                    "Tests failed, but the Debugging Agent returned no report."
                )

            state = blackboard.record_debug_report(report)

            print("\n=== DEBUG REPORT ===")
            print(report.model_dump_json(indent=2))

        else:
            print("\nAll tests passed. Debugging Agent was not needed.")

        # Step 3: Display the complete state.
        state = blackboard.get_state()

        print("\n=== FINAL BLACKBOARD STATE ===")
        print(json.dumps(state.model_dump(mode="json"), indent=2))

    except Exception as error:
        # Record workflow errors without hiding the original exception.
        try:
            blackboard.record_error(
                f"{type(error).__name__}: {error}"
            )
        except Exception:
            pass

        print("\nWorkflow failed.")
        print("Error type:", type(error).__name__)
        print("Error message:", error)
        print("\nBlackboard state:")
        print(blackboard.get_state().model_dump_json(indent=2))
        raise


if __name__ == "__main__":
    main()
