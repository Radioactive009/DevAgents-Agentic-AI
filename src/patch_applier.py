
import os
import tempfile
from pathlib import Path

from src.patch_validator import CodePatch, validate_patch


def apply_patch(
    patch: CodePatch,
    workspace: Path,
    allowed_files: list[str],
) -> dict[str, str]:
    """
    Apply one validated exact-text patch to an existing file.

    Creates a .bak backup before replacing the file.
    Refuses ambiguous, stale, or unapproved patches.
    """

    workspace = Path(workspace).resolve()

    # Validate target path and ensure the original text matches uniquely.
    target = validate_patch(
        patch=patch,
        workspace=workspace,
        allowed_files=allowed_files,
    )

    # Read the exact current bytes so the backup preserves the original file.
    original_bytes = target.read_bytes()

    try:
        original_text = original_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Only UTF-8 files can be patched."
        ) from error

    # Recheck immediately before applying the patch.
    if original_text.count(patch.original_text) != 1:
        raise ValueError(
            "File content changed or patch became ambiguous."
        )

    updated_text = original_text.replace(
        patch.original_text,
        patch.replacement_text,
        1,
    )

    if updated_text == original_text:
        raise ValueError("Patch would not change the file.")

    backup = target.with_name(target.name + ".bak")

    # Never overwrite an earlier backup.
    try:
        with backup.open("xb") as backup_file:
            backup_file.write(original_bytes)
    except FileExistsError as error:
        raise FileExistsError(
            f"Backup already exists; refusing to overwrite it: {backup}"
        ) from error

    temporary_path = None

    try:
        # Create a temporary file beside the target, then atomically replace it.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(updated_text)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        # Recheck that the target has not changed since we read it.
        if target.read_bytes() != original_bytes:
            raise RuntimeError(
                "Target file changed during patch preparation; "
                "the patch was not applied."
            )

        os.replace(temporary_path, target)
        temporary_path = None

    except Exception:
        # Remove the temporary file if one was created.
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

        # If applying failed, remove the backup created by this invocation.
        # The original target is left unchanged unless replacement succeeded.
        if target.read_bytes() == original_bytes:
            try:
                backup.unlink(missing_ok=True)
            except OSError:
                pass

        raise

    return {
        "file_path": patch.file_path,
        "backup_path": str(backup),
        "explanation": patch.explanation,
        "status": "applied",
    }
