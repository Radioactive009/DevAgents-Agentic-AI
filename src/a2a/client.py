"""
A2A Client Communication Utilities.

Provides high-level client interfaces for discovering and communicating
with agents over JSON-RPC 2.0 conforming to a2a-sdk v1.2.3.
"""

from typing import Any
import uuid

import httpx

from a2a.client import Client, ClientConfig, create_client
from a2a.types import AgentCard


async def create_a2a_client(
    card_or_url: AgentCard | str,
    httpx_client: httpx.AsyncClient | None = None,
) -> Client:
    """Create an official A2A Client from an AgentCard or well-known endpoint URL.

    Allows injecting an in-memory `httpx.AsyncClient(transport=ASGITransport(app))`
    for 100% offline testing.
    """
    config = ClientConfig(streaming=False, httpx_client=httpx_client)
    return await create_client(card_or_url, client_config=config)


async def send_a2a_message(
    sender_card: AgentCard | None,
    receiver_url: AgentCard | str,
    text_payload: str,
    httpx_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Send an A2A JSON-RPC 2.0 SendMessage request to a target agent.

    Args:
        sender_card: Optional AgentCard of the sender agent.
        receiver_url: Target AgentCard or URL endpoint string.
        text_payload: Message string payload (plain text or serialized JSON).
        httpx_client: Optional httpx.AsyncClient (e.g. with ASGITransport).

    Returns:
        JSON-RPC 2.0 response dictionary containing 'result' or 'error',
        augmented with convenience fields ('response_text', 'text').
    """
    # 1. Determine target URL / endpoint
    target_url = "/"
    if isinstance(receiver_url, AgentCard):
        if receiver_url.supported_interfaces:
            target_url = receiver_url.supported_interfaces[0].url
    elif isinstance(receiver_url, str):
        target_url = receiver_url

    # 2. Construct JSON-RPC 2.0 SendMessage payload
    message_id = str(uuid.uuid4())
    rpc_id = str(uuid.uuid4())
    body = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": "SendMessage",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "ROLE_USER",
                "parts": [
                    {
                        "text": text_payload,
                        "mediaType": "application/json",
                    }
                ],
            }
        },
    }
    headers = {
        "A2A-Version": "1.0",
        "Content-Type": "application/json",
    }

    # 3. Dispatch via supplied httpx_client or create temporary client
    if httpx_client is not None:
        # If client has base_url or relative path
        endpoint = target_url if target_url.startswith("http") else "/"
        if hasattr(httpx_client, "base_url") and httpx_client.base_url:
            endpoint = "/"
        response = await httpx_client.post(endpoint, json=body, headers=headers)
        data: dict[str, Any] = response.json()
    else:
        async with httpx.AsyncClient(base_url=target_url if target_url.startswith("http") else None) as client:
            endpoint = target_url if not target_url.startswith("http") else "/"
            response = await client.post(endpoint, json=body, headers=headers)
            data = response.json()

    # 4. Augment with top-level helper shortcuts
    if "result" in data and isinstance(data["result"], dict):
        result_payload = data["result"]
        msg = result_payload.get("message", {})
        parts = msg.get("parts", [])
        if parts and isinstance(parts[0], dict):
            extracted_text = parts[0].get("text", "")
            data["response_text"] = extracted_text
            data["text"] = extracted_text

    return data
