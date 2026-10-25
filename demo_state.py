
from src.models import ProjectRequest, ProjectState

request = ProjectRequest(
    project_name="Todo API",
    description="Build an API for creating and managing tasks.",
    language="Python",
    features=["Create tasks", "List tasks", "Delete tasks"],
    acceptance_criteria=["All tests pass"],
)

state = ProjectState(
    task_id="task-001",
    request=request,
)

state.architecture_plan = "Use FastAPI with a task model."
state.status = "coding"

print(state.model_dump_json(indent=2))
