
from typing import Literal

from pydantic import BaseModel, Field


class ProjectRequest(BaseModel):
    """Requirements submitted by the user."""

    project_name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=10, max_length=5000)
    language: str = Field(min_length=1)
    features: list[str] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(default_factory=list)


class ArchitecturePlan(BaseModel):
    """Structured design produced by the Architecture Agent."""

    project_name: str
    summary: str
    components: list[str] = Field(min_length=1)
    proposed_files: list[str] = Field(min_length=1)
    implementation_steps: list[str] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """Structured results returned by the testing component."""

    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    summary: str = ""
    error_details: list[str] = Field(default_factory=list)


class ProjectState(BaseModel):
    """Shared project information used throughout the workflow."""

    task_id: str
    request: ProjectRequest

    status: Literal[
        "planning",
        "coding",
        "testing",
        "debugging",
        "verifying",
        "completed",
        "failed",
    ] = "planning"

    architecture_plan: ArchitecturePlan | None = None
    code_files: list[str] = Field(default_factory=list)
    test_result: TestResult | None = None
    errors: list[str] = Field(default_factory=list)

    iteration: int = Field(default=0, ge=0, le=10)
    final_report: str | None = None
