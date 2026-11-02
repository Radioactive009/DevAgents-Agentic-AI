"""Unit tests for OpenTelemetry distributed tracing and provenance tracking."""
import json
from pathlib import Path
import tempfile
import unittest

from src.observability.tracer import DevAgentsTracer


class TestObservabilityTracer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.trace_file = Path(self.temp_dir.name) / "test_traces.jsonl"
        self.tracer = DevAgentsTracer(trace_path=self.trace_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_single_span_emission(self):
        with self.tracer.start_span(
            name="test_stage_span",
            stage="testing",
            framework="google-adk",
            model="groq/qwen/qwen3.8-27b",
            prompt_variant="react",
            input_data="sample prompt content",
        ) as span:
            span.set_attribute("custom_attr", 42)

        self.assertTrue(self.trace_file.exists())
        lines = [line for line in self.trace_file.read_text(encoding="utf-8").splitlines() if line]
        self.assertEqual(len(lines), 1)

        record = json.loads(lines[0])
        self.assertEqual(record["name"], "test_stage_span")
        self.assertEqual(record["status"]["status_code"], "OK")
        self.assertEqual(record["attributes"]["devagents.stage"], "testing")
        self.assertEqual(record["attributes"]["provenance.framework"], "google-adk")
        self.assertEqual(record["attributes"]["provenance.model"], "groq/qwen/qwen3.8-27b")
        self.assertEqual(record["attributes"]["provenance.prompt_variant"], "react")
        self.assertIn("provenance.input_hash", record["attributes"])
        self.assertEqual(record["attributes"]["custom_attr"], 42)
        self.assertGreater(record["duration_ms"], 0.0)

    def test_nested_parent_child_spans(self):
        with self.tracer.start_span("root_workflow", stage="pipeline") as root:
            with self.tracer.start_span("child_adk_architecture", stage="architecture", framework="google-adk"):
                pass
            with self.tracer.start_span("child_crewai_coding", stage="coding", framework="crewai"):
                pass

        lines = [line for line in self.trace_file.read_text(encoding="utf-8").splitlines() if line]
        self.assertEqual(len(lines), 3)

        records = [json.loads(line) for line in lines]
        # Child spans export first when exited, root span exports last
        child_spans = [r for r in records if r["name"].startswith("child_")]
        root_span = next(r for r in records if r["name"] == "root_workflow")

        for child in child_spans:
            self.assertEqual(child["parent_span_id"], root_span["span_id"])
            self.assertEqual(child["trace_id"], root_span["trace_id"])


if __name__ == "__main__":
    unittest.main()

