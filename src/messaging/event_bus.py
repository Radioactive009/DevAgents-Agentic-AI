"""
EventBus (Pub/Sub) Messaging Architecture.

Decouples agent producers and consumers via typed topic messages and an
append-only in-memory event stream. State is maintained by an event-sourcing reducer.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
from typing import Any, Callable

from src.messaging.base import BaseMessagingArchitecture
from src.models import (
    ArchitecturePlan,
    DebugReport,
    ProjectRequest,
    ProjectState,
    TestResult,
)


@dataclass
class EventEnvelope:
    topic: str
    payload: Any
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EventBusMessaging(BaseMessagingArchitecture):
    """Event-driven Pub/Sub messaging architecture."""

    def __init__(self, task_id: str, request: ProjectRequest):
        self._lock = threading.RLock()
        self._task_id = task_id
        self._request = request
        self._subscribers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)
        self._event_log: list[EventEnvelope] = []
        self._state = ProjectState(task_id=task_id, request=request)

    def architecture_name(self) -> str:
        return "EventBus (Decoupled Pub/Sub)"

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            self._subscribers[topic].append(handler)

    def publish(self, topic: str, payload: Any) -> None:
        """Append to event log, update state projection, and notify subscribers."""
        with self._lock:
            envelope = EventEnvelope(topic=topic, payload=payload)
            self._event_log.append(envelope)
            self._apply_to_state(topic, payload)
            subscribers = list(self._subscribers.get(topic, []))

        # Notify subscribers outside the lock to prevent deadlocks
        for handler in subscribers:
            handler(payload)

    def _apply_to_state(self, topic: str, payload: Any) -> None:
        """Project event payload onto current state."""
        if topic == "architecture.plan" and isinstance(payload, ArchitecturePlan):
            self._state.architecture_plan = payload
            self._state.status = "coding"
        elif topic == "code.files" and isinstance(payload, list):
            self._state.code_files = [str(p).replace("\\", "/") for p in payload]
        elif topic == "test.result" and isinstance(payload, TestResult):
            self._state.test_result = payload
            self._state.status = "debugging" if payload.failed > 0 else "verifying"
        elif topic == "debug.report" and isinstance(payload, DebugReport):
            self._state.debug_report = payload
        elif topic == "error":
            self._state.errors.append(str(payload))
            self._state.status = "failed"

    def get_state(self) -> ProjectState:
        with self._lock:
            return self._state.model_copy(deep=True)

    @property
    def event_log(self) -> list[EventEnvelope]:
        with self._lock:
            return list(self._event_log)

