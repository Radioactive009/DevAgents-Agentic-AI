
from src.architecture_agent import generate_architecture
from src.models import ProjectRequest


def main():
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

    print("\nGenerating architecture plan...\n")

    plan = generate_architecture(request)

    print("\n========== ARCHITECTURE PLAN ==========\n")
    print(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
