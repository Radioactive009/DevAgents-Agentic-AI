
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """
    Append-only JSONL audit logger for DevAgents workflow events.

    Each event is written as one JSON object per line.
    API keys and common secret-bearing fields are redacted.
    """

    _SECRET_KEY_PATTERN = re.compile(
        r"(api[_-]?key|secret|password|token|authorization|credential)",
        re.IGNORECASE,
    )

    _SECRET_VALUE_PATTERNS = [
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
        re.compile(r"\bgsk_[A-Za-z0-9_-]+\b"),
    ]

    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path).resolve()
        self._lock = threading.Lock()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _sanitize(cls, value: Any, key: str = "") -> Any:
        """Redact likely secrets recursively before serialization."""
        if cls._SECRET_KEY_PATTERN.search(key):
            return "[REDACTED]"

        if isinstance(value, dict):
            return {
                str(child_key): cls._sanitize(child_value, str(child_key))
                for child_key, child_value in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [cls._sanitize(item) for item in value]

        if isinstance(value, str):
            sanitized = value
            for pattern in cls._SECRET_VALUE_PATTERNS:
                sanitized = pattern.sub("[REDACTED]", sanitized)
            return sanitized

        if value is None or isinstance(value, (bool, int, float)):
            return value

        # Avoid serializing arbitrary objects that may expose secrets.
        return str(value)

    def log_event(
        self,
        *,
        task_id: str,
        event_type: str,
        stage: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one sanitized audit event and return the event."""
        if not task_id.strip():
            raise ValueError("task_id cannot be empty.")

        if not event_type.strip():
            raise ValueError("event_type cannot be empty.")

        if not stage.strip():
            raise ValueError("stage cannot be empty.")

        if not status.strip():
            raise ValueError("status cannot be empty.")

        event = {
            "timestamp": self._timestamp(),
            "task_id": task_id,
            "event_type": event_type,
            "stage": stage,
            "status": status,
            "details": self._sanitize(details or {}),
        }

        serialized = json.dumps(
            event,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )

        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(serialized + "\n")
                log_file.flush()
                os.fsync(log_file.fileno())

        return event
