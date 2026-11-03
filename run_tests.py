"""
DevAgents AGI — Master Test Suite Runner.

Executes all 105 unit and integration tests across all project modules:
- Blackboard & State Management
- Google ADK Architecture Agent
- CrewAI Coding, Debugging, and Repair Agents
- MCP Tools (AST Parser & SQLite Metadata)
- Messaging Architectures (Blackboard & EventBus)
- Security Guardrails & Prompt Injection Defenses
- OpenTelemetry Distributed Tracing & Provenance
"""

import os
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

import pytest


def main():
    print("=" * 65)
    print("DEVAGENTS AGI — RUNNING ALL 105 UNIT & INTEGRATION TESTS")
    print("=" * 65)

    # Run pytest across the tests directory with verbose reporting
    exit_code = pytest.main(["-v", "tests"])

    print("\n" + "=" * 65)
    if exit_code == 0:
        print("RESULT: ALL TESTS PASSED SUCCESSFULLY! (100% HEALTH)")
    else:
        print(f"RESULT: Tests finished with exit code {exit_code}")
    print("=" * 65)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
