
import pytest
from pydantic import ValidationError

from src.patch_validator import CodePatch, validate_patch


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


def test_valid_patch_returns_target_without_modifying_file(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("def calculate():\n    return 1\n", encoding="utf-8")
    original_content = target.read_text(encoding="utf-8")

    patch = make_patch()

    result = validate_patch(
        patch=patch,
        workspace=tmp_path,
        allowed_files=["app.py"],
    )

    assert result == target.resolve()
    assert target.read_text(encoding="utf-8") == original_content


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.py",
        "..\\outside.py",
        "C:\\Windows\\temp.py",
        "/tmp/outside.py",
        ".env",
        "src/.secret.py",
        "src/../app.py",
    ],
)
def test_rejects_unsafe_paths(unsafe_path):
    with pytest.raises(ValidationError):
        make_patch(file_path=unsafe_path)


def test_rejects_file_not_in_allowed_list(tmp_path):
    (tmp_path / "app.py").write_text("return 1", encoding="utf-8")

    with pytest.raises(ValueError, match="allowed file list"):
        validate_patch(
            patch=make_patch(),
            workspace=tmp_path,
            allowed_files=["store.py"],
        )


def test_rejects_missing_original_text(tmp_path):
    (tmp_path / "app.py").write_text("return 3", encoding="utf-8")

    with pytest.raises(ValueError, match="Original text was not found"):
        validate_patch(
            patch=make_patch(),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )


def test_rejects_ambiguous_original_text(tmp_path):
    (tmp_path / "app.py").write_text(
        "return 1\nreturn 1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="appears more than once"):
        validate_patch(
            patch=make_patch(),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )


def test_rejects_identical_replacement(tmp_path):
    (tmp_path / "app.py").write_text("return 1", encoding="utf-8")

    with pytest.raises(ValueError, match="identical"):
        validate_patch(
            patch=make_patch(
                original_text="return 1",
                replacement_text="return 1",
            ),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )


def test_rejects_nonexistent_target(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        validate_patch(
            patch=make_patch(),
            workspace=tmp_path,
            allowed_files=["app.py"],
        )


def test_rejects_blank_explanation():
    with pytest.raises(ValidationError):
        CodePatch(
            file_path="app.py",
            original_text="return 1",
            replacement_text="return 2",
            explanation="   ",
        )


def test_rejects_unexpected_patch_fields():
    with pytest.raises(ValidationError):
        CodePatch(
            file_path="app.py",
            original_text="return 1",
            replacement_text="return 2",
            explanation="Fix the return value.",
            execute_shell_command="delete everything",
        )
