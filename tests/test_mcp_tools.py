"""Unit tests for MCP Server, AST Parser Tool, and SQLite Metadata Tool."""
import tempfile
from pathlib import Path
import unittest

from src.mcp.client import McpClientBridge
from src.mcp.server import (
    AstFileParserTool,
    McpServer,
    SqliteMetadataLookupTool,
)


class TestMcpTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_knowledge.db"
        self.server = McpServer(db_path=self.db_path)
        self.client = McpClientBridge(server=self.server)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_list_tools_conforms_to_mcp_schema(self):
        tools = self.client.list_available_tools()
        self.assertEqual(len(tools), 2)
        names = {t["name"] for t in tools}
        self.assertIn("ast_file_parser", names)
        self.assertIn("sqlite_metadata_lookup", names)
        for t in tools:
            self.assertIn("inputSchema", t)
            self.assertIn("description", t)

    def test_ast_file_parser_valid_code(self):
        sample_code = (
            "import os\n\n"
            "class SampleClass:\n"
            "    def method_one(self):\n"
            "        pass\n\n"
            "def standalone_func(x, y):\n"
            "    return x + y\n"
        )
        result = self.client.parse_python_ast(code_content=sample_code)
        self.assertTrue(result["is_valid_syntax"])
        self.assertEqual(len(result["classes"]), 1)
        self.assertEqual(result["classes"][0]["name"], "SampleClass")
        self.assertEqual(result["classes"][0]["methods"], ["method_one"])
        self.assertEqual(len(result["functions"]), 1)
        self.assertEqual(result["functions"][0]["name"], "standalone_func")
        self.assertIn("os", result["imports"])

    def test_ast_file_parser_syntax_error(self):
        bad_code = "def invalid_syntax(x: return x +"
        result = self.client.parse_python_ast(code_content=bad_code)
        self.assertFalse(result["is_valid_syntax"])
        self.assertIn("SyntaxError", result["error"])

    def test_sqlite_metadata_lookup(self):
        res = self.client.lookup_metadata(category="fastapi")
        self.assertGreater(res["found_count"], 0)
        self.assertTrue(any("crud" in r["key"].lower() for r in res["results"]))

    def test_sqlite_lookup_by_key(self):
        res = self.client.lookup_metadata(key="test_client")
        self.assertGreater(res["found_count"], 0)
        self.assertIn("pytest", res["results"][0]["category"])


if __name__ == "__main__":
    unittest.main()

