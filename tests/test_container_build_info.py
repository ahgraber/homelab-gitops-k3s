"""Behavior tests for generic container build discovery."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

from ruamel.yaml import YAML

SCRIPT_PATH = pathlib.Path(__file__).parents[1] / ".github/scripts/container-build-info.sh"
WORKFLOW_PATH = pathlib.Path(__file__).parents[1] / ".github/workflows/container-images.yaml"
BUILD_WORKFLOW_PATH = pathlib.Path(__file__).parents[1] / ".github/workflows/container-image-build.yaml"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the build-info helper through Bash."""
    return subprocess.run(  # noqa: S603 - tests pass controlled arguments to a fixed script.
        ["/bin/bash", str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def add_container(root: pathlib.Path, name: str, version: str = "1.0.0") -> pathlib.Path:
    """Create a minimal container build context for a test."""
    directory = root / name
    directory.mkdir(parents=True)
    containerfile = directory / "Containerfile"
    containerfile.write_text(f"ARG VERSION={version}\nFROM scratch\nARG VERSION\n")
    return containerfile


def test_discover_returns_sorted_container_matrix(tmp_path: pathlib.Path) -> None:
    """All valid build contexts are returned in stable order."""
    add_container(tmp_path, "zeta")
    add_container(tmp_path, "alpha")

    result = run_script("discover", str(tmp_path), "all")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["alpha", "zeta"]


def test_discover_rejects_path_input(tmp_path: pathlib.Path) -> None:
    """A dispatch input cannot escape the containers directory."""
    add_container(tmp_path, "galene")

    result = run_script("discover", str(tmp_path), "../galene")

    assert result.returncode != 0
    assert "invalid container name" in result.stderr


def test_version_uses_default_or_valid_override(tmp_path: pathlib.Path) -> None:
    """The Containerfile default is used unless dispatch supplies a valid tag."""
    containerfile = add_container(tmp_path, "galene", "galene-1.1")

    default_result = run_script("version", str(containerfile), "")
    override_result = run_script("version", str(containerfile), "galene-1.2")

    assert default_result.returncode == 0, default_result.stderr
    assert default_result.stdout.strip() == "galene-1.1"
    assert override_result.returncode == 0, override_result.stderr
    assert override_result.stdout.strip() == "galene-1.2"


def test_version_rejects_invalid_docker_tag(tmp_path: pathlib.Path) -> None:
    """A dispatch version cannot alter an image reference or shell command."""
    containerfile = add_container(tmp_path, "galene")

    result = run_script("version", str(containerfile), "bad/tag")

    assert result.returncode != 0
    assert "invalid container version" in result.stderr


def test_pull_request_build_has_read_only_permissions() -> None:
    """PR-controlled build contexts cannot receive package or OIDC write access."""
    workflow = YAML(typ="safe").load(WORKFLOW_PATH.read_text())
    jobs = workflow["jobs"]

    assert "verify" in jobs
    assert jobs["verify"]["permissions"] == {"contents": "read"}
    assert jobs["verify"]["with"]["push"] is False
    assert jobs["publish"]["permissions"] == {
        "attestations": "write",
        "contents": "read",
        "id-token": "write",
        "packages": "write",
    }
    assert jobs["publish"]["with"]["push"] is True
    assert "github.ref == 'refs/heads/main'" in jobs["publish"]["if"]
    assert jobs["discover"]["timeout-minutes"] == 5


def test_reusable_build_inherits_caller_permissions() -> None:
    """The reusable workflow cannot erase or elevate its caller's token policy."""
    workflow = YAML(typ="safe").load(BUILD_WORKFLOW_PATH.read_text())

    assert "permissions" not in workflow
    assert "permissions" not in workflow["jobs"]["build"]
    assert workflow["jobs"]["build"]["timeout-minutes"] == 45
    build_step = next(step for step in workflow["jobs"]["build"]["steps"] if step["name"] == "Build and push")
    assert build_step["with"]["file"] == "./containers/${{ inputs.container }}/Containerfile"


def test_external_actions_are_pinned_to_commits() -> None:
    """Third-party workflow code cannot move without a repository change."""
    for path in (WORKFLOW_PATH, BUILD_WORKFLOW_PATH):
        workflow = YAML(typ="safe").load(path.read_text())
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                action = step.get("uses", "")
                if action and not action.startswith("./"):
                    assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", action), action
