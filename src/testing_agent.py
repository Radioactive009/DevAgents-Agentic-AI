
from pathlib import Path
import subprocess
import sys

from src.models import TestResult


def run_project_tests(
    workspace: Path,
    timeout_seconds: int = 60,
) -> TestResult:
    """
    Run pytest for a generated project and return structured results.

    Only projects inside the designated generated_projects directory
    are eligible to run.
    """
    project_root = Path(__file__).resolve().parent.parent
    allowed_root = (project_root / "generated_projects").resolve()
    workspace = workspace.resolve()

    if not workspace.is_relative_to(allowed_root):
        raise ValueError(
            "Testing is restricted to generated_projects workspaces."
        )

    if not workspace.is_dir():
        raise FileNotFoundError(
            f"Project workspace does not exist: {workspace}"
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

    if timeout_seconds < 1 or timeout_seconds > 300:
        raise ValueError(
            "timeout_seconds must be between 1 and 300."
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
            summary=f"Tests exceeded the {timeout_seconds}-second timeout.",
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

    # Read pytest's summary, for example:
    # 12 passed in 0.65s
    # 2 failed, 10 passed in 1.20s
    import re

    summary_matches = re.findall(
        r"(\d+)\s+(passed|failed|error|skipped|xfailed|xpassed)",
        output,
        flags=re.IGNORECASE,
    )

    for count_text, outcome in summary_matches:
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
