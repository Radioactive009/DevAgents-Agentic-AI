"""
MCP Client Bridge.

Connects agents to the MCP Server, validates tool returns using runtime
callbacks, and provides native tool call wrappers for both CrewAI and Google ADK.
"""

from typing import Any, Callable
from src.mcp.server import McpServer
from src.security.validation_callbacks import ToolReturnValidator


class McpClientBridge:
    """Client bridge interacting with MCP tools with integrated safety validation."""

    def __init__(self, server: McpServer | None = None):
        self._server = server or McpServer()

    def list_available_tools(self) -> list[dict[str, Any]]:
        """Query the MCP server for available tools."""
        return self._server.list_tools()

    def invoke_tool(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Invoke an MCP tool and validate that its return conforms to contract."""
        raw_result = self._server.call_tool(tool_name, kwargs)

        # Safety & type validation callback (Req 8)
        validated_result = ToolReturnValidator.validate_type(
            tool_name=tool_name,
            result=raw_result,
            expected_type=dict,
        )
        return validated_result

    def parse_python_ast(
        self,
        *,
        code_content: str | None = None,
        file_path: str | None = None,
    ) -> dict[str, Any]:
        """High-level client method to invoke the MCP ast_file_parser tool."""
        return self.invoke_tool(
            "ast_file_parser",
            code_content=code_content,
            file_path=file_path,
        )

    def lookup_metadata(
        self,
        *,
        category: str | None = None,
        key: str | None = None,
    ) -> dict[str, Any]:
        """High-level client method to invoke the MCP sqlite_metadata_lookup tool."""
        return self.invoke_tool(
            "sqlite_metadata_lookup",
            category=category,
            key=key,
        )

    def get_crewai_tools(self) -> list[Callable[..., str]]:
        """Export MCP tools as native callable functions for CrewAI agents."""
        def mcp_ast_parser_tool(code: str) -> str:
            """Inspect Python code AST syntax and extract classes/functions."""
            import json
            result = self.parse_python_ast(code_content=code)
            return json.dumps(result)

        def mcp_metadata_lookup_tool(keyword: str) -> str:
            """Query SQLite database for architectural reference patterns."""
            import json
            result = self.lookup_metadata(key=keyword)
            return json.dumps(result)

        mcp_ast_parser_tool.__name__ = "mcp_ast_parser_tool"
        mcp_metadata_lookup_tool.__name__ = "mcp_metadata_lookup_tool"

        return [mcp_ast_parser_tool, mcp_metadata_lookup_tool]

