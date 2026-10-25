import os

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Process, Task

from src.models import ArchitecturePlan, ProjectRequest

load_dotenv(override=True)


def create_architecture_agent() -> Agent:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Check your .env file."
        )

    llm = LLM(
        model="groq/qwen/qwen3.8-27b",
        api_key=api_key,
        temperature=0.1,
        max_tokens=800,
    )

    return Agent(
        role="Software Architect",
        goal="Create a concise, practical and testable software design.",
        backstory=(
            "You are a pragmatic software architect. "
            "You design small, maintainable applications. "
            "Never claim that code was executed or tested unless it was."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )


def generate_architecture(
    request: ProjectRequest,
) -> ArchitecturePlan:
    architect = create_architecture_agent()

    task = Task(
        description=(
            "Create a concise architecture plan for this project.\n\n"
            "Project: {project_name}\n"
            "Description: {description}\n"
            "Language: {language}\n"
            "Features: {features}\n"
            "Acceptance criteria: {acceptance_criteria}\n\n"
            "Output requirements:\n"
            "- Summary: maximum 80 words.\n"
            "- Components: 3 to 5 entries.\n"
            "- Proposed files: 4 to 6 paths.\n"
            "- Implementation steps: exactly 4 steps.\n"
            "- Acceptance criteria: exactly 3 criteria.\n"
            "- Risks: at most 3 entries.\n"
            "- Return concise data matching the required schema."
        ),
        expected_output=(
            "A structured ArchitecturePlan with project details, "
            "components, files, steps, acceptance criteria and risks."
        ),
        agent=architect,
        output_pydantic=ArchitecturePlan,
    )

    crew = Crew(
        agents=[architect],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff(
        inputs={
            "project_name": request.project_name,
            "description": request.description,
            "language": request.language,
            "features": ", ".join(request.features),
            "acceptance_criteria": (
                "; ".join(request.acceptance_criteria)
                or "Define suitable criteria."
            ),
        }
    )

    plan = result.pydantic

    if plan is None:
        raise RuntimeError(
            "Architecture generation did not produce a valid "
            "ArchitecturePlan."
        )

    return plan