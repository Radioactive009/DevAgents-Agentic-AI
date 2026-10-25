
import json

import pytest

from src.audit_logger import AuditLogger


def test_log_event_writes_jsonl_record(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    event = logger.log_event(
        task_id="task-001",
        event_type="patch_applied",
        stage="patch_application",
        status="success",
        details={"file_path": "app.py"},
    )

    lines = log_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    saved_event = json.loads(lines[0])
    assert saved_event["task_id"] == "task-001"
    assert saved_event["event_type"] == "patch_applied"
    assert saved_event["stage"] == "patch_application"
    assert saved_event["status"] == "success"
    assert saved_event["details"]["file_path"] == "app.py"
    assert "timestamp" in saved_event
    assert event == saved_event


def test_logger_appends_events_without_overwriting(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    for index in range(2):
        logger.log_event(
            task_id="task-001",
            event_type="test_run",
            stage="testing",
            status="completed",
            details={"run": index + 1},
        )

    lines = log_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["details"]["run"] == 1
    assert json.loads(lines[1])["details"]["run"] == 2


def test_logger_redacts_secret_fields(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.log_event(
        task_id="task-001",
        event_type="configuration_check",
        stage="setup",
        status="completed",
        details={
            "api_key": "test-secret-value",
            "nested": {
                "password": "another-secret",
            },
        },
    )

    saved = json.loads(log_path.read_text(encoding="utf-8"))

    assert saved["details"]["api_key"] == "[REDACTED]"
    assert saved["details"]["nested"]["password"] == "[REDACTED]"
    assert "test-secret-value" not in log_path.read_text(encoding="utf-8")


def test_logger_redacts_groq_style_key_in_text(tmp_path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.log_event(
        task_id="task-001",
        event_type="diagnostic",
        stage="debugging",
        status="completed",
        details={"message": "Detected key gsk_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
    )

    contents = log_path.read_text(encoding="utf-8")

    assert "gsk_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456" not in contents
    assert "[REDACTED]" in contents


@pytest.mark.parametrize(
    "field,value",
    [
        ("task_id", ""),
        ("event_type", ""),
        ("stage", ""),
        ("status", ""),
    ],
)
def test_logger_rejects_empty_required_fields(
    tmp_path,
    field,
    value,
):
    logger = AuditLogger(tmp_path / "audit.jsonl")

    arguments = {
        "task_id": "task-001",
        "event_type": "test_run",
        "stage": "testing",
        "status": "completed",
    }
    arguments[field] = value

    with pytest.raises(ValueError):
        logger.log_event(**arguments)


def test_logger_creates_parent_directories(tmp_path):
    log_path = tmp_path / "logs" / "devagents" / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.log_event(
        task_id="task-001",
        event_type="workflow_started",
        stage="initialization",
        status="started",
    )

    assert log_path.is_file()


def test_logger_rejects_non_finite_numbers(tmp_path):
    logger = AuditLogger(tmp_path / "audit.jsonl")

    with pytest.raises(ValueError):
        logger.log_event(
            task_id="task-001",
            event_type="metrics",
            stage="evaluation",
            status="completed",
            details={"score": float("nan")},
        )
