"""
DevAgents Visual Dashboard Launcher.

Opens the interactive project dashboard in your web browser to present
to your professor, visualizing:
1. Dual Agent Framework (Google ADK & CrewAI)
2. Thread-Safe Blackboard State
3. OpenTelemetry Distributed Traces (logs/devagents_traces.jsonl)
4. MCP External Tools (AST Parser & SQLite Lookup)
5. Security Guardrail Sandbox (Prompt Injection & Toxic Defense)
6. Messaging Architecture Comparison (Blackboard vs EventBus)
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8080
DASHBOARD_FILE = Path(__file__).resolve().parent / "dashboard.html"


def main():
    if not DASHBOARD_FILE.is_file():
        print(f"Error: dashboard.html not found at {DASHBOARD_FILE}")
        return

    dashboard_url = f"http://localhost:{PORT}/dashboard.html"
    print("=" * 65)
    print("DEVAGENTS AGI — INTERACTIVE VISUAL DASHBOARD")
    print("=" * 65)
    print(f"Starting local presentation server on port {PORT}...")
    print(f"Dashboard URL: {dashboard_url}")
    print("Opening in your web browser automatically...")
    print("Press Ctrl+C in this terminal when you want to stop the server.")
    print("=" * 65)

    # Open dashboard in browser
    webbrowser.open(dashboard_url)

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard server stopped.")


if __name__ == "__main__":
    main()

