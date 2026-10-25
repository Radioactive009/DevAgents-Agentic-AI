
import tempfile
import unittest
from pathlib import Path

from src.coding_agent import (
    CodeGenerationResult,
    GeneratedFile,
    validate_relative_path,
    write_generated_files,
)


class TestCodingAgentSafety(unittest.TestCase):

    def test_accepts_safe_relative_path(self):
        self.assertEqual(
            validate_relative_path("tests/test_app.py"),
            "tests/test_app.py",
        )

    def test_rejects_parent_directory_traversal(self):
        with self.assertRaises(ValueError):
            validate_relative_path("../outside.py")

    def test_rejects_absolute_path(self):
        with self.assertRaises(ValueError):
            validate_relative_path("C:\\outside.py")

    def test_rejects_hidden_files(self):
        with self.assertRaises(ValueError):
            validate_relative_path(".env")

    def test_writes_file_inside_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "generated"

            result = CodeGenerationResult(
                summary="Generated a simple application.",
                files=[
                    GeneratedFile(
                        path="app.py",
                        content="print('Hello from DevAgents')\n",
                    )
                ],
            )

            written = write_generated_files(result, workspace)

            self.assertEqual(written, ["app.py"])
            self.assertEqual(
                (workspace / "app.py").read_text(encoding="utf-8"),
                "print('Hello from DevAgents')\n",
            )

    def test_refuses_to_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            existing_file = workspace / "app.py"
            existing_file.write_text("original", encoding="utf-8")

            result = CodeGenerationResult(
                summary="Test overwrite protection.",
                files=[
                    GeneratedFile(
                        path="app.py",
                        content="replacement",
                    )
                ],
            )

            with self.assertRaises(FileExistsError):
                write_generated_files(result, workspace)

            self.assertEqual(
                existing_file.read_text(encoding="utf-8"),
                "original",
            )

    def test_rejects_all_files_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)

            result = CodeGenerationResult(
                summary="Test validation before writing.",
                files=[
                    GeneratedFile(path="safe.py", content="print('safe')"),
                    GeneratedFile(path="../escape.py", content="unsafe"),
                ],
            )

            with self.assertRaises(ValueError):
                write_generated_files(result, workspace)

            self.assertFalse((workspace / "safe.py").exists())


if __name__ == "__main__":
    unittest.main()
