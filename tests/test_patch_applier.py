
import pytest

from src.patch_applier import apply_patch
from src.patch_validator import CodePatch


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


def test_apply_patch_updates_file_and_creates_backup(tmp_path):
    target = tmp_path / "app.py"
    original = "def calculate():\n    return 1\n"
    target.write_text(original, encoding="utf-8")

    result = apply_patch(
        patch=make_patch(),
        workspace=tmp_path,
        allowed_files=["app.py"],
    )

    assert target.read_text(encoding="utf-8") == (
        "def calculate():\n    return 2\n"
    )
    assert target.with_name("app.py.bak").read_text(encoding="utf-8") == original
    assert result["status"] == "applied"
    assert result["file_path"] == "app.py"


def test_apply_patch_rejects_stale_patch(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("return 3", encoding="utf-8")

    with pytest.raises(ValueError, match="Original text was not found"):
        apply_patch(
            patch=make_patch(),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )

    assert target.read_text(encoding="utf-8") == "return 3"
    assert not target.with_name("app.py.bak").exists()


def test_apply_patch_rejects_unapproved_file(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("return 1", encoding="utf-8")

    with pytest.raises(ValueError, match="allowed file list"):
        apply_patch(
            patch=make_patch(),
            workspace=tmp_path,
            allowed_files=["store.py"],
        )

    assert target.read_text(encoding="utf-8") == "return 1"


def test_apply_patch_refuses_existing_backup(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("return 1", encoding="utf-8")

    backup = tmp_path / "app.py.bak"
    backup.write_text("preserve this backup", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Backup already exists"):
        apply_patch(
            patch=make_patch(),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )

    assert target.read_text(encoding="utf-8") == "return 1"
    assert backup.read_text(encoding="utf-8") == "preserve this backup"


def test_apply_patch_rejects_ambiguous_text(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("return 1\nreturn 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="appears more than once"):
        apply_patch(
            patch=make_patch(),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )

    assert target.read_text(encoding="utf-8") == "return 1\nreturn 1\n"


def test_apply_patch_preserves_original_on_validation_failure(tmp_path):
    target = tmp_path / "app.py"
    original = "return 1"
    target.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError):
        apply_patch(
            patch=make_patch(original_text="return 99"),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )

    assert target.read_text(encoding="utf-8") == original
    assert not target.with_name("app.py.bak").exists()
