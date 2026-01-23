#!/usr/bin/env python3
"""Crawl SOPS secrets and build a Bitwarden ESO inventory.

Warnings
--------
- Best-effort parsing only; this script does not validate your intent.
- Namespace/app inference relies on the nearest ks.yaml and helmrelease.yaml.
- The inventory contains metadata only (no plaintext), but still review output.

Usage:
    ./scripts/bws/crawl.py --dir kubernetes/apps --output-dir ./migration-out --project-id <id>
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import Iterable, List, Optional

from scripts.bws.models import Inventory, InventoryEntry


@dataclass(frozen=True)
class Item:
    namespace: str
    app: str
    ks_path: Path
    helmrelease_path: Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Crawl SOPS secrets and build an inventory for Bitwarden ESO.",
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="Directory to crawl for *.sops.yaml files.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory where inventory.json will be written (defaults to --dir).",
    )
    parser.add_argument(
        "--project-id",
        help="Bitwarden project ID to store in the inventory.",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include paths under kubernetes/apps/.archive.",
    )
    return parser.parse_args()


def find_sops_files(root: Path, include_archived: bool) -> List[Path]:
    """Return a sorted list of SOPS secret files under root."""
    files = []
    for path in root.rglob("*.sops.yaml"):
        if path.name.endswith(".sops.yaml.tmpl"):
            continue
        if not include_archived and "/.archive/" in str(path):
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def strip_inline_comment(value: str) -> str:
    """Remove inline comments from a scalar value."""
    return value.split("#", 1)[0].strip()


def parse_scalar(value: str) -> str:
    """Extract a scalar string from a YAML value segment."""
    value = strip_inline_comment(value)
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    tokens = value.split()
    if tokens:
        return tokens[-1]
    return value


def parse_yaml_value(path: Path, key: str) -> Optional[str]:
    """Find a top-level YAML scalar value for the given key."""
    pattern = re.compile(rf"^\s*{re.escape(key)}:\s*(.+)?$")
    for line in path.read_text().splitlines():
        match = pattern.match(line)
        if match:
            raw = match.group(1) or ""
            value = parse_scalar(raw)
            if value:
                return value
    return None


def find_nearest(start: Path, filename: str) -> Optional[Path]:
    """Find the nearest filename by walking up parent directories."""
    current = start
    while True:
        candidate = current / filename
        if candidate.exists():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def infer_namespace_app(sops_path: Path) -> Item:
    """Infer namespace and app from nearest ks.yaml/helmrelease.yaml or path."""
    sops_dir = sops_path.parent
    ks_path = find_nearest(sops_dir, "ks.yaml")
    helmrelease_path = find_nearest(sops_dir, "helmrelease.yaml")

    namespace = parse_yaml_value(ks_path, "targetNamespace") if ks_path else None
    app = parse_yaml_value(helmrelease_path, "name") if helmrelease_path else None

    used_fallback = False
    if not namespace or not app:
        parts = list(sops_path.parts)
        try:
            apps_idx = parts.index("apps")
            if not namespace and len(parts) > apps_idx + 1:
                namespace = parts[apps_idx + 1]
            if not app and len(parts) > apps_idx + 2:
                app = parts[apps_idx + 2]
            used_fallback = True
        except ValueError:
            pass

    if not namespace:
        raise RuntimeError(f"Unable to infer namespace for {sops_path}")
    if not app:
        raise RuntimeError(f"Unable to infer app name for {sops_path}")

    if used_fallback:
        print(
            f"WARNING: inferred namespace/app from path for {sops_path}",
            file=sys.stderr,
        )

    return Item(
        namespace=namespace,
        app=app,
        ks_path=ks_path or sops_path,
        helmrelease_path=helmrelease_path or sops_path,
    )


def extract_keys_from_sops(path: Path) -> List[str]:
    """Extract secret keys from stringData/data sections without decrypting."""
    keys: List[str] = []
    lines = path.read_text().splitlines()
    sections = {"stringData": None, "data": None}

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        for section in sections:
            match = re.match(rf"^(\s*){section}:\s*$", line)
            if not match:
                continue
            indent = len(match.group(1))
            idx += 1
            while idx < len(lines):
                inner = lines[idx]
                if not inner.strip():
                    idx += 1
                    continue
                current_indent = len(inner) - len(inner.lstrip())
                if current_indent <= indent:
                    break
                if inner.lstrip().startswith("#"):
                    idx += 1
                    continue
                key_match = re.match(r"^\s*([^:#\s][^:]*):", inner)
                if key_match:
                    key = key_match.group(1).strip().strip('"').strip("'")
                    if key and key not in keys:
                        keys.append(key)
                idx += 1
            continue
        idx += 1

    return keys


def infer_purpose(sops_path: Path) -> str:
    """Infer item purpose from the SOPS filename."""
    name = sops_path.name
    match = re.match(r"^secret(?:-(.+))?\.sops\.yaml$", name)
    if match:
        return match.group(1) or "app"
    alt = re.sub(r"\.sops\.yaml$", "", name)
    return alt


def build_item_name(namespace: str, app: str, purpose: str) -> str:
    """Build a Bitwarden item name from namespace/app/purpose."""
    return f"{namespace}/{app}-{purpose}"


def main() -> int:
    """Run the crawler and write the inventory."""
    args = parse_args()
    root = Path(args.dir)
    if not root.exists():
        print(f"Root directory not found: {root}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else root
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / "inventory.json"
    project_id = args.project_id or os.environ.get("BWS_PROJECT_ID")

    entries = []
    errors = 0
    sops_files = find_sops_files(root, args.include_archived)

    for sops_path in sops_files:
        try:
            inference = infer_namespace_app(sops_path)
        except RuntimeError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)
            errors += 1
            continue

        fields = extract_keys_from_sops(sops_path)
        if not fields:
            print(f"WARNING: No fields found in {sops_path}", file=sys.stderr)

        purpose = infer_purpose(sops_path)
        item_name = build_item_name(inference.namespace, inference.app, purpose)

        entries.append(
            {
                "sops_path": str(sops_path),
                "namespace": inference.namespace,
                "app": inference.app,
                "purpose": purpose,
                "item_name": item_name,
                "fields": fields,
                "ks_path": str(inference.ks_path),
                "helmrelease_path": str(inference.helmrelease_path),
            }
        )

    inventory = Inventory(
        root=str(root),
        project_id=project_id,
        entries=[InventoryEntry(**entry) for entry in entries],
    )
    inventory_path.write_text(inventory.model_dump_json(indent=2, exclude_none=True))
    print(f"Wrote inventory to {inventory_path}")

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
