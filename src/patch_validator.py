
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CodePatch(BaseModel):
    """A proposed exact-text replacement. It does not apply itself."""

    model_config = ConfigDict(extra="forbid")

    file_path: str = Field(min_length=1, max_length=240)
    original_text: str = Field(min_length=1, max_length=20000)
    replacement_text: str = Field(max_length=20000)
    explanation: str = Field(min_length=1, max_length=1000)

    @field_validator("file_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        parts = normalized.split("/")

        if (
            not normalized
            or normalized.startswith("/")
            or any(part in ("", ".", "..") for part in parts)
            or any(part.startswith(".") for part in parts)
            or ":" in normalized
        ):
            raise ValueError("Unsafe relative file path.")

        return normalized

    @field_validator("original_text")
    @classmethod
    def validate_original_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Original text cannot be blank.")
        return value

    @field_validator("replacement_text")
    @classmethod
    def validate_replacement_text(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Replacement text cannot contain NUL bytes.")
        return value

    @field_validator("explanation")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Explanation cannot be blank.")
        return value


def validate_patch(
    patch: CodePatch,
    workspace: Path,
    allowed_files: list[str],
) -> Path:
    """
    Validate a proposed patch against an existing workspace file.

    This function never writes or modifies files. It returns the resolved
    target path only if all validation checks pass.
    """

    workspace = Path(workspace).resolve()

    if not workspace.is_dir():
        raise FileNotFoundError("The patch workspace does not exist.")

    normalized_allowed = {
        item.replace("\\", "/")
        for item in allowed_files
    }

    if patch.file_path not in normalized_allowed:
        raise ValueError(
            "Patch target is not in the workflow's allowed file list."
        )

    target = (workspace / patch.file_path).resolve()

    if not target.is_relative_to(workspace):
        raise ValueError("Patch target is outside the workspace.")

    if not target.is_file():
        raise FileNotFoundError("Patch target file does not exist.")

    content = target.read_text(encoding="utf-8")

    occurrences = content.count(patch.original_text)

    if occurrences == 0:
        raise ValueError(
            "Original text was not found. The patch may be based on stale code."
        )

    if occurrences > 1:
        raise ValueError(
            "Original text appears more than once. The patch is ambiguous."
        )

    if patch.original_text == patch.replacement_text:
        raise ValueError(
            "Replacement text is identical to the original text."
        )

    return target
