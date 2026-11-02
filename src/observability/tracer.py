"""
OpenTelemetry Distributed Tracing and Provenance Engine.

Emits structured OpenTelemetry spans to an append-only JSONL trace log
(logs/devagents_traces.jsonl). Captures deep provenance for agent runs:
- Model and framework provenance (Google ADK vs CrewAI)
- Prompt architecture variant (ReAct vs Few-Shot vs Direct)
- SHA-256 cryptographic hashes of prompt inputs and generated outputs
- Precise stage timings and parent-child span hierarchy
"""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode


class JsonFileSpanExporter(SpanExporter):
    """Custom OpenTelemetry Span Exporter appending JSON objects to a trace file."""

    def __init__(self, trace_file_path: str | Path = "logs/devagents_traces.jsonl"):
        self.path = Path(trace_file_path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def export(self, spans: tuple[ReadableSpan, ...]) -> SpanExportResult:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                for s in spans:
                    span_record = {
                        "name": s.name,
                        "trace_id": format(s.context.trace_id, "032x"),
                        "span_id": format(s.context.span_id, "016x"),
                        "parent_span_id": (
                            format(s.parent.span_id, "016x") if s.parent else None
                        ),
                        "start_time_ns": s.start_time,
                        "end_time_ns": s.end_time,
                        "duration_ms": (
                            round((s.end_time - s.start_time) / 1_000_000, 3)
                            if s.end_time and s.start_time
                            else 0.0
                        ),
                        "status": {
                            "status_code": s.status.status_code.name,
                            "description": s.status.description,
                        },
                        "attributes": dict(s.attributes or {}),
                    }
                    f.write(json.dumps(span_record, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


class DevAgentsTracer:
    """Singleton wrapper configuring and managing OpenTelemetry distributed spans."""

    def __init__(self, trace_path: str | Path = "logs/devagents_traces.jsonl"):
        self.resource = Resource.create({
            "service.name": "devagents-agi",
            "service.version": "1.0.0",
        })
        self.provider = TracerProvider(resource=self.resource)
        self.exporter = JsonFileSpanExporter(trace_file_path=trace_path)
        self.provider.add_span_processor(SimpleSpanProcessor(self.exporter))
        self.tracer = self.provider.get_tracer("devagents.core", "1.0.0")

    @staticmethod
    def compute_sha256(content: str) -> str:
        """Calculate SHA-256 fingerprint of prompt or artifact for provenance."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @contextmanager
    def start_span(
        self,
        name: str,
        stage: str,
        *,
        framework: str | None = None,
        model: str | None = None,
        prompt_variant: str | None = None,
        input_data: Any | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[trace.Span]:
        """Context manager initiating an OpenTelemetry span with provenance tags."""
        span_attrs = dict(attributes or {})
        span_attrs["devagents.stage"] = stage

        if framework:
            span_attrs["provenance.framework"] = framework
        if model:
            span_attrs["provenance.model"] = model
        if prompt_variant:
            span_attrs["provenance.prompt_variant"] = prompt_variant
        if input_data is not None:
            serialized_input = (
                input_data if isinstance(input_data, str) else str(input_data)
            )
            span_attrs["provenance.input_hash"] = self.compute_sha256(serialized_input)

        with self.tracer.start_as_current_span(name, attributes=span_attrs) as span:
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, description=str(exc)))
                span.record_exception(exc)
                raise


_GLOBAL_TRACER: DevAgentsTracer | None = None


def init_tracer(trace_path: str | Path = "logs/devagents_traces.jsonl") -> DevAgentsTracer:
    global _GLOBAL_TRACER
    _GLOBAL_TRACER = DevAgentsTracer(trace_path=trace_path)
    return _GLOBAL_TRACER


def get_tracer() -> DevAgentsTracer:
    global _GLOBAL_TRACER
    if _GLOBAL_TRACER is None:
        _GLOBAL_TRACER = DevAgentsTracer()
    return _GLOBAL_TRACER

