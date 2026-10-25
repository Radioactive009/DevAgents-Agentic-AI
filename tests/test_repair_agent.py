
from types import SimpleNamespace

import pytest

import src.repair_agent as repair_agent_module
from src.models import DebugReport
from src.patch_validator import CodePatch


def make_debug_report():
    return DebugReport(
        diagnosis="A calculation returns an incorrect value.",
        root_cause="The function returns 1 instead of 2.",
        severity="low",
        affected_files=["app.py"],
        recommended_fixes=["Correct the return value."],
        confidence=0.95,
        needs_more_information=False,
    )


def make_patch(
    file_path="app.py",
    original_text="return 1",
    replacement_text="return 2",
):
    return CodePatch(
        file_path=file_path,
        original_text=original_text,
        replacement_text=replacement_text,
        explanation="Correct the return value.",
    )


def configure_mocked_llm(monkeypatch, patch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-a-real-key")

    class FakeLLM:
        def __init__(self, **kwargs):
            pass

    class FakeAgent:
        def __init__(self, **kwargs):
            pass

    class FakeTask:
        def __init__(self, **kwargs):
            pass

    class FakeCrew:
        def __init__(self, **kwargs):
            pass

        def kickoff(self, inputs):
            return SimpleNamespace(pydantic=patch)

    monkeypatch.setattr(repair_agent_module, "LLM", FakeLLM)
    monkeypatch.setattr(repair_agent_module, "Agent", FakeAgent)
    monkeypatch.setattr(repair_agent_module, "Task", FakeTask)
    monkeypatch.setattr(repair_agent_module, "Crew", FakeCrew)


def test_propose_repair_returns_validated_patch(tmp_path, monkeypatch):
    target = tmp_path / "app.py"
    target.write_text("def calculate():\n    return 1\n", encoding="utf-8")

    patch = make_patch()
    configure_mocked_llm(monkeypatch, patch)

    result = repair_agent_module.propose_repair(
        debug_report=make_debug_report(),
        workspace=tmp_path,
        allowed_files=["app.py"],
    )

    assert result == patch
    assert target.read_text(encoding="utf-8") == (
        "def calculate():\n    return 1\n"
    )


def test_propose_repair_rejects_empty_allowed_files(tmp_path):
    with pytest.raises(ValueError, match="At least one allowed file"):
        repair_agent_module.propose_repair(
            debug_report=make_debug_report(),
            workspace=tmp_path,
            allowed_files=[],
        )


def test_propose_repair_rejects_missing_workspace(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(
        FileNotFoundError,
        match="workspace does not exist",
    ):
        repair_agent_module.propose_repair(
            debug_report=make_debug_report(),
            workspace=missing,
            allowed_files=["app.py"],
        )


def test_propose_repair_rejects_unsafe_allowed_path(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-a-real-key")

    with pytest.raises(ValueError, match="Unsafe file path"):
        repair_agent_module.propose_repair(
            debug_report=make_debug_report(),
            workspace=tmp_path,
            allowed_files=["../outside.py"],
        )


def test_propose_repair_rejects_patch_for_unapproved_file(
    tmp_path,
    monkeypatch,
):
    (tmp_path / "app.py").write_text("return 1", encoding="utf-8")

    patch = make_patch(file_path="store.py")
    configure_mocked_llm(monkeypatch, patch)

    with pytest.raises(ValueError, match="outside the allowed list"):
        repair_agent_module.propose_repair(
            debug_report=make_debug_report(),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )
