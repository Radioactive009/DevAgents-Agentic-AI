"""
Blackboard Messaging Adapter.

Exposes a messaging interface backed by the thread-safe centralized Blackboard.
Updates to topics map directly to transactional updates on the shared ProjectState.
"""

from collections import defaultdict
from typing import Any, Callable

from src.blackboard import Blackboard
from src.messaging.base import BaseMessagingArchitecture
from src.models import (
    ArchitecturePlan,
    DebugReport,
    ProjectRequest,
    ProjectState,
    TestResult,
)


class BlackboardMessaging(BaseMessagingArchitecture):
    """Direct shared-state Blackboard architecture adapter."""

    def __init__(self, task_id: str, request: ProjectRequest):
        self._blackboard = Blackboard(task_id=task_id, request=request)
        self._subscribers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    @property
    def blackboard(self) -> Blackboard:
        return self._blackboard

    def architecture_name(self) -> str:
        return "Blackboard (Centralized Shared State)"

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        self._subscribers[topic].append(handler)

    def publish(self, topic: str, payload: Any) -> None:
        """Route topic update to corresponding Blackboard mutation."""
        if topic == "architecture.plan":
            if isinstance(payload, ArchitecturePlan):
                self._blackboard.update_architecture(payload)
        elif topic == "code.files":
            if isinstance(payload, list):
                self._blackboard.record_code_files(payload)
        elif topic == "test.result":
            if isinstance(payload, TestResult):
                self._blackboard.record_test_result(payload)
        elif topic == "debug.report":
            if isinstance(payload, DebugReport):
                self._blackboard.record_debug_report(payload)
        elif topic == "error":
            self._blackboard.record_error(str(payload))

        # Notify any subscribed listeners
        for handler in self._subscribers.get(topic, []):
            handler(payload)

    def get_state(self) -> ProjectState:
        return self._blackboard.get_state()

