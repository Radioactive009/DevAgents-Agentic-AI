# DevAgents AGI: Autonomous Multi-Agent Software Engineering System

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-105%20passed-brightgreen.svg)](tests/)
[![Agent Frameworks](https://img.shields.io/badge/frameworks-Google%20ADK%20%7C%20CrewAI-orange.svg)](#dual-agentic-frameworks)
[![MCP Protocol](https://img.shields.io/badge/tools-Model%20Context%20Protocol%20(MCP)-purple.svg)](#model-context-protocol-mcp-integration)
[![Observability](https://img.shields.io/badge/observability-OpenTelemetry%20OTel-cyan.svg)](#observability-distributed-tracing--provenance)
[![Security](https://img.shields.io/badge/guardrails-PromptGuard%20Active-red.svg)](#security-guardrails--prompt-defense)

**DevAgents AGI** is an autonomous, multi-agent software engineering framework featuring a **deterministic self-healing repair loop**. 

Unlike single-prompt LLM code generators—which hallucinate success and lack validation—DevAgents decouples software development into specialized, truth-grounded AI agents. It integrates **Google ADK** for system architecture, **CrewAI** for coding and repair, an isolated **Pytest sandbox** for truth-grounded testing, a thread-safe **Blackboard pattern** for state management, **Model Context Protocol (MCP)** tools for AST inspection, and **OpenTelemetry** for cryptographic provenance.

---

## Interactive Presentation Dashboard

DevAgents includes a visual dashboard to demonstrate the agent pipeline, trace spans, and security guardrails:

```bash
# Launch the presentation dashboard in your browser
python run_dashboard.py
```
*Alternatively, double-click `dashboard.html` directly in your file explorer.*

---

## System Architecture

```mermaid
flowchart TD
    subgraph Sec["1. Security Guardrails (Req 8)"]
        UserReq["ProjectRequest"] --> Guard["PromptGuard\n(Jailbreak & Injection Defense)"]
        Guard --> VarEngine["Prompt Variance Engine\n(ReAct vs Few-Shot vs Personas)"]
    end

    subgraph Dual["2. Dual Framework Collaboration (Req 7)"]
        VarEngine --> ADK["Google ADK Architecture Agent\n[google-adk + LiteLLM + Groq]"]
        ADK --> BB["Blackboard Store (Must - Req 1)\nThread-Safe RLock State"]
        BB --> CrewCoder["CrewAI Coding Agent\nGenerates Workspace Files"]
    end

    subgraph MCP["3. External Tool Integration (Req 2)"]
        MCPServer["MCP Server (Official SDK 1.30.0)"]
        Tool1["Tool 1: ast_file_parser\n(Syntax & Symbol Extraction)"]
        Tool2["Tool 2: sqlite_metadata_lookup\n(SQLite Design Catalog)"]
        MCPClient["MCP Client Bridge\n(Type-Validation Callbacks)"]
        MCPServer --> Tool1 & Tool2
        MCPClient <--> MCPServer
    end

    subgraph Loop["4. Truth-Grounded Self-Healing Loop"]
        CrewCoder --> Pytest["Isolated Pytest Subprocess Runner"]
        Pytest --> Check{All Tests Pass?}
        Check -- Yes --> Completed["State: Completed / Verifying"]
        Check -- No --> Debugger["CrewAI Debugging Agent\n(Root Cause Diagnosis)"]
        Debugger --> Repairer["CrewAI Repair Agent\n(Minimal CodePatch)"]
        Repairer --> PatchVal["Deterministic Patch Validator\n& Atomic Backup Applier (.bak)"]
        PatchVal --> Pytest
    end

    subgraph Obs["5. Observability & Tracing (Req 9)"]
        OTel["OpenTelemetry Distributed Tracer\n(Parent/Child Hierarchy)"]
        TraceLog["logs/devagents_traces.jsonl\n(Cryptographic SHA-256 Provenance)"]
        OTel --> TraceLog
    end

    CrewCoder <--> MCPClient
    Repairer <--> MCPClient
    OTel -.-> Sec & Dual & MCP & Loop
```

---

## Key Engineering Pillars

### 1. Dual Agentic Frameworks (Google ADK & CrewAI)
* **Strict Constraint:** Uses **only** Google ADK and CrewAI; no unauthorized third-party agent frameworks.
* **Google ADK (`google-adk` 2.13.0):** Powers the [`ArchitectureAgent`](src/adk_architecture_agent.py). It uses `LiteLlm` connected to Groq (`qwen/qwen3.8-27b`) to synthesize structured Pydantic [`ArchitecturePlan`](src/models.py) objects.
* **CrewAI (`crewai` 1.15.30):** Powers developer, debugger, and repair agents specializing in file generation, stack-trace diagnosis, and minimal unified diff proposals.

### 2. State & Messaging: Blackboard (Must) vs. EventBus
* **Mandatory Blackboard (`src/blackboard.py`):** Acts as a thread-safe, transactional single-source-of-truth using Python's `threading.RLock`. Enables immediate state coherence during iterative self-repair loops.
* **Comparative EventBus (`src/messaging/event_bus.py`):** Implements an asynchronous, decoupled Pub/Sub architecture with event-sourced state projection.
* **Empirical Benchmark (`compare_messaging.py`):**
  
  | Evaluation Metric | Blackboard (Must) | EventBus (Pub/Sub) |
  |---|---|---|
  | **Sequential Latency (P95)** | **499.70 µs** | 119.90 µs |
  | **Concurrent Throughput (8 workers)** | **17,116 events/sec** | 43,671 events/sec |
  | **State Synchronization** | **Instantaneous (Zero Lag)** | Event-Sourced Reducer |
  | **Best Architectural Fit** | **Iterative Self-Repair Loops** | Distributed Microservices |

### 3. Model Context Protocol (MCP) Integration
Integrated using the official Anthropic/Linux Foundation `mcp` SDK (v1.30.0):
* **Tool 1: `ast_file_parser`:** Parses Python Abstract Syntax Trees (AST) safely without executing untrusted code. Extracts class definitions, function signatures, docstrings, and verifies syntax before patch application.
* **Tool 2: `sqlite_metadata_lookup`:** Queries an external SQLite database (`data/project_knowledge.db`) for standard API guidelines, Pytest client fixtures, and HTTP error code conventions.

### 4. Security Guardrails & Prompt Defense
* **`PromptGuard` (`src/security/prompt_guard.py`):** Pre-execution screening detecting:
  * **Prompt Injections & Jailbreaks:** System prompt leakages, instruction overrides, DAN mode, and fake XML/system tags.
  * **Toxic & Dangerous Content:** Malware generation, exploit payloads, and hazardous material requests.
* **Prompt Variance Engine (`src/prompts/variance_manager.py`):** Evaluates agent robustness across:
  * **Architectures:** ReAct (Thought $\to$ Action $\to$ Observation) vs. Few-Shot Demonstration vs. Direct Schema.
  * **Personas:** *Defensive Security Architect* vs. *High-Velocity Pragmatic Architect*.
* **Runtime Callbacks (`src/security/validation_callbacks.py`):** Enforces contract-level type-checking on tool return values before data ingestion.

### 5. Observability, Distributed Tracing & Cryptographic Provenance
* Built with **OpenTelemetry (`opentelemetry-api` & `opentelemetry-sdk`)**.
* Emits distributed trace spans into `logs/devagents_traces.jsonl`.
* **Span Hierarchy:** Root span `workflow_execution` with child spans `guardrail_scan`, `mcp_knowledge_lookup`, `initial_testing`, and `repair_retesting`.
* **Provenance Auditability:** Records exact model names, framework tags (`google-adk` vs `crewai`), prompt variance IDs, and cryptographic **SHA-256 hashes** of user prompts and generated code artifacts.

---

## Project Structure

```text
DevAgents_AGI/
├── compare_messaging.py         # Empirical benchmark: Blackboard vs EventBus
├── dashboard.html               # Interactive visual presentation dashboard
├── run_dashboard.py             # 1-click launcher for dashboard server
├── run_repair_loop.py           # End-to-end self-repair pipeline runner
├── requirements.txt             # Project dependencies
├── pytest.ini                   # Pytest test discovery configuration
│
├── data/
│   └── project_knowledge.db     # SQLite knowledge catalog for MCP Tool 2
│
├── logs/
│   ├── devagents_audit.jsonl    # Sanitized audit trail of state transitions
│   └── devagents_traces.jsonl   # OpenTelemetry distributed trace spans
│
├── src/
│   ├── models.py                # Core Pydantic schemas (State, Plan, TestResult)
│   ├── blackboard.py            # Central thread-safe Blackboard store
│   ├── adk_architecture_agent.py# Google ADK Architecture planning agent
│   ├── coding_agent.py          # CrewAI source code generation agent
│   ├── debugging_agent.py       # CrewAI failure diagnosis agent
│   ├── repair_agent.py          # CrewAI minimal patch proposal agent
│   ├── testing_agent.py         # Subprocess Pytest execution sandbox
│   ├── patch_validator.py       # Deterministic patch validation engine
│   ├── patch_applier.py         # Atomic file patching with .bak backup
│   ├── trace_context.py         # Monotonic stage execution timing
│   ├── audit_logger.py          # Append-only JSONL audit logger
│   │
│   ├── mcp/                     # Model Context Protocol (MCP)
│   │   ├── server.py            # MCP Server (AST parser & SQLite tools)
│   │   └── client.py            # MCP Client Bridge with validation callbacks
│   │
│   ├── messaging/               # Context sharing architectures
│   │   ├── base.py              # Abstract messaging interface
│   │   ├── blackboard_adapter.py# Blackboard messaging adapter
│   │   └── event_bus.py         # Decoupled Pub/Sub EventBus
│   │
│   ├── security/                # System hardening & validation
│   │   ├── prompt_guard.py      # Prompt injection & toxicity guardrails
│   │   └── validation_callbacks.py # Tool return type checking callbacks
│   │
│   ├── prompts/                 # Prompt engineering
│   │   └── variance_manager.py  # ReAct vs Few-Shot vs Persona engine
│   │
│   └── observability/           # Distributed tracing
│       └── tracer.py            # OpenTelemetry Tracer & JSONL Span Exporter
│
└── tests/                       # Complete Test Suite (105 tests)
    ├── test_adk_agent.py        # Google ADK agent unit tests
    ├── test_guardrails.py       # PromptGuard & validation callback tests
    ├── test_mcp_tools.py        # MCP server & client integration tests
    ├── test_messaging.py        # Blackboard & EventBus messaging tests
    ├── test_observability.py    # OpenTelemetry trace span tests
    ├── test_blackboard.py       # Blackboard state mutation tests
    ├── test_coding_agent.py     # Sandbox & path safety tests
    ├── test_debugging_agent.py  # Debug report schema tests
    ├── test_patch_validator.py  # Patch verification tests
    ├── test_patch_applier.py    # Atomic backup & replacement tests
    ├── test_repair_agent.py     # Repair proposal tests
    ├── test_testing_agent.py    # Pytest runner tests
    └── test_models.py           # Pydantic data model tests
```

---

## Quickstart & Installation

### 1. Clone the Repository & Set Up Virtual Environment
```bash
git clone https://github.com/Radioactive009/DevAgents-Agentic-AI.git
cd DevAgents-Agentic-AI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows Command Prompt:
.\.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Credentials
Create a `.env` file in the project root:
```ini
GROQ_API_KEY=your_groq_api_key_here
```

---

## Running the System

### 1. Execute the Full Automated Test Suite (105 Tests)
```bash
python -m pytest -v
```

### 2. Run the End-to-End Self-Repair Loop
Executes input screening, MCP tool inspection, Pytest truth-grounding, and OpenTelemetry trace emission:
```bash
python run_repair_loop.py
```

### 3. Run the Messaging Architecture Comparison
Runs empirical benchmarks comparing Blackboard vs. EventBus across 1,200 concurrent events:
```bash
python compare_messaging.py
```

### 4. Launch the Interactive Visual Dashboard
Opens the presentation dashboard in your web browser:
```bash
python run_dashboard.py
```

---

## Minimum Standardization Requirements Compliance

| # | Requirement | Status | Deliverables & Verification |
|---|---|:---:|---|
| **1** | **Context Sharing & State Updates** | ✅ **100%** | Thread-safe `Blackboard` (`src/blackboard.py`), EventBus (`src/messaging/event_bus.py`), and `compare_messaging.py`. |
| **2** | **Tool Integration using MCP** | ✅ **100%** | Official `mcp` SDK (v1.30.0), `ast_file_parser`, and `sqlite_metadata_lookup` (`src/mcp/`). |
| **3** | **Structured Output using Pydantic** | ✅ **100%** | Pydantic BaseModels across all agents (`ArchitecturePlan`, `CodePatch`, `TestResult`, `ProjectState`). |
| **4** | **Agentic Design Patterns** | ✅ **100%** | Blackboard Pattern, Evaluator-Optimizer / Self-Correction Loop, and Guarded Execution. |
| **5** | **Task Monitoring & Callbacks** | ✅ **100%** | `AuditLogger` (JSONL), `TraceContext`, and `DataValidationCallback` (`src/security/validation_callbacks.py`). |
| **7** | **Dual Frameworks (CrewAI & ADK Only)**| ✅ **100%** | Google ADK (`src/adk_architecture_agent.py`) + CrewAI (`src/coding_agent.py`). Strictly no other frameworks. |
| **8** | **System Security & Guardrails** | ✅ **100%** | `PromptGuard` (jailbreaks/injections), runtime validation callbacks, path traversal blocks, and ReAct/Few-Shot prompt variances. |
| **9** | **Observability & Tracing** | ✅ **100%** | OpenTelemetry tracer emitting parent/child spans with cryptographic SHA-256 hashes (`logs/devagents_traces.jsonl`). |

---

## License

This project is licensed under the Apache 2.0 License.
