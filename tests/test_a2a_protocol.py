"""
Comprehensive Unit and Integration Test Suite for Agent-to-Agent (A2A) Protocol.

Verifies:
1. Protobuf AgentCard schema compliance (all 8 required fields, 0 violations).
2. GET /.well-known/agent-card.json endpoint on ADK and CrewAI apps.
3. JSON-RPC 2.0 SendMessage dispatch to GoogleAdkAgentExecutor.
4. JSON-RPC 2.0 SendMessage dispatch to CrewAiAgentExecutor.
5. End-to-end A2A pipeline: ADK architecture output forwarded to CrewAI code generator.
6. Error handling:
   - Method not found (-32601)
   - Validation failure on missing message_id (-32602)
   - Parse error on malformed JSON body (-32700)
   - Internal error on executor runtime exception (-32603)
7. Disk export functionality (agent_card.json, adk_agent_card.json, crewai_agent_card.json).
8. Official a2a.client integration with in-memory httpx.ASGITransport.
"""

import json
from pathlib import Path
import uuid

import httpx
import pytest

from a2a.client import ClientConfig, create_client
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    SendMessageRequest,
)
from a2a.utils.proto_utils import (
    _validate_proto_required_fields_internal,
    validate_proto_required_fields,
)

from src.a2a.cards import (
    export_agent_cards_to_disk,
    get_adk_agent_card,
    get_agent_card,
    get_crewai_agent_card,
)
from src.a2a.client import create_a2a_client, send_a2a_message
from src.a2a.executors import CrewAiAgentExecutor, GoogleAdkAgentExecutor
from src.a2a.server import (
    create_a2a_app,
    create_adk_a2a_app,
    create_crewai_a2a_app,
)
from src.models import ArchitecturePlan, ProjectRequest


class CrashingExecutor(AgentExecutor):
    """Executor that unconditionally raises a RuntimeError for error testing."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise RuntimeError("Intentional executor crash for A2A error code verification")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


# =====================================================================
# 1. AGENT CARD SPECIFICATION & VALIDATION TESTS
# =====================================================================

def test_agent_cards_pass_official_protobuf_validation() -> None:
    """Ensure all agent cards satisfy all 8 strictly required fields with 0 errors."""
    cards = [
        get_adk_agent_card("http://localhost:8001"),
        get_crewai_agent_card("http://localhost:8002"),
        get_agent_card("http://localhost:8000"),
    ]

    for card in cards:
        # validate_proto_required_fields should not raise
        validate_proto_required_fields(card)
        # _validate_proto_required_fields_internal should return empty list
        violations = _validate_proto_required_fields_internal(card)
        assert violations == [], f"Violations found for card {card.name}: {violations}"

        # Verify the 8 required fields explicitly
        assert card.name, "name must not be empty"
        assert card.description, "description must not be empty"
        assert len(card.supported_interfaces) >= 1, "supported_interfaces must not be empty"
        assert card.version == "1.0.0"
        assert card.HasField("capabilities"), "capabilities must be present"
        assert len(card.default_input_modes) >= 1, "default_input_modes must not be empty"
        assert len(card.default_output_modes) >= 1, "default_output_modes must not be empty"
        assert len(card.skills) >= 1, "skills must not be empty"

        # Verify interface fields
        interface = card.supported_interfaces[0]
        assert interface.url.startswith("http")
        assert interface.protocol_binding == "JSONRPC"
        assert interface.protocol_version == "1.0"

        # Verify skill fields
        skill = card.skills[0]
        assert skill.id
        assert skill.name
        assert skill.description
        assert len(skill.tags) >= 1


def test_incomplete_agent_card_fails_validation() -> None:
    """Ensure our validation helper accurately detects incomplete cards."""
    incomplete = AgentCard(name="incomplete_agent")
    violations = _validate_proto_required_fields_internal(incomplete)
    assert len(violations) > 0
    missing_fields = {v["field"] for v in violations}
    assert "description" in missing_fields
    assert "supported_interfaces" in missing_fields
    assert "version" in missing_fields
    assert "capabilities" in missing_fields


# =====================================================================
# 2. WELL-KNOWN AGENT CARD ENDPOINT TESTS
# =====================================================================

@pytest.mark.anyio
async def test_well_known_agent_card_endpoint_adk() -> None:
    """Verify GET /.well-known/agent-card.json on ADK FastAPI service."""
    app = create_adk_a2a_app(GoogleAdkAgentExecutor(mock=True))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8001",
    ) as client:
        response = await client.get("/.well-known/agent-card.json")
        assert response.status_code == 200
        assert "etag" in response.headers

        data = response.json()
        assert data["name"] == "adk_software_architect"
        assert data["version"] == "1.0.0"
        assert "supportedInterfaces" in data
        assert data["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
        assert len(data["skills"]) >= 1


@pytest.mark.anyio
async def test_well_known_agent_card_endpoint_crewai() -> None:
    """Verify GET /.well-known/agent-card.json on CrewAI FastAPI service."""
    app = create_crewai_a2a_app(CrewAiAgentExecutor(mock=True))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8002",
    ) as client:
        response = await client.get("/.well-known/agent-card.json")
        assert response.status_code == 200
        assert "etag" in response.headers

        data = response.json()
        assert data["name"] == "crewai_software_engineer"
        assert data["version"] == "1.0.0"
        assert "supportedInterfaces" in data
        assert data["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
        assert len(data["skills"]) >= 1


# =====================================================================
# 3. JSON-RPC SEND MESSAGE TESTS
# =====================================================================

@pytest.mark.anyio
async def test_adk_agent_send_message_jsonrpc() -> None:
    """Test JSON-RPC SendMessage execution on Google ADK Agent app."""
    app = create_adk_a2a_app(GoogleAdkAgentExecutor(mock=True))

    request_payload = ProjectRequest(
        project_name="DataPipeline",
        description="High throughput real-time streaming data processor.",
        language="python",
        features=["Kafka ingestion", "Transform engine", "Postgres sink"],
        acceptance_criteria=["Zero message loss", "Latency under 50ms"],
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8001",
    ) as client:
        result = await send_a2a_message(
            sender_card=None,
            receiver_url="http://localhost:8001",
            text_payload=request_payload.model_dump_json(),
            httpx_client=client,
        )

        assert "error" not in result or result["error"] is None
        assert "result" in result
        raw_plan_text = result["result"]["message"]["parts"][0]["text"]
        plan_dict = json.loads(raw_plan_text)

        plan = ArchitecturePlan.model_validate(plan_dict)
        assert plan.project_name == "DataPipeline"
        assert len(plan.components) >= 1
        assert len(plan.proposed_files) >= 1
        assert len(plan.implementation_steps) >= 1


@pytest.mark.anyio
async def test_crewai_agent_send_message_jsonrpc(tmp_path: Path) -> None:
    """Test JSON-RPC SendMessage execution on CrewAI Agent app with file generation."""
    workspace = tmp_path / "crewai_workspace"
    app = create_crewai_a2a_app(CrewAiAgentExecutor(workspace_dir=workspace, mock=True))

    plan = ArchitecturePlan(
        project_name="MicroService",
        summary="REST API microservice architecture.",
        components=["API", "Models"],
        proposed_files=["app.py", "test_app.py"],
        implementation_steps=["Create models", "Create endpoints", "Write tests"],
        acceptance_criteria=["Clean endpoints", "Tests pass"],
        risks=["Latency"],
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8002",
    ) as client:
        result = await send_a2a_message(
            sender_card=None,
            receiver_url="http://localhost:8002",
            text_payload=plan.model_dump_json(),
            httpx_client=client,
        )

        assert "error" not in result or result["error"] is None
        assert "result" in result
        response_payload = json.loads(result["result"]["message"]["parts"][0]["text"])

        assert response_payload["project_name"] == "MicroService"
        assert "result" in response_payload
        assert len(response_payload["result"]["files"]) >= 1
        assert len(response_payload["written_paths"]) >= 1

        # Confirm files were written to workspace on disk
        for written in response_payload["written_paths"]:
            assert (workspace / written).exists()


# =====================================================================
# 4. END-TO-END A2A INTERACTION PIPELINE
# =====================================================================

@pytest.mark.anyio
async def test_end_to_end_a2a_adk_to_crewai_pipeline(tmp_path: Path) -> None:
    """Full End-to-End A2A Pipeline:
    1. Send user request to ADK Agent over A2A transport -> yields ArchitecturePlan.
    2. Forward ArchitecturePlan over A2A transport to CrewAI Agent -> yields CodeGenerationResult.
    """
    workspace = tmp_path / "e2e_workspace"
    adk_app = create_adk_a2a_app(GoogleAdkAgentExecutor(mock=True))
    crewai_app = create_crewai_a2a_app(CrewAiAgentExecutor(workspace_dir=workspace, mock=True))

    user_request = ProjectRequest(
        project_name="E2EAutonomousSystem",
        description="Autonomous agent system coordinating planning and coding over A2A.",
        language="python",
        features=["A2A messaging", "Protobuf validation", "ASGI in-memory transport"],
        acceptance_criteria=["Zero socket collision", "Complete code output"],
    )

    # Step 1: ADK A2A interaction
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=adk_app),
        base_url="http://localhost:8001",
    ) as adk_client:
        adk_response = await send_a2a_message(
            sender_card=None,
            receiver_url="http://localhost:8001",
            text_payload=user_request.model_dump_json(),
            httpx_client=adk_client,
        )

        adk_plan_json = adk_response["result"]["message"]["parts"][0]["text"]
        plan = ArchitecturePlan.model_validate_json(adk_plan_json)
        assert plan.project_name == "E2EAutonomousSystem"

    # Step 2: Forward architecture plan from ADK to CrewAI over A2A
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=crewai_app),
        base_url="http://localhost:8002",
    ) as crewai_client:
        crewai_response = await send_a2a_message(
            sender_card=get_adk_agent_card(),
            receiver_url="http://localhost:8002",
            text_payload=plan.model_dump_json(),
            httpx_client=crewai_client,
        )

        crewai_payload = json.loads(crewai_response["result"]["message"]["parts"][0]["text"])
        assert crewai_payload["project_name"] == "E2EAutonomousSystem"
        assert len(crewai_payload["written_paths"]) >= 2
        for written in crewai_payload["written_paths"]:
            file_disk_path = workspace / written
            assert file_disk_path.exists()
            content = file_disk_path.read_text(encoding="utf-8")
            assert "DevAgents-AGI A2A Success" in content


# =====================================================================
# 5. ERROR HANDLING SPECIFICATION TESTS
# =====================================================================

@pytest.mark.anyio
async def test_jsonrpc_error_unknown_method() -> None:
    """Unknown method returns JSON-RPC -32601 Method not found."""
    app = create_adk_a2a_app(GoogleAdkAgentExecutor(mock=True))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8001",
    ) as client:
        body = {
            "jsonrpc": "2.0",
            "id": "test-unknown-method",
            "method": "NonExistentMethod",
            "params": {},
        }
        res = await client.post("/", json=body, headers={"A2A-Version": "1.0"})
        assert res.status_code == 200
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == -32601
        assert "Method not found" in data["error"]["message"]


@pytest.mark.anyio
async def test_jsonrpc_error_missing_message_id() -> None:
    """Missing message_id in SendMessage returns JSON-RPC -32602 Validation failed."""
    app = create_adk_a2a_app(GoogleAdkAgentExecutor(mock=True))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8001",
    ) as client:
        body = {
            "jsonrpc": "2.0",
            "id": "test-missing-message-id",
            "method": "SendMessage",
            "params": {
                "message": {
                    # Missing messageId
                    "role": "ROLE_USER",
                    "parts": [{"text": "Hello", "mediaType": "application/json"}],
                }
            },
        }
        res = await client.post("/", json=body, headers={"A2A-Version": "1.0"})
        assert res.status_code == 200
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == -32602
        assert "Validation failed" in data["error"]["message"]


@pytest.mark.anyio
async def test_jsonrpc_error_malformed_json_body() -> None:
    """Malformed non-JSON payload returns JSON-RPC -32700 Parse error."""
    app = create_adk_a2a_app(GoogleAdkAgentExecutor(mock=True))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8001",
    ) as client:
        res = await client.post(
            "/",
            content=b"not a valid json string {[]",
            headers={"A2A-Version": "1.0", "Content-Type": "application/json"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == -32700


@pytest.mark.anyio
async def test_jsonrpc_error_executor_exception() -> None:
    """Executor runtime crash returns JSON-RPC -32603 InternalError."""
    card = get_adk_agent_card()
    app = create_a2a_app(agent_card=card, agent_executor=CrashingExecutor())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8001",
    ) as client:
        body = {
            "jsonrpc": "2.0",
            "id": "test-crash",
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "ROLE_USER",
                    "parts": [{"text": "Trigger crash", "mediaType": "application/json"}],
                }
            },
        }
        res = await client.post("/", json=body, headers={"A2A-Version": "1.0"})
        assert res.status_code == 200
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == -32603


# =====================================================================
# 6. DISK EXPORT SPECIFICATION TESTS
# =====================================================================

def test_export_agent_cards_to_disk(tmp_path: Path) -> None:
    """Verify export_agent_cards_to_disk creates valid canonical JSON files."""
    exported = export_agent_cards_to_disk(output_dir=tmp_path)
    assert "agent_card.json" in exported
    assert "adk_agent_card.json" in exported
    assert "crewai_agent_card.json" in exported

    for filename, filepath in exported.items():
        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "name" in data
        assert "version" in data
        assert "supportedInterfaces" in data
        assert "capabilities" in data
        assert "skills" in data


def test_root_agent_card_files_exist() -> None:
    """Verify that root agent card files exist and are valid JSON."""
    root_dir = Path(".")
    for filename in ["agent_card.json", "adk_agent_card.json", "crewai_agent_card.json"]:
        file_path = root_dir / filename
        assert file_path.exists(), f"Required root file missing: {filename}"
        data = json.loads(file_path.read_text(encoding="utf-8"))
        assert data["version"] == "1.0.0"
        assert len(data["skills"]) >= 1


# =====================================================================
# 7. OFFICIAL A2A CLIENT RESOLUTION AND SEND_MESSAGE
# =====================================================================

@pytest.mark.anyio
async def test_official_a2a_client_with_asgi_transport() -> None:
    """Test official a2a.client.Client connected via httpx.ASGITransport."""
    app = create_adk_a2a_app(GoogleAdkAgentExecutor(mock=True))
    card = get_adk_agent_card("http://localhost:8001")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8001",
    ) as http_client:
        client = await create_a2a_client(card, httpx_client=http_client)
        req = SendMessageRequest(
            message=Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[Part(text="Build an analytics tracker", media_type="application/json")],
            )
        )
        stream = client.send_message(req)
        responses = []
        async for event in stream:
            responses.append(event)

        assert len(responses) >= 1
        response_msg = responses[0].message
        assert response_msg.role == Role.ROLE_AGENT
        plan = ArchitecturePlan.model_validate_json(response_msg.parts[0].text)
        assert plan.project_name == "A2A-Project"
