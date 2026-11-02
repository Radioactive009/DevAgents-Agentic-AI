"""
Base interface for inter-agent context sharing and messaging architectures.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable

from src.models import ProjectState


class BaseMessagingArchitecture(ABC):
    """Abstract contract for messaging and state coordination across agents."""

    @abstractmethod
    def publish(self, topic: str, payload: Any) -> None:
        """Publish an event or message payload to a specific topic."""
        pass

    @abstractmethod
    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        """Register a subscriber callback for a specific topic."""
        pass

    @abstractmethod
    def get_state(self) -> ProjectState:
        """Retrieve a snapshot of the current shared state."""
        pass

    @abstractmethod
    def architecture_name(self) -> str:
        """Return the human-readable name of the messaging architecture."""
        pass

