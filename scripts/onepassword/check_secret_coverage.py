#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Check SOPS Secret coverage by ExternalSecret definitions.

This script is read-only and never decrypts secret values.
It reports SOPS-encrypted Kubernetes Secret manifests that do not have
corresponding ExternalSecret-managed targets.

Coverage rules:
- SOPS Secret: `kind: Secret` document with a `sops` key.
- Covered by ExternalSecret when:
  - same `(namespace, target secret name)` exists from `kind: ExternalSecret`, or
  - target secret name exists from `kind: ClusterExternalSecret` (global fallback).
- For ExternalSecret, target secret name defaults to `metadata.name` if
  `spec.target.name` is omitted.
- For ClusterExternalSecret, target secret name is resolved from:
  1) `spec.externalSecretSpec.target.name`
  2) `spec.externalSecretName`
  3) `metadata.name`

Usage:
  ./scripts/onepassword/check_secret_coverage.py
  ./scripts/onepassword/check_secret_coverage.py --root kubernetes/apps
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Iterable

from ruamel.yaml import YAML


@dataclass(frozen=True)
class SecretRef:
    """A namespaced Kubernetes Secret reference."""

    namespace: str
    name: str
    path: Path


@dataclass(frozen=True)
class ExternalTargetRef:
    """A discovered ExternalSecret target."""

    namespace: str | None
    name: str
    path: Path
    is_cluster: bool


_YAML = YAML(typ="safe")
_MANIFEST_SUFFIXES = (".yaml", ".yml")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Find SOPS Secret manifests not covered by ExternalSecret targets.",
    )
    parser.add_argument(
        "--root",
        default="kubernetes",
        help="Root directory to scan for YAML manifests (default: kubernetes).",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include files under dot-directories.",
    )
    parser.add_argument(
        "--output",
        choices=("plain", "markdown"),
        default="plain",
        help="Output format for the uncovered table (default: plain).",
    )
    parser.add_argument(
        "--max-width-sops",
        type=int,
        default=36,
        help="Maximum width of the SOPS secret column in plain output.",
    )
    parser.add_argument(
        "--max-width-external",
        type=int,
        default=48,
        help="Maximum width of the ExternalSecret secret column in plain output.",
    )
    parser.add_argument(
        "--max-width-path",
        type=int,
        default=56,
        help="Maximum width of the parent dir path column in plain output.",
    )
    return parser.parse_args()


def iter_manifest_files(root: Path, include_hidden: bool) -> Iterable[Path]:
    """Yield YAML manifest files recursively under root."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in _MANIFEST_SUFFIXES:
            continue
        if path.name.endswith(".sops.yaml.tmpl"):
            continue
        if not include_hidden and any(part.startswith(".") for part in path.parts):
            continue
        yield path


def iter_documents(path: Path) -> Iterable[dict[str, Any]]:
    """Yield YAML documents from path as dictionaries."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"WARNING: failed to read {path}: {exc}", file=sys.stderr)
        return

    try:
        loaded = _YAML.load_all(text)
    except Exception as exc:  # pragma: no cover - parser exceptions vary
        print(f"WARNING: failed to parse YAML in {path}: {exc}", file=sys.stderr)
        return

    for raw_doc in loaded:
        if isinstance(raw_doc, dict):
            yield from expand_list_kind(raw_doc)


def expand_list_kind(doc: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Expand `kind: List` documents into item documents."""
    if doc.get("kind") != "List":
        yield doc
        return

    items = doc.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, dict):
            yield item


def infer_namespace(doc: dict[str, Any], path: Path) -> str | None:
    """Infer namespace from metadata or known path layout."""
    metadata = doc.get("metadata")
    if isinstance(metadata, dict):
        namespace = metadata.get("namespace")
        if isinstance(namespace, str) and namespace.strip():
            return namespace.strip()

    parts = list(path.parts)
    if "apps" in parts:
        idx = parts.index("apps")
        if idx + 1 < len(parts):
            candidate = parts[idx + 1].strip()
            if candidate:
                return candidate
    return None


def read_metadata_name(doc: dict[str, Any]) -> str | None:
    """Read metadata.name as a non-empty string."""
    metadata = doc.get("metadata")
    if not isinstance(metadata, dict):
        return None
    name = metadata.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def collect_refs(
    root: Path, include_hidden: bool
) -> tuple[list[SecretRef], set[tuple[str, str]], set[str], list[ExternalTargetRef]]:
    """Collect SOPS secrets and ExternalSecret-managed targets."""
    sops_secrets: list[SecretRef] = []
    external_targets: set[tuple[str, str]] = set()
    cluster_external_targets: set[str] = set()
    external_target_refs: list[ExternalTargetRef] = []

    for path in iter_manifest_files(root, include_hidden):
        for doc in iter_documents(path):
            process_doc(
                doc=doc,
                path=path,
                sops_secrets=sops_secrets,
                external_targets=external_targets,
                cluster_external_targets=cluster_external_targets,
                external_target_refs=external_target_refs,
            )

    return sops_secrets, external_targets, cluster_external_targets, external_target_refs


def process_doc(
    doc: dict[str, Any],
    path: Path,
    sops_secrets: list[SecretRef],
    external_targets: set[tuple[str, str]],
    cluster_external_targets: set[str],
    external_target_refs: list[ExternalTargetRef],
) -> None:
    """Collect relevant refs from one manifest document."""
    kind = doc.get("kind")
    if not isinstance(kind, str):
        return

    if kind == "Secret":
        add_sops_secret(doc, path, sops_secrets)
        return

    if kind == "ExternalSecret":
        add_external_secret_target(doc, path, external_targets, external_target_refs)
        return

    if kind == "ClusterExternalSecret":
        add_cluster_external_secret_target(doc, path, cluster_external_targets, external_target_refs)


def add_sops_secret(doc: dict[str, Any], path: Path, sops_secrets: list[SecretRef]) -> None:
    """Add Secret ref when manifest appears to be SOPS-encrypted."""
    if "sops" not in doc:
        return
    namespace = infer_namespace(doc, path)
    name = read_metadata_name(doc)
    if namespace and name:
        sops_secrets.append(SecretRef(namespace=namespace, name=name, path=path))


def add_external_secret_target(
    doc: dict[str, Any],
    path: Path,
    external_targets: set[tuple[str, str]],
    external_target_refs: list[ExternalTargetRef],
) -> None:
    """Add namespaced ExternalSecret target secret reference."""
    namespace = infer_namespace(doc, path)
    target_name = resolve_external_secret_target_name(doc)
    if namespace and target_name:
        external_targets.add((namespace, target_name))
        external_target_refs.append(
            ExternalTargetRef(namespace=namespace, name=target_name, path=path, is_cluster=False)
        )


def resolve_external_secret_target_name(doc: dict[str, Any]) -> str | None:
    """Resolve target secret name for an ExternalSecret document."""
    spec = doc.get("spec")
    if isinstance(spec, dict):
        target = spec.get("target")
        if isinstance(target, dict):
            name = target.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return read_metadata_name(doc)


def add_cluster_external_secret_target(
    doc: dict[str, Any],
    path: Path,
    cluster_external_targets: set[str],
    external_target_refs: list[ExternalTargetRef],
) -> None:
    """Add cluster-wide ExternalSecret target name."""
    target_name = resolve_cluster_external_secret_target_name(doc)
    if target_name:
        cluster_external_targets.add(target_name)
        external_target_refs.append(
            ExternalTargetRef(namespace=None, name=target_name, path=path, is_cluster=True)
        )


def format_cell(value: str) -> str:
    """Escape markdown table separator in cell values."""
    return value.replace("|", "\\|")


def build_candidate_names(ref: SecretRef, external_target_refs: list[ExternalTargetRef]) -> str:
    """Build candidate ExternalSecret names from the same app directory."""
    names = sorted(
        {
            target.name
            for target in external_target_refs
            if not target.is_cluster
            and target.namespace == ref.namespace
            and target.path.parent == ref.path.parent
        }
    )
    if not names:
        return "(none)"
    return ", ".join(names)


def print_uncovered_table(
    uncovered: list[SecretRef],
    external_target_refs: list[ExternalTargetRef],
    root: Path,
    output: str,
    max_width_sops: int,
    max_width_external: int,
    max_width_path: int,
) -> None:
    """Print uncovered SOPS secrets as markdown or plain table."""
    rows: list[tuple[str, str, str]] = []
    for ref in sorted(uncovered, key=lambda item: (item.namespace, item.name, str(item.path))):
        candidate_names = build_candidate_names(ref, external_target_refs)
        parent_dir = ref.path.parent
        try:
            parent_dir_display = str(parent_dir.relative_to(root))
        except ValueError:
            parent_dir_display = str(parent_dir)
        rows.append((ref.name, candidate_names, parent_dir_display))

    if output == "markdown":
        print("| sops secret name | externalsecret secret name | parent dir path |")
        print("| --- | --- | --- |")
        for sops_name, external_name, parent_dir_display in rows:
            print(
                f"| {format_cell(sops_name)} | {format_cell(external_name)} | "
                f"{format_cell(parent_dir_display)} |"
            )
        return

    print_plain_table(
        rows=rows,
        max_width_sops=max_width_sops,
        max_width_external=max_width_external,
        max_width_path=max_width_path,
    )


def fit_cell(value: str, width: int) -> str:
    """Pad or truncate a cell to the requested width."""
    if width < 4:
        width = 4
    if len(value) <= width:
        return value.ljust(width)
    return f"{value[: width - 3]}...".ljust(width)


def print_plain_table(
    rows: list[tuple[str, str, str]],
    max_width_sops: int,
    max_width_external: int,
    max_width_path: int,
) -> None:
    """Print uncovered rows in a CLI-friendly fixed-width table."""
    header = ("sops secret name", "externalsecret secret name", "parent dir path")
    sops_width = min(max([len(header[0]), *[len(row[0]) for row in rows]]), max_width_sops)
    external_width = min(
        max([len(header[1]), *[len(row[1]) for row in rows]]),
        max_width_external,
    )
    path_width = min(max([len(header[2]), *[len(row[2]) for row in rows]]), max_width_path)

    print(
        f"{fit_cell(header[0], sops_width)}  "
        f"{fit_cell(header[1], external_width)}  "
        f"{fit_cell(header[2], path_width)}"
    )
    print(f"{'-' * sops_width}  {'-' * external_width}  {'-' * path_width}")
    for sops_name, external_name, parent_dir in rows:
        print(
            f"{fit_cell(sops_name, sops_width)}  "
            f"{fit_cell(external_name, external_width)}  "
            f"{fit_cell(parent_dir, path_width)}"
        )


def resolve_cluster_external_secret_target_name(doc: dict[str, Any]) -> str | None:
    """Resolve target secret name for a ClusterExternalSecret document."""
    metadata_name = read_metadata_name(doc)
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        return metadata_name

    external_secret_spec = spec.get("externalSecretSpec")
    if isinstance(external_secret_spec, dict):
        target = external_secret_spec.get("target")
        if isinstance(target, dict):
            name = target.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

    external_secret_name = spec.get("externalSecretName")
    if isinstance(external_secret_name, str) and external_secret_name.strip():
        return external_secret_name.strip()
    return metadata_name


def main() -> int:
    """Run coverage check and print unmatched SOPS secrets."""
    args = parse_args()
    root = Path(args.root)
    if not root.exists():
        print(f"Root path not found: {root}", file=sys.stderr)
        return 2

    sops_secrets, external_targets, cluster_external_targets, external_target_refs = collect_refs(
        root=root,
        include_hidden=args.include_hidden,
    )

    uncovered: list[SecretRef] = []
    for ref in sops_secrets:
        if (ref.namespace, ref.name) in external_targets:
            continue
        if ref.name in cluster_external_targets:
            continue
        uncovered.append(ref)

    if not uncovered:
        print(
            "All SOPS Secret manifests appear to have a corresponding "
            "ExternalSecret-managed target.",
        )
        return 0

    print_uncovered_table(
        uncovered,
        external_target_refs,
        root,
        output=args.output,
        max_width_sops=args.max_width_sops,
        max_width_external=args.max_width_external,
        max_width_path=args.max_width_path,
    )
    print()
    print(f"Total uncovered: {len(uncovered)}")
    print(f"Total SOPS secrets scanned: {len(sops_secrets)}")
    print(f"ExternalSecret targets found: {len(external_targets)}")
    print(f"ClusterExternalSecret target names found: {len(cluster_external_targets)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
