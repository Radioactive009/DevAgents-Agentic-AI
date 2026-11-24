"""
A2A FastAPI Server Factories.

Provides FastAPI applications exposing official A2A protocol routes:
- GET /.well-known/agent-card.json (Agent Card metadata)
- POST / (JSON-RPC 2.0 SendMessage transport)
"""

from fastapi import FastAPI
from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard

from src.a2a.cards import get_adk_agent_card, get_crewai_agent_card
from src.a2a.executors import CrewAiAgentExecutor, GoogleAdkAgentExecutor


def create_a2a_app(
    agent_card: AgentCard,
    agent_executor: AgentExecutor,
    rpc_url: str = "/",
    title: str = "A2A Agent Service",
) -> FastAPI:
    """Create a FastAPI application hosting A2A protocol routes for any given AgentCard and Executor."""
    task_store = InMemoryTaskStore()
    handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store,
        agent_card=agent_card,
    )

    card_routes = create_agent_card_routes(agent_card=agent_card)
    jsonrpc_routes = create_jsonrpc_routes(
        request_handler=handler,
        rpc_url=rpc_url,
    )

    app = FastAPI(title=title, version=agent_card.version or "1.0.0")
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=card_routes,
        jsonrpc_routes=jsonrpc_routes,
    )

    # Attach references for introspectability
    app.state.agent_card = agent_card
    app.state.agent_executor = agent_executor
    app.state.task_store = task_store
    app.state.request_handler = handler

    return app


def create_adk_a2a_app(
    agent_executor: AgentExecutor | None = None,
    base_url: str = "http://localhost:8001",
) -> FastAPI:
    """Instantiate a FastAPI server for the Google ADK Architecture Agent over A2A."""
    executor = agent_executor or GoogleAdkAgentExecutor()
    card = get_adk_agent_card(base_url=base_url)
    return create_a2a_app(
        agent_card=card,
        agent_executor=executor,
        title="Google ADK A2A Service",
    )


def create_crewai_a2a_app(
    agent_executor: AgentExecutor | None = None,
    base_url: str = "http://localhost:8002",
) -> FastAPI:
    """Instantiate a FastAPI server for the CrewAI Coding Agent over A2A."""
    executor = agent_executor or CrewAiAgentExecutor()
    card = get_crewai_agent_card(base_url=base_url)
    return create_a2a_app(
        agent_card=card,
        agent_executor=executor,
        title="CrewAI A2A Service",
    )
