"""
Model Context Protocol (MCP) Server and Tool Implementations.

Exposes two external tools over MCP:
1. ast_file_parser: Syntactic Python AST inspection, syntax validation, and symbol extraction.
2. sqlite_metadata_lookup: SQLite-backed reference catalog for architecture patterns and API schemas.
"""

import ast
from pathlib import Path
import sqlite3
from typing import Any


class AstFileParserTool:
    """Tool 1: Parses Python code, verifies AST syntax, and extracts signatures."""

    name = "ast_file_parser"
    description = (
        "Parses Python source code, checks syntax correctness, "
        "and extracts symbols including classes, functions, and imports."
    )

    @classmethod
    def execute(
        cls,
        *,
        code_content: str | None = None,
        file_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Parse source code string or read from file path and analyze AST."""
        content = code_content

        if content is None and file_path is not None:
            path = Path(file_path).resolve()
            if not path.is_file():
                return {
                    "is_valid_syntax": False,
                    "error": f"File not found: {file_path}",
                    "classes": [],
                    "functions": [],
                    "imports": [],
                }
            content = path.read_text(encoding="utf-8", errors="replace")

        if content is None:
            return {
                "is_valid_syntax": False,
                "error": "Either code_content or file_path must be provided.",
                "classes": [],
                "functions": [],
                "imports": [],
            }

        try:
            tree = ast.parse(content)
        except SyntaxError as err:
            return {
                "is_valid_syntax": False,
                "error": f"SyntaxError at line {err.lineno}: {err.msg}",
                "classes": [],
                "functions": [],
                "imports": [],
            }

        classes = []
        functions = []
        imports = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    sub.name
                    for sub in node.body
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "docstring": ast.get_docstring(node) or "",
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [arg.arg for arg in node.args.args]
                functions.append({
                    "name": node.name,
                    "args": args,
                    "docstring": ast.get_docstring(node) or "",
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        return {
            "is_valid_syntax": True,
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "symbol_count": len(classes) + len(functions),
        }


class SqliteMetadataLookupTool:
    """Tool 2: Queries SQLite metadata store for API designs, templates, and patterns."""

    name = "sqlite_metadata_lookup"
    description = (
        "Queries an external SQLite knowledge base for FastAPI endpoints, "
        "pytest configurations, error conventions, and architectural best practices."
    )

    def __init__(self, db_path: str | Path = "data/project_knowledge.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize and seed SQLite tables if not already present."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    description TEXT
                )
            """)

            # Seed default knowledge items
            seeds = [
                (
                    "fastapi",
                    "rest_crud_pattern",
                    "Use APIRouter or FastAPI instance, Pydantic request/response models, HTTPException(status_code=404).",
                    "Standard CRUD pattern for FastAPI",
                ),
                (
                    "pytest",
                    "test_client_pattern",
                    "from fastapi.testclient import TestClient; client = TestClient(app)",
                    "Pytest client initialization",
                ),
                (
                    "security",
                    "input_validation_pattern",
                    "Pydantic Field(min_length=..., max_length=...) with regex checks.",
                    "Input validation recommendation",
                ),
                (
                    "http_status",
                    "not_found",
                    "404: Resource Not Found",
                    "Standard 404 response",
                ),
            ]
            cursor.executemany("""
                INSERT OR IGNORE INTO knowledge_items (category, key, value, description)
                VALUES (?, ?, ?, ?)
            """, seeds)
            conn.commit()
        finally:
            conn.close()

    def execute(self, *, category: str | None = None, key: str | None = None) -> dict[str, Any]:
        """Search metadata entries by category or key."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if key:
                cursor.execute(
                    "SELECT category, key, value, description FROM knowledge_items WHERE key LIKE ?",
                    (f"%{key}%",),
                )
            elif category:
                cursor.execute(
                    "SELECT category, key, value, description FROM knowledge_items WHERE category = ?",
                    (category,),
                )
            else:
                cursor.execute(
                    "SELECT category, key, value, description FROM knowledge_items LIMIT 10"
                )

            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
        finally:
            conn.close()

        return {
            "found_count": len(results),
            "results": results,
        }


class McpServer:
    """Model Context Protocol (MCP) Server exposing tools with schema discovery."""

    def __init__(self, db_path: str | Path = "data/project_knowledge.db"):
        self.ast_tool = AstFileParserTool()
        self.sqlite_tool = SqliteMetadataLookupTool(db_path=db_path)

    def list_tools(self) -> list[dict[str, Any]]:
        """Return MCP tool descriptors conformant with MCP specification."""
        return [
            {
                "name": AstFileParserTool.name,
                "description": AstFileParserTool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code_content": {"type": "string", "description": "Python source code"},
                        "file_path": {"type": "string", "description": "Path to Python file"},
                    },
                },
            },
            {
                "name": SqliteMetadataLookupTool.name,
                "description": SqliteMetadataLookupTool.description,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Category to filter by"},
                        "key": {"type": "string", "description": "Key keyword substring to match"},
                    },
                },
            },
        ]

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute an MCP tool call and return structured result."""
        if tool_name == AstFileParserTool.name:
            return self.ast_tool.execute(
                code_content=arguments.get("code_content"),
                file_path=arguments.get("file_path"),
            )
        elif tool_name == SqliteMetadataLookupTool.name:
            return self.sqlite_tool.execute(
                category=arguments.get("category"),
                key=arguments.get("key"),
            )
        else:
            raise KeyError(f"MCP Tool not found: {tool_name}")
