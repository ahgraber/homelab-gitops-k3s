"""
Security audit tests using ``uv audit`` to detect known vulnerabilities.

Runs ``uv audit --frozen`` against the project's locked dependencies (``uv.lock``)
and emits a warning (not a failure) if any vulnerabilities are detected, surfacing
them for developer attention. The test still fails if uv audit itself cannot run
(missing, timed out, or erroring), since that means the audit did not actually happen.

To ignore an advisory, add an entry to ``IGNORED_VULNERABILITIES`` below with a
justification. IDs may be GHSA/PYSEC primary IDs or CVE aliases (uv matches both);
entries are passed to uv audit via ``--ignore``.

``uv audit`` is currently a preview feature, so we pass
``--preview-features audit,json-output`` to opt in explicitly and silence the
experimental warnings. Note that uv's malware check is a separate, install-time
feature (``UV_MALWARE_CHECK=1`` on ``uv sync`` / ``uv add``) and is not covered here.

Ref: https://astral.sh/blog/uv-audit
"""

import json
from pathlib import Path
import shutil
import subprocess
import warnings

import pytest


def _find_workspace_root(start: Path) -> Path:
    """Walk up from ``start`` to the nearest ancestor containing ``uv.lock``.

    The audit targets the uv workspace's single shared lockfile (one ``uv.lock``,
    one resolved environment for all members), so the test must resolve the
    workspace root regardless of which member directory it lives in. The search is
    bounded to the git repository: it never ascends past the directory holding
    ``.git``, so a stray ``uv.lock`` outside the checkout can't be picked up. Falls
    back to ``start`` when no lockfile is found within the repo (e.g. a non-workspace
    checkout), letting the caller's own skip/fallback logic take over.
    """
    for directory in (start, *start.parents):
        if (directory / "uv.lock").exists():
            return directory
        if (directory / ".git").exists():
            break  # reached the repo root; do not search outside the checkout
    return start


def _uv_audit_skip_reason(project_root: Path) -> str | None:
    """Return why uv audit cannot run here, or ``None`` if it can.

    uv audit is skipped when uv is unavailable or the project has no lockfile
    (``--frozen`` requires ``uv.lock``). In those cases the pip-audit fallback runs
    instead. See ``test_pypi_security_audit.py``.
    """
    if shutil.which("uv") is None:
        return "uv is not installed"
    if not (project_root / "uv.lock").exists():
        return "uv.lock not found (run `uv lock`)"
    return None


# Map of advisory id -> reason for ignoring (GHSA/PYSEC id or CVE alias). Revisit
# periodically; remove entries once an upstream fix is released or the risk changes.
IGNORED_VULNERABILITIES: dict[str, str] = {
    "CVE-2025-69872": "#nofix / #wontfix per https://github.com/grantjenks/python-diskcache/issues/357",
}


def _ignore_args() -> list[str]:
    args: list[str] = []
    for advisory_id in IGNORED_VULNERABILITIES:
        args.extend(["--ignore", advisory_id])
    return args


def _summarize_uv_audit_json(raw_output: str) -> str:
    payload = json.loads(raw_output)
    vulnerabilities = payload.get("vulnerabilities", [])

    # uv audit emits a flat list of vulnerabilities; group by dependency for readability.
    by_dependency: dict[tuple[str, str], list[dict]] = {}
    for vuln in vulnerabilities:
        dependency = vuln.get("dependency", {})
        key = (dependency.get("name", "unknown"), dependency.get("version", "unknown"))
        by_dependency.setdefault(key, []).append(vuln)

    lines: list[str] = [f"Vulnerable packages: {len(by_dependency)}"]
    for (name, version), vulns in by_dependency.items():
        lines.append(f"- {name} {version}")
        for vuln in vulns:
            vuln_id = vuln.get("display_id") or vuln.get("id", "unknown-id")
            fix_versions = ", ".join(vuln.get("fix_versions", [])) or "no fix published"
            lines.append(f"  - {vuln_id}; fix: {fix_versions}")

    adverse_statuses = payload.get("adverse_statuses", [])
    if adverse_statuses:
        lines.append("")
        lines.append(f"Adverse statuses: {len(adverse_statuses)}")
        for status in adverse_statuses:
            dependency = status.get("dependency", {})
            name = dependency.get("name", "unknown")
            detail = status.get("summary") or status.get("kind") or "see uv audit output"
            lines.append(f"- {name}: {detail}")

    return "\n".join(lines)


def test_uv_audit_no_vulnerabilities():
    """
    Run ``uv audit`` to check for known security vulnerabilities.

    Detected vulnerabilities are surfaced as a warning so upstream dependency
    advisories are visible to developers without failing the suite. The test still
    fails if uv audit itself cannot run (missing, timed out, or erroring), since
    that means the audit did not actually happen.

    To run this test specifically:
        uv run pytest tests/test_uv_security_audit.py -v
    """
    project_root = _find_workspace_root(Path(__file__).resolve().parent)

    skip_reason = _uv_audit_skip_reason(project_root)
    if skip_reason:
        pytest.skip(f"uv audit unavailable: {skip_reason}")

    try:
        result = subprocess.run(  # NOQA: S603
            [
                "uv",
                "audit",
                "--frozen",
                "--preview-features",
                "audit,json-output",
                "--output-format",
                "json",
                *_ignore_args(),
            ],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )
    except subprocess.TimeoutExpired:
        pytest.fail("uv audit command timed out after 120 seconds")
    except FileNotFoundError:
        pytest.fail("uv not installed or not accessible")

    # Exit 0 -> no vulnerabilities. Exit 1 with JSON on stdout -> vulnerabilities found.
    # Any other failure means uv audit could not run and should fail the test.
    if result.returncode == 0:
        return

    if result.stdout.strip().startswith("{"):
        try:
            summarized_output = _summarize_uv_audit_json(result.stdout)
        except json.JSONDecodeError:
            summarized_output = result.stdout
        warnings.warn(
            f"uv audit detected security vulnerabilities!\n\n"
            f"Output:\n{summarized_output}\n\n"
            f"Please review and update vulnerable packages.\n"
            f"Run manually with: uv audit",
            stacklevel=2,
        )
        return

    pytest.fail(
        f"uv audit failed to run properly:\n\n"
        f"Return code: {result.returncode}\nOutput: {result.stdout}\n{result.stderr}\n"
    )


def test_uv_audit_runs_successfully():
    """
    Verify that ``uv audit`` is available and runnable.

    This is a smoke test to ensure uv (with the audit subcommand) is properly
    installed and functional.
    """
    if shutil.which("uv") is None:
        pytest.skip("uv is not installed")

    try:
        result = subprocess.run(
            ["uv", "audit", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        pytest.fail("uv not installed")
    except subprocess.TimeoutExpired:
        pytest.fail("uv audit --help timed out")

    if result.returncode != 0:
        pytest.fail(f"uv audit --help failed: {result.stderr}")
