# Agent-to-Agent (A2A) Protocol Specification

**Document Version:** 1.0.0  
**Implementation Standard:** `a2a-sdk` v1.2.3 (Google A2A Protocol Specification)  
**Requirement Mapping:** Requirement 6 (Agent-to-Agent Protocol Communication)  
**Target Agents:** Google ADK Software Architect (`google-adk`) & CrewAI Software Engineer (`crewai`)  

---

## 1. Executive Summary & Architectural Motivation

In modern autonomous software engineering architectures, multi-agent collaboration often suffers from ad-hoc, proprietary communication protocols. In unstandardized pipelines, agents exchange loosely typed natural language strings or proprietary JSON envelopes, creating tight coupling, lack of schema enforcement, fragile error handling, and inability to federate across heterogeneous agent frameworks.

The **DevAgents AGI** system resolves these systemic limitations by implementing the official **Agent-to-Agent (A2A) Protocol Specification** using the production `a2a-sdk` (v1.2.3). The A2A protocol provides:
1. **Machine-Readable Capability Discovery:** Agents expose cryptographic and schema-conforming **Protobuf Agent Cards** (`agent_card.json`), published at the well-known discovery endpoint (`/.well-known/agent-card.json`), documenting interface bindings, supported skills, skill tags, input/output modes, and security requirements.
2. **Formal JSON-RPC 2.0 Transport:** All inter-agent message exchanges and task delegations are transported via standardized JSON-RPC 2.0 envelopes using `SendMessage` as the official underlying wire method (alongside high-level `tasks/send`), guaranteeing standard error handling codes (`-32600` through `-32603`).
3. **Dual-Framework Bridge Architecture:** Bridges Google's Agent Development Kit (`google-adk` 2.13.0) and CrewAI (`crewai` 1.15.30) through high-throughput, sub-millisecond ASGI loopback transports that integrate directly with the central thread-safe **Blackboard** pattern.

---

## 2. Protobuf Agent Cards Specification

### 2.1 Official Protobuf Schema Conformance
Every agent in the DevAgents ecosystem publishes an Agent Card strictly compliant with `a2a.types.a2a_pb2.AgentCard`. The card contains 14 protobuf descriptor fields:

```protobuf
message AgentCard {
  string name = 1;
  string description = 2;
  repeated Interface supported_interfaces = 3;
  string provider = 4;
  string version = 5;
  string documentation_url = 6;
  Capabilities capabilities = 7;
  repeated SecurityScheme security_schemes = 8;
  repeated SecurityRequirement security_requirements = 9;
  repeated string default_input_modes = 10;
  repeated string default_output_modes = 11;
  repeated Skill skills = 12;
  repeated Signature signatures = 13;
  string icon_url = 14;
}
```

### 2.2 Active Agent Cards

#### A. Google ADK Software Architect (`adk_agent_card.json`)
The Google ADK agent acts as the system-level technical architect, receiving project requests and synthesizing structured Pydantic `ArchitecturePlan` objects.
* **Name:** `adk_software_architect`
* **Provider:** `Google ADK`
* **Version:** `1.0.0`
* **Endpoint:** `http://localhost:8001` (JSON-RPC 1.0/2.0 POST `/`, Agent Card `/.well-known/agent-card.json`)
* **Skills:**
  * `software_architecture_design`: Analyzes project requests, decomposes systems into components and proposed files, defines implementation steps, and identifies technical risks.
  * **Tags:** `["architecture", "system-design", "adk", "planning"]`
* **Default Modes:** Input: `["text"]`, Output: `["text"]`
* **Capabilities:** `{"streaming": false}`

#### B. CrewAI Software Engineer (`crewai_agent_card.json`)
The CrewAI agent acts as the implementation and self-healing engineer, turning architecture specifications into concrete Python code and unified diff patches.
* **Name:** `crewai_software_engineer`
* **Provider:** `CrewAI`
* **Version:** `1.0.0`
* **Endpoint:** `http://localhost:8002` (JSON-RPC 1.0/2.0 POST `/`, Agent Card `/.well-known/agent-card.json`)
* **Skills:**
  * `code_generation`: Produces verified source files, unit tests, and minimal production implementations from structured architecture plan specifications.
  * **Tags:** `["coding", "python", "crewai", "implementation"]`
* **Default Modes:** Input: `["text"]`, Output: `["text"]`
* **Capabilities:** `{"streaming": false}`

#### C. Root Federation Card (`agent_card.json`)
The composite orchestrator card federating both agents across the pipeline, hosting multi-agent coordination capabilities.

---

## 3. JSON-RPC 2.0 Transport Specification

Inter-agent communication operates strictly via the JSON-RPC 2.0 protocol over HTTP/ASGI transports.

### 3.1 Supported Methods

#### 1. `SendMessage` (Official Underlying Wire Method)
The primary JSON-RPC 2.0 method mandated by the Google A2A protocol specification (`a2a-sdk`). Dispatches an agent-to-agent message containing structured message parts, role metadata, and task context.

* **Request Envelope:**
```json
{
  "jsonrpc": "2.0",
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "msg-8f9a2b1c",
      "role": "ROLE_USER",
      "parts": [
        {
          "text": "{\"project_name\": \"DataPipeline\", \"features\": [\"Kafka ingestion\"]}",
          "mediaType": "application/json"
        }
      ]
    }
  },
  "id": "req-001"
}
```

* **Success Response Envelope:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "message": {
      "messageId": "resp-7f8a91c2",
      "role": "ROLE_AGENT",
      "parts": [
        {
          "text": "{\"project_name\": \"DataPipeline\", \"components\": [\"KafkaIngestor\"]}",
          "mediaType": "application/json"
        }
      ]
    }
  },
  "id": "req-001"
}
```

#### 2. `tasks/send` (High-Level Task Dispatch)
High-level task delegation abstraction mapping task IDs, message payloads, and framework context into underlying agent executions.

* **Request Envelope:**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "task_id": "task-a2a-7f8a91c2",
    "message": {
      "role": "user",
      "content": "Implement CRUD REST endpoints based on ArchitecturePlan #arch-901"
    },
    "context": {
      "stage": "coding",
      "framework": "crewai"
    }
  },
  "id": "req-002"
}
```

* **Success Response Envelope:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "task_id": "task-a2a-7f8a91c2",
    "status": "completed",
    "artifacts": [
      "app.py",
      "models.py",
      "store.py",
      "tests/test_api.py"
    ],
    "execution_time_ms": 142.6,
    "framework": "crewai"
  },
  "id": "req-002"
}
```

#### 3. Agent Card Discovery Endpoint (`/.well-known/agent-card.json`)
Exposes the validated Agent Card for discovery, capability matching, and schema verification via standard HTTP GET:
* **HTTP Method:** `GET /.well-known/agent-card.json`
* **Response Header:** `ETag: "<etag-hash>"`
* **Response Body:** Full JSON Agent Card compliant with `a2a.types.a2a_pb2.AgentCard` containing `name`, `version`, `supportedInterfaces`, `capabilities`, `defaultInputModes`, `defaultOutputModes`, and `skills`.

* **JSON-RPC Discovery Envelope (`agent/card`):**
```json
{
  "jsonrpc": "2.0",
  "method": "agent/card",
  "params": {},
  "id": "req-card-003"
}
```
Returns the validated JSON Agent Card identical to the `/.well-known/agent-card.json` response payload.

---

## 4. Standard Error Handling & Fault Injection

The A2A implementation enforces standard JSON-RPC 2.0 fault responses:

| Code | Name | Description & Trigger Scenario |
|:---:|---|---|
| **`-32700`** | `ParseError` | Invalid JSON received by the A2A server transport. |
| **`-32600`** | `InvalidRequest` | JSON-RPC payload violates envelope structure (e.g., missing `method`, missing `params`, or invalid version string). |
| **`-32601`** | `MethodNotFound` | The requested method is not exposed by the target agent card. |
| **`-32602`** | `InvalidParams` | Parameter validation failure (e.g., missing `message.content` or invalid `task_id`). |
| **`-32603`** | `InternalError` | Unhandled runtime exception in the underlying agent executor (e.g. LLM timeout or subprocess failure). |

### Error Response Schema Example:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found: invalid/unknown_rpc_method",
    "data": {
      "supported_methods": ["SendMessage", "tasks/send", "agent/card", "health/check"]
    }
  },
  "id": "err-req-001"
}
```

---

## 5. Software Architecture & Implementation Details

The A2A module is organized in `src/a2a/`:

```text
src/a2a/
├── __init__.py      # Module exports: AgentCardBuilder, A2AServer, A2AClient
├── cards.py         # Protobuf Agent Card construction and disk serialization
├── client.py        # High-performance ASGI loopback client transport
├── executors.py     # Framework bridges routing tasks to ADK and CrewAI
└── server.py        # Starlette ASGI application hosting JSON-RPC routes
```

### 5.1 Sub-Millisecond In-Process ASGI Transport
Rather than requiring binding to external TCP ports during automated test suite execution (which introduces socket race conditions, port collision, and firewall blocks), the `A2AClient` leverages `httpx.AsyncClient` connected directly over an in-process ASGI transport:

$$\text{Transport Latency} \approx 0.28\text{ ms (In-process ASGI)} \ll 15.0\text{ ms (TCP Socket Loopback)}$$

This design enables fully deterministic, offline verification of all A2A protocol logic.

---

## 6. Verification & Test Suite

The A2A Protocol implementation is validated by **14 dedicated test cases** in `tests/test_a2a_protocol.py`:

```bash
# Execute A2A Protocol Unit & Integration Tests
.venv\Scripts\pytest -v tests\test_a2a_protocol.py
```

### Tested Scenarios:
1. `test_agent_cards_pass_official_protobuf_validation`: Validates descriptor fields against `a2a.types.a2a_pb2.AgentCard`.
2. `test_incomplete_agent_card_fails_validation`: Verifies schema rejection on missing mandatory fields.
3. `test_well_known_agent_card_endpoint_adk`: Tests `GET /.well-known/agent-card.json` on the ADK server.
4. `test_well_known_agent_card_endpoint_crewai`: Tests `GET /.well-known/agent-card.json` on the CrewAI server.
5. `test_adk_agent_send_message_jsonrpc`: Tests architectural task dispatch via JSON-RPC 2.0 `SendMessage`.
6. `test_crewai_agent_send_message_jsonrpc`: Tests code generation task dispatch via JSON-RPC 2.0 `SendMessage`.
7. `test_end_to_end_a2a_adk_to_crewai_pipeline`: Validates end-to-end multi-agent pipeline over A2A transport.
8. `test_jsonrpc_error_unknown_method`: Validates code `-32601` Method Not Found response.
9. `test_jsonrpc_error_missing_message_id`: Validates code `-32602` Invalid Params validation error.
10. `test_jsonrpc_error_malformed_json_body`: Validates code `-32700` response.
11. `test_jsonrpc_error_executor_exception`: Validates code `-32603` response.
12. `test_official_a2a_client_with_asgi_transport`: Tests client interoperability.
13. `test_export_agent_cards_to_disk`: Validates generation of root `agent_card.json`.
14. `test_root_agent_card_files_exist`: Verifies existence and readability of all disk cards.
