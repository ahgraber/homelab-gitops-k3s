"""
Security audit tests using pip-audit to detect known vulnerabilities.

This test runs pip-audit against the installed packages and emits a warning (not a failure)
if any vulnerabilities are detected, surfacing them for developer attention.

These tests skip when ``uv audit`` is available, so only one auditor runs per suite.
"Available" means uv is installed, a lockfile exists, and the uv build is new enough
to have an audit command with JSON output; older uv builds fall through to pip-audit.

To ignore a CVE, add an entry to ``IGNORED_VULNERABILITIES`` below with a
justification. Entries are passed to pip-audit via ``--ignore-vuln``.

Ref: https://gist.github.com/mikeckennedy/de70ce13231b407a8dccea758f83a5cd
"""

from functools import cache
import json
from pathlib import Path
import shutil
import subprocess
import sys
import warnings

import pytest


def _find_workspace_root(start: Path) -> Path | None:
    """Walk up from ``start`` to the nearest ancestor containing ``uv.lock``.

    The audit targets the uv workspace's single shared lockfile (one ``uv.lock``,
    one resolved environment for all members). The search is bounded to the git
    repository: it never ascends past the directory holding ``.git``, so a stray
    ``uv.lock`` outside the checkout can't be picked up. Returns ``None`` when no
    lockfile is found within the repo.
    """
    for directory in (start, *start.parents):
        if (directory / "uv.lock").exists():
            return directory
        if (directory / ".git").exists():
            break  # reached the repo root; do not search outside the checkout
    return None


def _resolve_workspace_root() -> Path:
    """Resolve the project to audit: the working directory first, then this file's.

    pytest is normally invoked from the project root, so the working directory is
    searched first. The fallback to this file's own location covers runs started
    from elsewhere. When neither search finds a lockfile, the working directory is
    returned and the caller's own skip/fallback logic takes over. This resolution
    must stay in step with ``test_uv_security_audit.py``, or the two files could
    audit different roots.
    """
    return _find_workspace_root(Path.cwd()) or _find_workspace_root(Path(__file__).resolve().parent) or Path.cwd()


@cache
def _uv_audit_available() -> bool:
    """Return True when ``uv audit`` can run for this project.

    pip-audit is the fallback auditor: when uv audit is available it runs instead
    (see ``test_uv_security_audit.py``), so these tests skip to avoid auditing
    twice. The uv build is probed rather than version-parsed — ``uv audit --help``
    exits non-zero on builds predating the audit command, and its help text names
    ``--output-format`` only on builds whose audit can emit JSON. This check must
    stay in step with the one in ``test_uv_security_audit.py``, or a uv build that
    is too old will be audited by neither file.
    """
    if shutil.which("uv") is None:
        return False
    project_root = _resolve_workspace_root()
    if not (project_root / "uv.lock").exists():
        return False
    try:
        result = subprocess.run(
            ["uv", "audit", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and "--output-format" in result.stdout


# Map of CVE id -> reason for ignoring. Revisit periodically; remove entries
# once an upstream fix is released or the risk assessment changes.
IGNORED_VULNERABILITIES: dict[str, str] = {
    # "CVE-2025-53000": "nbconvert Windows-only vulnerability (no risk on Linux/macOS)",
    # "CVE-2025-69872": "#nofix / #wontfix per https://github.com/grantjenks/python-diskcache/issues/357",
}


def _ignore_vuln_args() -> list[str]:
    args: list[str] = []
    for cve in IGNORED_VULNERABILITIES:
        args.extend(["--ignore-vuln", cve])
    return args


def _format_fix_versions(fix_versions: list[str]) -> str:
    if not fix_versions:
        return "no fix published"
    return ", ".join(fix_versions)


def _summarize_pip_audit_json(raw_output: str) -> str:
    payload = json.loads(raw_output)
    dependencies = payload.get("dependencies", [])

    vulnerable_dependencies = []
    skipped_dependencies = []
    for dependency in dependencies:
        vulns = dependency.get("vulns", [])
        if vulns:
            vulnerable_dependencies.append(dependency)
        elif dependency.get("skip_reason"):
            skipped_dependencies.append(dependency)

    lines: list[str] = []
    lines.append(f"Vulnerable packages: {len(vulnerable_dependencies)}")
    for dependency in vulnerable_dependencies:
        name = dependency["name"]
        version = dependency.get("version", "unknown")
        lines.append(f"- {name} {version}")
        for vulnerability in dependency.get("vulns", []):
            vuln_id = vulnerability.get("id", "unknown-id")
            fix_versions = _format_fix_versions(vulnerability.get("fix_versions", []))
            lines.append(f"  - {vuln_id}; fix: {fix_versions}")

    if skipped_dependencies:
        lines.append("")
        lines.append(f"Skipped dependencies: {len(skipped_dependencies)}")
        lines.extend(f"- {dependency['name']}: {dependency['skip_reason']}" for dependency in skipped_dependencies)

    return "\n".join(lines)


def test_pip_audit_no_vulnerabilities():
    """
    Run pip-audit to check for known security vulnerabilities.

    Detected vulnerabilities are surfaced as a warning so upstream dependency CVEs
    are visible to developers without failing the suite.
    The test still fails if pip-audit itself cannot run (missing, timed out, or
    erroring), since that means the audit did not actually happen.

    To run this test specifically:
        pytest tests/test_pypi_security_audit.py -v
    """
    if _uv_audit_available():
        pytest.skip("uv audit is available; using it instead of pip-audit")

    # Audit the uv workspace root (the shared environment for all members).
    project_root = _resolve_workspace_root()

    # Run pip-audit with JSON output for easier parsing
    try:
        result = subprocess.run(  # NOQA: S603
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--format=json",
                "--progress-spinner=off",
                "--skip-editable",
                *_ignore_vuln_args(),
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("pip-audit command timed out after 120 seconds")
    except FileNotFoundError:
        pytest.fail("pip-audit not installed or not accessible")

    # Check if pip-audit found any vulnerabilities
    if result.returncode != 0:
        # pip-audit returns non-zero when vulnerabilities are found
        error_output = result.stdout + "\n" + result.stderr

        # Check if it's an actual vulnerability vs an error
        if "vulnerabilities found" in error_output.lower() or '"dependencies"' in result.stdout:
            try:
                summarized_output = _summarize_pip_audit_json(result.stdout)
            except json.JSONDecodeError:
                summarized_output = result.stdout
            warnings.warn(
                f"pip-audit detected security vulnerabilities!\n\n"
                f"Output:\n{summarized_output}\n\n"
                f"Please review and update vulnerable packages.\n"
                f"Run manually with: python -m pip_audit --skip-editable",
                stacklevel=2,
            )
            return
        # Some other error occurred
        pytest.fail(f"pip-audit failed to run properly:\n\nReturn code: {result.returncode}\nOutput: {error_output}\n")


def test_pip_audit_runs_successfully():
    """
    Verify that pip-audit can run successfully (even if vulnerabilities are found).

    This is a smoke test to ensure pip-audit is properly installed and functional.
    """
    if _uv_audit_available():
        pytest.skip("uv audit is available; using it instead of pip-audit")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            pytest.fail(f"pip-audit --version failed: {result.stderr}")

        if "pip-audit" not in result.stdout.lower():
            pytest.fail("pip-audit version output unexpected")
    except FileNotFoundError:
        pytest.fail("pip-audit not installed")
    except subprocess.TimeoutExpired:
        pytest.fail("pip-audit --version timed out")
