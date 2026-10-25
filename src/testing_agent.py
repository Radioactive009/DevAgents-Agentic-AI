
from pathlib import Path
import re
import subprocess
import sys

from src.models import TestResult


def run_project_tests(
    workspace: Path,
    timeout_seconds: int = 60,
    allowed_root: Path | None = None,
) -> TestResult:
    """Run pytest for a project inside an explicitly allowed workspace."""

    project_root = Path(__file__).resolve().parent.parent

    if allowed_root is None:
        allowed_root = project_root / "generated_projects"

    allowed_root = Path(allowed_root).resolve()
    workspace = Path(workspace).resolve()

    if not workspace.is_relative_to(allowed_root):
        raise ValueError(
            "Testing is restricted to the allowed workspace."
        )

    if not workspace.is_dir():
        raise FileNotFoundError(
            f"Project workspace does not exist: {workspace}"
        )

    if not 1 <= timeout_seconds <= 300:
        raise ValueError(
            "timeout_seconds must be between 1 and 300."
        )

    test_directory = workspace / "tests"

    if not test_directory.is_dir():
        raise FileNotFoundError(
            "Generated project does not contain a tests directory."
        )

    test_files = list(test_directory.glob("test_*.py"))

    if not test_files:
        raise FileNotFoundError(
            "No test_*.py files were found in the project's tests directory."
        )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
        str(test_directory),
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            passed=0,
            failed=1,
            summary=f"Tests timed out after {timeout_seconds} seconds.",
            error_details=[
                f"Test execution timed out after {timeout_seconds} seconds."
            ],
        )

    output = "\n".join(
        part
        for part in (completed.stdout, completed.stderr)
        if part
    )

    passed = 0
    failed = 0

    # Extract pytest's final summary counts.
    for count_text, outcome in re.findall(
        r"(\d+)\s+(passed|failed|error|skipped|xfailed|xpassed)",
        output,
        flags=re.IGNORECASE,
    ):
        count = int(count_text)
        outcome = outcome.lower()

        if outcome == "passed":
            passed += count
        elif outcome in ("failed", "error"):
            failed += count

    if completed.returncode != 0 and failed == 0:
        failed = 1

    if completed.returncode == 0:
        summary = f"Tests completed successfully: {passed} passed."
    else:
        summary = (
            f"Tests did not complete successfully: "
            f"{passed} passed, {failed} failed or errored."
        )

    error_details = []

    if completed.returncode != 0:
        error_details.append(
            output[-6000:] if output else "Pytest failed without output."
        )

    return TestResult(
        passed=passed,
        failed=failed,
        summary=summary,
        error_details=error_details,
    )
