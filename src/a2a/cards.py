"""
A2A Agent Card Definitions and Export Utilities.

Builds AgentCard protobuf objects conforming strictly to the official
a2a-sdk v1.2.3 specification, satisfying all 8 required fields:
1. name (str)
2. description (str)
3. supported_interfaces (list with at least one AgentInterface, protocol_binding='JSONRPC')
4. version (str)
5. capabilities (AgentCapabilities)
6. default_input_modes (list[str])
7. default_output_modes (list[str])
8. skills (list with at least one AgentSkill with non-empty tags)
"""

import json
from pathlib import Path
from typing import Any

from a2a.server.routes.agent_card_routes import agent_card_to_dict
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from a2a.utils.proto_utils import (
    _validate_proto_required_fields_internal,
    validate_proto_required_fields,
)


def get_adk_agent_card(base_url: str = "http://localhost:8001") -> AgentCard:
    """Build and return the Google ADK Software Architect AgentCard."""
    clean_base_url = base_url.rstrip("/")
    card = AgentCard(
        name="adk_software_architect",
        description=(
            "Google ADK Software Architect agent specialized in analyzing requirements, "
            "evaluating system constraints, and designing structured technical architecture plans."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url=clean_base_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
        ),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            AgentSkill(
                id="software_architecture_design",
                name="Software Architecture Design",
                description=(
                    "Analyzes project requests, decomposes systems into components and proposed files, "
                    "defines implementation steps, and identifies technical risks."
                ),
                tags=["architecture", "system-design", "adk", "planning"],
            )
        ],
    )
    validate_proto_required_fields(card)
    return card


def get_crewai_agent_card(base_url: str = "http://localhost:8002") -> AgentCard:
    """Build and return the CrewAI Software Engineer AgentCard."""
    clean_base_url = base_url.rstrip("/")
    card = AgentCard(
        name="crewai_software_engineer",
        description=(
            "CrewAI Software Engineer agent generating robust, maintainable source code "
            "and unit tests strictly compliant with architecture plans."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url=clean_base_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
        ),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            AgentSkill(
                id="code_generation",
                name="Code Generation",
                description=(
                    "Produces verified source files, unit tests, and minimal production implementations "
                    "from structured architecture plan specifications."
                ),
                tags=["coding", "python", "crewai", "implementation"],
            )
        ],
    )
    validate_proto_required_fields(card)
    return card


def get_agent_card(base_url: str = "http://localhost:8000") -> AgentCard:
    """Build and return the primary/orchestrator DevAgents-AGI AgentCard."""
    clean_base_url = base_url.rstrip("/")
    card = AgentCard(
        name="devagents_agi_orchestrator",
        description=(
            "DevAgents-AGI Multi-Agent Orchestrator coordinating dual-framework agents "
            "(Google ADK and CrewAI) over the A2A protocol for autonomous software engineering."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url=clean_base_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
        ),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[
            AgentSkill(
                id="multi_agent_orchestration",
                name="Multi-Agent Orchestration",
                description="Coordinates dual-agent planning and code generation over A2A JSON-RPC transport.",
                tags=["orchestration", "multi-agent", "a2a", "coordination"],
            ),
            AgentSkill(
                id="software_architecture_design",
                name="Software Architecture Design",
                description="Analyzes requirements and designs technical plans via Google ADK.",
                tags=["architecture", "adk"],
            ),
            AgentSkill(
                id="code_generation",
                name="Code Generation",
                description="Implements modules and test suites via CrewAI.",
                tags=["coding", "crewai"],
            ),
        ],
    )
    validate_proto_required_fields(card)
    return card


def export_agent_cards_to_disk(
    output_dir: Path | str = Path("."),
) -> dict[str, Path]:
    """Export all agent cards as canonical JSON files to disk.

    Writes:
      - agent_card.json (Unified / Orchestrator card)
      - adk_agent_card.json (Google ADK agent card)
      - crewai_agent_card.json (CrewAI agent card)

    Returns a dict mapping card filename to its absolute Path.
    """
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    cards: dict[str, AgentCard] = {
        "agent_card.json": get_agent_card(),
        "adk_agent_card.json": get_adk_agent_card(),
        "crewai_agent_card.json": get_crewai_agent_card(),
    }

    exported_paths: dict[str, Path] = {}
    for filename, card in cards.items():
        # Validate required fields
        violations = _validate_proto_required_fields_internal(card)
        if violations:
            raise ValueError(f"AgentCard {filename} failed validation: {violations}")

        card_dict: dict[str, Any] = agent_card_to_dict(card)
        file_path = target_dir / filename
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(card_dict, f, indent=2)
        exported_paths[filename] = file_path

    return exported_paths
