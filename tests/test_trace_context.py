
import time
from uuid import UUID

import pytest

from src.trace_context import TraceContext


def test_trace_context_creates_valid_unique_trace_ids():
    first = TraceContext("task-1")
    second = TraceContext("task-1")

    assert first.task_id == "task-1"
    assert UUID(first.trace_id)
    assert UUID(second.trace_id)
    assert first.trace_id != second.trace_id


def test_measure_records_duration():
    trace = TraceContext("task-1")

    with trace.measure("testing") as result:
        time.sleep(0.01)

    assert result["stage"] == "testing"
    assert isinstance(result["duration_seconds"], float)
    assert result["duration_seconds"] >= 0.01


def test_measure_records_duration_when_stage_fails():
    trace = TraceContext("task-1")

    with pytest.raises(RuntimeError, match="stage failed"):
        with trace.measure("debugging") as result:
            raise RuntimeError("stage failed")

    assert result["stage"] == "debugging"
    assert result["duration_seconds"] >= 0.0


def test_empty_task_id_is_rejected():
    with pytest.raises(ValueError, match="task_id"):
        TraceContext("")


def test_empty_stage_is_rejected():
    trace = TraceContext("task-1")

    with pytest.raises(ValueError, match="stage"):
        with trace.measure(""):
            pass
