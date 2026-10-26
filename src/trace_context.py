
from contextlib import contextmanager
from time import perf_counter
from typing import Iterator
from uuid import uuid4


class TraceContext:
    """
    Tracks one workflow execution and measures stage durations.

    A trace ID groups events from a single workflow run.
    Durations use a monotonic clock for reliable elapsed-time measurement.
    """

    def __init__(self, task_id: str):
        if not task_id.strip():
            raise ValueError("task_id cannot be empty.")

        self.task_id = task_id
        self.trace_id = str(uuid4())

    @contextmanager
    def measure(self, stage: str) -> Iterator[dict[str, float | str]]:
        """Measure a stage and expose its duration in seconds."""
        if not stage.strip():
            raise ValueError("stage cannot be empty.")

        started = perf_counter()
        result: dict[str, float | str] = {
            "stage": stage,
            "duration_seconds": 0.0,
        }

        try:
            yield result
        finally:
            result["duration_seconds"] = round(
                perf_counter() - started,
                6,
            )
