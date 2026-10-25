
import json
from pathlib import Path
from uuid import uuid4

from src.architecture_agent import generate_architecture
from src.blackboard import Blackboard
from src.coding_agent import generate_code
from src.models import ProjectRequest


def main():
    request = ProjectRequest(
        project_name="Todo API",
        description=(
            "Build a small Python REST API for managing todo tasks. "
            "Users should be able to create, list, update, and delete tasks."
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
        task_id=str(uuid4()),
        request=request,
    )

    # Step 1: Generate the architecture plan.
    try:
        print("\n=== STEP 1: ARCHITECTURE ===")

        plan = generate_architecture(request)
        state = blackboard.update_architecture(plan)

        print("Architecture plan saved.")
        print(json.dumps(
            state.architecture_plan.model_dump(),
            indent=2,
        ))
        print("Current status:", state.status)

        # Step 2: Generate code in a dedicated workspace.
        print("\n=== STEP 2: CODE GENERATION ===")

        workspace = (
            Path(__file__).resolve().parent
            / "generated_projects"
            / state.task_id
        )

        result, written_paths = generate_code(
            plan=plan,
            workspace=workspace,
        )

        # Step 3: Save the generated paths to the Blackboard.
        state = blackboard.record_code_files(written_paths)

        print("\nCode generation summary:")
        print(result.summary)

        print("\nGenerated files:")
        for file_path in written_paths:
            print(f"- {file_path}")

        print("\n=== FINAL BLACKBOARD STATE ===")
        print(state.model_dump_json(indent=2))
        print("\nWorkflow reached code generation successfully.")

    except Exception as error:
        blackboard.record_error(
            f"{type(error).__name__}: {error}"
        )
        print("\nWorkflow failed.")
        print("Error type:", type(error).__name__)
        print("Error message:", error)
        print("\nBlackboard state:")
        print(blackboard.get_state().model_dump_json(indent=2))
        raise


if __name__ == "__main__":
    main()
