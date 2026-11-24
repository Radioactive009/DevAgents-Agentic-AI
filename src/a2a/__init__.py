"""
Agent-to-Agent (A2A) Protocol Communication Module.

Provides official A2A protocol implementations conforming to a2a-sdk v1.2.3:
- AgentCard builders & schema validation (Google ADK and CrewAI)
- AgentExecutor implementations bridging ADK architecture & CrewAI coding
- FastAPI servers with /.well-known/agent-card.json and JSON-RPC routes
- In-memory ASGI client transport for offline and end-to-end communication
"""

from src.a2a.cards import (
    export_agent_cards_to_disk,
    get_adk_agent_card,
    get_agent_card,
    get_crewai_agent_card,
)
from src.a2a.client import (
    create_a2a_client,
    send_a2a_message,
)
from src.a2a.executors import (
    CrewAiAgentExecutor,
    GoogleAdkAgentExecutor,
)
from src.a2a.server import (
    create_a2a_app,
    create_adk_a2a_app,
    create_crewai_a2a_app,
)

__all__ = [
    "export_agent_cards_to_disk",
    "get_adk_agent_card",
    "get_crewai_agent_card",
    "get_agent_card",
    "GoogleAdkAgentExecutor",
    "CrewAiAgentExecutor",
    "create_a2a_app",
    "create_adk_a2a_app",
    "create_crewai_a2a_app",
    "create_a2a_client",
    "send_a2a_message",
]
