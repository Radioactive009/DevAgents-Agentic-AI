
import os

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Process, Task

from src.models import ArchitecturePlan, ProjectRequest


load_dotenv()


def create_architecture_agent() -> Agent:
    """Create the Architecture Agent using the Groq API."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Check your project's .env file."
        )

    llm = LLM(
        model="groq/openai/gpt-oss-120b",
        api_key=api_key,
        temperature=0.2,
    )

    return Agent(
        role="Senior Software Architect",
        goal=(
            "Design maintainable, testable software that satisfies "
            "the user's requirements."
        ),
        backstory=(
            "You are an experienced software architect. "
            "You produce practical designs, define clear file structures, "
            "identify risks, and create testable acceptance criteria. "
            "Never claim that code has been implemented or tested "
            "when it has not."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def generate_architecture(
    request: ProjectRequest,
) -> ArchitecturePlan:
    """Generate and validate an architecture plan."""

    architect = create_architecture_agent()

    task = Task(
        description=(
            "Design a software project using these requirements:\n"
            "Project name: {project_name}\n"
            "Description: {description}\n"
            "Language: {language}\n"
            "Required features: {features}\n"
            "Acceptance criteria: {acceptance_criteria}\n\n"
            "Create a practical architecture suitable for a beginner "
            "to implement. Propose realistic files, implementation steps, "
            "acceptance criteria, and important risks. Do not claim "
            "that implementation or testing has already occurred."
        ),
        expected_output=(
            "A complete architecture plan matching the ArchitecturePlan "
            "schema. All lists must contain useful, specific entries."
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
                or "Define appropriate acceptance criteria."
            ),
        }
    )

    if result.pydantic is None:
        raise RuntimeError(
            "CrewAI did not return a valid ArchitecturePlan. "
            "Inspect the execution output for details."
        )

    return result.pydantic
