
import os
import tempfile
from pathlib import Path

from src.patch_validator import CodePatch, validate_patch


def _create_unique_backup(target: Path, original_bytes: bytes) -> Path:
    """Create a new backup without overwriting any existing backup."""

    base = target.with_name(target.name + ".bak")
    counter = 0

    while True:
        backup = (
            base
            if counter == 0
            else base.with_name(f"{base.name}.{counter}")
        )

        try:
            with backup.open("xb") as backup_file:
                backup_file.write(original_bytes)
            return backup
        except FileExistsError:
            counter += 1


def apply_patch(
    patch: CodePatch,
    workspace: Path,
    allowed_files: list[str],
) -> dict[str, str]:
    """Apply one validated patch and preserve the original file."""

    workspace = Path(workspace).resolve()

    target = validate_patch(
        patch=patch,
        workspace=workspace,
        allowed_files=allowed_files,
    )

    original_bytes = target.read_bytes()

    try:
        original_text = original_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Only UTF-8 files can be patched.") from error

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

    # Create a unique backup; never overwrite earlier backups.
    backup = _create_unique_backup(target, original_bytes)
    temporary_path = None

    try:
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

        # Do not overwrite a file changed after our initial read.
        if target.read_bytes() != original_bytes:
            raise RuntimeError(
                "Target file changed during patch preparation; "
                "the patch was not applied."
            )

        os.replace(temporary_path, target)
        temporary_path = None

    except Exception:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

        # Keep the backup if the target may have changed.
        # Delete it only if the original content is still intact.
        try:
            if target.read_bytes() == original_bytes:
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
