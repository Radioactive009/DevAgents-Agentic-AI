
from uuid import uuid4

from src.blackboard import Blackboard
from src.models import ProjectRequest
from src.architecture_agent import generate_architecture


def main():
    # 1. Define the user's project requirements.
    request = ProjectRequest(
        project_name="Todo API",
        description=(
            "Build a REST API for managing tasks with create, "
            "list, update, and delete functionality."
        ),
        language="Python",
        features=[
            "Create tasks",
            "List tasks",
            "Update tasks",
            "Delete tasks",
        ],
        acceptance_criteria=[
            "The API supports all required task operations.",
            "Invalid requests return appropriate errors.",
            "Automated tests cover the main endpoints.",
        ],
    )

    # 2. Create a Blackboard with an initial project state.
    blackboard = Blackboard(
        task_id=str(uuid4()),
        request=request,
    )

    print("\n========== INITIAL PROJECT STATE ==========")
    print(blackboard.get_state().model_dump_json(indent=2))

    try:
        # 3. Ask the CrewAI Architecture Agent to create a plan.
        print("\nGenerating architecture plan...")
        plan = generate_architecture(request)

        # 4. Save the plan to the shared Blackboard.
        updated_state = blackboard.update_architecture(plan)

        # 5. Display the updated shared state.
        print("\n========== UPDATED BLACKBOARD STATE ==========")
        print(updated_state.model_dump_json(indent=2))

        print("\nArchitecture plan successfully saved to Blackboard.")
        print(f"Current status: {updated_state.status}")

    except Exception as error:
        # Record the failure so the project state retains the error.
        blackboard.record_error(str(error))

        print("\nArchitecture generation failed.")
        print(f"Error: {error}")
        print("\n========== BLACKBOARD AFTER FAILURE ==========")
        print(blackboard.get_state().model_dump_json(indent=2))


if __name__ == "__main__":
    main()
