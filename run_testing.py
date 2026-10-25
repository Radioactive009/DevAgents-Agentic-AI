
from pathlib import Path
import json

from src.blackboard import Blackboard
from src.models import ProjectRequest
from src.testing_agent import run_project_tests


def main():
    task_id = "6d4515a7-eb77-45c5-ae7a-cd7d14e7bd55"

    workspace = (
        Path(__file__).resolve().parent
        / "generated_projects"
        / task_id
    )

    # Reconstruct the project request for this demonstration.
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

    # Restore the status required before recording generated files.
    from src.models import ArchitecturePlan

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

    blackboard.update_architecture(plan)

    generated_files = [
        "app.py",
        "models.py",
        "store.py",
        "tests/test_api.py",
        "requirements.txt",
    ]
    blackboard.record_code_files(generated_files)

    print("Running generated project tests...")
    result = run_project_tests(workspace)

    # Record the test results and update workflow status.
    state = blackboard.record_test_result(result)

    print("\n=== TEST RESULT ===")
    print(result.model_dump_json(indent=2))

    print("\n=== UPDATED BLACKBOARD ===")
    print(json.dumps(
        {
            "task_id": state.task_id,
            "status": state.status,
            "code_files": state.code_files,
            "test_result": (
                state.test_result.model_dump()
                if state.test_result
                else None
            ),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
