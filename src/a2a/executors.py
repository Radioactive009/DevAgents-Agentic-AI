"""
A2A Agent Executors for Google ADK and CrewAI.

Implements AgentExecutor subclasses conforming to a2a-sdk v1.2.3:
- GoogleAdkAgentExecutor: receives ProjectRequest via A2A, generates ArchitecturePlan,
  and enqueues response Message.
- CrewAiAgentExecutor: receives ArchitecturePlan or ProjectRequest via A2A,
  generates code, and enqueues response Message.
"""

import json
import os
from pathlib import Path
from typing import Any
import uuid

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Message,
    Part,
    Role,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from src.adk_architecture_agent import generate_adk_architecture
from src.coding_agent import (
    CodeGenerationResult,
    GeneratedFile,
    generate_code,
    write_generated_files,
)
from src.models import ArchitecturePlan, ProjectRequest


class GoogleAdkAgentExecutor(AgentExecutor):
    """A2A Executor wrapping the Google ADK Architecture Agent."""

    def __init__(
        self,
        mock: bool = False,
        config: Any | None = None,
        callback_listener: Any | None = None,
    ):
        self.mock = mock
        self.config = config
        self.callback_listener = callback_listener

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Execute architecture generation for the incoming A2A request."""
        # 1. Extract message text
        msg = context.message
        if not msg or not msg.parts or not msg.parts[0].text:
            raise ValueError("GoogleAdkAgentExecutor: No message text found in request.")

        raw_text = msg.parts[0].text.strip()
        if not raw_text:
            raise ValueError("GoogleAdkAgentExecutor: Empty text payload.")

        # 2. Parse ProjectRequest
        request: ProjectRequest
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict) and "project_name" in parsed:
                request = ProjectRequest.model_validate(parsed)
            elif isinstance(parsed, dict):
                request = ProjectRequest(
                    project_name=parsed.get("name", "A2A-Project"),
                    description=parsed.get("description", raw_text),
                    language=parsed.get("language", "python"),
                    features=parsed.get("features", ["Autonomous execution"]),
                    acceptance_criteria=parsed.get("acceptance_criteria", []),
                )
            else:
                request = ProjectRequest(
                    project_name="A2A-Project",
                    description=raw_text,
                    language="python",
                    features=["Autonomous architecture generation"],
                )
        except Exception:
            request = ProjectRequest(
                project_name="A2A-Project",
                description=raw_text,
                language="python",
                features=["Autonomous architecture generation"],
            )

        # 3. Generate ArchitecturePlan
        has_groq = bool(os.getenv("GROQ_API_KEY"))
        if self.mock or not has_groq:
            plan = ArchitecturePlan(
                project_name=request.project_name,
                summary=f"Architecture plan for {request.project_name} designed via Google ADK over A2A.",
                components=["CoreEngine", "StorageAdapter", "ServiceAPI"],
                proposed_files=["app.py", "models.py", "storage.py", "test_app.py"],
                implementation_steps=[
                    "Define schema data models",
                    "Implement business logic engine",
                    "Add interface and storage bindings",
                    "Develop automated verification suite",
                ],
                acceptance_criteria=request.acceptance_criteria
                or [
                    "All components execute without uncaught exceptions",
                    "Inputs and outputs validate against schemas",
                    "Unit test suite achieves full coverage",
                ],
                risks=["High concurrency latency", "External service timeouts"],
            )
        else:
            plan = generate_adk_architecture(
                request=request,
                config=self.config,
                callback_listener=self.callback_listener,
            )

        # 4. Enqueue A2A Response Message
        response = Message(
            message_id=str(uuid.uuid4()),
            role=Role.ROLE_AGENT,
            parts=[
                Part(
                    text=plan.model_dump_json(indent=2),
                    media_type="application/json",
                )
            ],
        )
        await event_queue.enqueue_event(response)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel ongoing architecture task."""
        if context.task_id:
            event = TaskStatusUpdateEvent(
                task_id=context.task_id,
                status=TaskStatus(state=TaskState.TASK_STATE_CANCELED),
            )
            await event_queue.enqueue_event(event)


class CrewAiAgentExecutor(AgentExecutor):
    """A2A Executor wrapping CrewAI Coding and Engineering Agent."""

    def __init__(
        self,
        workspace_dir: Path | str | None = None,
        mock: bool = False,
    ):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else None
        self.mock = mock

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Execute code generation for incoming A2A plan or request."""
        # 1. Extract message text
        msg = context.message
        if not msg or not msg.parts or not msg.parts[0].text:
            raise ValueError("CrewAiAgentExecutor: No message text found in request.")

        raw_text = msg.parts[0].text.strip()
        if not raw_text:
            raise ValueError("CrewAiAgentExecutor: Empty text payload.")

        # 2. Parse ArchitecturePlan or ProjectRequest
        plan: ArchitecturePlan
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict) and "proposed_files" in parsed and "implementation_steps" in parsed:
                plan = ArchitecturePlan.model_validate(parsed)
            elif isinstance(parsed, dict) and "project_name" in parsed and "features" in parsed:
                req = ProjectRequest.model_validate(parsed)
                plan = ArchitecturePlan(
                    project_name=req.project_name,
                    summary=f"Architecture plan for {req.project_name}",
                    components=["MainModule", "TestModule"],
                    proposed_files=["main.py", "test_main.py"],
                    implementation_steps=["Create main module", "Create test module", "Verify", "Done"],
                    acceptance_criteria=req.acceptance_criteria or ["All tests pass"],
                    risks=["None"],
                )
            elif isinstance(parsed, dict):
                plan = ArchitecturePlan(
                    project_name=parsed.get("project_name", "A2A-Project"),
                    summary=parsed.get("summary", "A2A generated architecture"),
                    components=["CoreModule"],
                    proposed_files=["app.py", "test_app.py"],
                    implementation_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
                    acceptance_criteria=["Passes verification", "Runs cleanly"],
                    risks=["None"],
                )
            else:
                plan = ArchitecturePlan(
                    project_name="A2A-Project",
                    summary=raw_text,
                    components=["CoreModule"],
                    proposed_files=["app.py", "test_app.py"],
                    implementation_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
                    acceptance_criteria=["Passes verification"],
                    risks=["None"],
                )
        except Exception:
            plan = ArchitecturePlan(
                project_name="A2A-Project",
                summary=raw_text,
                components=["CoreModule"],
                proposed_files=["app.py", "test_app.py"],
                implementation_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
                acceptance_criteria=["Passes verification"],
                risks=["None"],
            )

        # 3. Generate Code
        has_groq = bool(os.getenv("GROQ_API_KEY"))
        if self.mock or not has_groq or not self.workspace_dir:
            result = CodeGenerationResult(
                files=[
                    GeneratedFile(
                        path="app.py",
                        content=(
                            "# Generated by CrewAI via A2A protocol\n\n"
                            "def run() -> str:\n"
                            "    return 'DevAgents-AGI A2A Success'\n"
                        ),
                    ),
                    GeneratedFile(
                        path="test_app.py",
                        content=(
                            "from app import run\n\n"
                            "def test_run():\n"
                            "    assert run() == 'DevAgents-AGI A2A Success'\n"
                        ),
                    ),
                ],
                summary=f"Successfully generated 2 implementation files for {plan.project_name}.",
            )
            written_paths: list[str] = []
            if self.workspace_dir:
                written_paths = write_generated_files(result, self.workspace_dir)
        else:
            result, written_paths = generate_code(plan, self.workspace_dir)

        # 4. Enqueue A2A Response Message
        payload = {
            "project_name": plan.project_name,
            "result": result.model_dump(),
            "written_paths": written_paths,
        }
        response = Message(
            message_id=str(uuid.uuid4()),
            role=Role.ROLE_AGENT,
            parts=[
                Part(
                    text=json.dumps(payload, indent=2),
                    media_type="application/json",
                )
            ],
        )
        await event_queue.enqueue_event(response)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel ongoing coding task."""
        if context.task_id:
            event = TaskStatusUpdateEvent(
                task_id=context.task_id,
                status=TaskStatus(state=TaskState.TASK_STATE_CANCELED),
            )
            await event_queue.enqueue_event(event)
