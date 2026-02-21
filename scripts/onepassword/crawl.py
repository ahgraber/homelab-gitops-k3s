#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2",
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Crawl SOPS secrets and build a 1Password ESO inventory.

Warnings
--------
- Best-effort parsing only; this script does not validate your intent.
- Namespace/app inference relies on the nearest ks.yaml and helmrelease.yaml.
- The inventory contains metadata only (no plaintext), but still review output.

Usage:
    ./scripts/onepassword/crawl.py --dir kubernetes/apps --output-dir ./migration-out --vault homelab
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import List, Optional

from ruamel.yaml import YAML

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from onepassword.models import Inventory, InventoryEntry

_ITEM_NAME_ALLOWED = re.compile(r"[^a-zA-Z0-9._-]+")
_SEPARATOR_PREFERENCE = (".", "_", "-")
_YAML = YAML(typ="safe")


@dataclass(frozen=True)
class Item:
    namespace: str
    app: str
    ks_path: Path
    helmrelease_path: Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Crawl SOPS secrets and build an inventory for 1Password ESO.",
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
        "--vault",
        help="Default 1Password vault name to store in the inventory.",
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


def load_yaml_doc(path: Path) -> Optional[dict]:
    """Load a YAML document safely as a dictionary."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = _YAML.load(handle)
    except Exception:
        return None
    if isinstance(loaded, dict):
        return loaded
    return None


def parse_yaml_value(path: Path, key: str) -> Optional[str]:
    """Find a top-level YAML scalar value for the given key."""
    document = load_yaml_doc(path)
    if document is None:
        return None
    value = document.get(key)
    if isinstance(value, str) and value:
        return value
    if value is not None:
        rendered = str(value).strip()
        if rendered:
            return rendered
    return None


def find_nearest(start: Path, filename: str, boundary: Path) -> Optional[Path]:
    """Find the nearest filename by walking up parent directories."""
    current = start.resolve()
    boundary = boundary.resolve()

    def within_boundary(path: Path) -> bool:
        return path == boundary or boundary in path.parents

    if not within_boundary(current):
        return None

    while True:
        candidate = current / filename
        if candidate.exists():
            return candidate
        if current == boundary or current.parent == current or not within_boundary(current.parent):
            return None
        current = current.parent


def infer_namespace_app(sops_path: Path, boundary: Path) -> Item:
    """Infer namespace and app from nearest ks.yaml/helmrelease.yaml or path."""
    sops_dir = sops_path.parent
    ks_path = find_nearest(sops_dir, "ks.yaml", boundary)
    helmrelease_path = find_nearest(sops_dir, "helmrelease.yaml", boundary)

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
    document = load_yaml_doc(path)
    if document is None:
        return []

    keys: List[str] = []
    for section_name in ("stringData", "data"):
        section = document.get(section_name)
        if isinstance(section, dict):
            for key in section:
                key_text = str(key).strip()
                if key_text and key_text not in keys:
                    keys.append(key_text)
    return sorted(keys)


def infer_purpose(sops_path: Path) -> str:
    """Infer item purpose from the SOPS filename."""
    name = sops_path.name
    match = re.match(r"^secret(?:-(.+))?\.sops\.yaml$", name)
    if match:
        return match.group(1) or "app"
    alt = re.sub(r"\.sops\.yaml$", "", name)
    return alt


def sanitize_component(value: str) -> str:
    """Normalize a namespace/app component for 1Password references."""
    normalized = _ITEM_NAME_ALLOWED.sub("_", value.strip().lower())
    normalized = normalized.strip("._-")
    if not normalized:
        raise RuntimeError(f"Unable to normalize component: {value!r}")
    return normalized


def choose_separator(namespace: str, app: str) -> str:
    """Choose separator with preference order: dot, underscore, hyphen."""
    for separator in _SEPARATOR_PREFERENCE:
        if separator not in namespace and separator not in app:
            return separator
    return _SEPARATOR_PREFERENCE[0]


def infer_section(purpose: str) -> Optional[str]:
    """Map filename purpose to optional 1Password section."""
    if purpose == "app":
        return None
    return sanitize_component(purpose)


def build_item_name(namespace: str, app: str) -> str:
    """Build a 1Password item title from namespace/app.

    Slashes are intentionally avoided to keep item names compatible with
    `op://` secret reference syntax.
    """
    safe_namespace = sanitize_component(namespace)
    safe_app = sanitize_component(app)
    separator = choose_separator(safe_namespace, safe_app)
    return f"{safe_namespace}{separator}{safe_app}"


def main() -> int:
    """Run the crawler and write the inventory."""
    os.umask(0o077)
    args = parse_args()
    root = Path(args.dir)
    if not root.exists():
        print(f"Root directory not found: {root}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else root
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / "inventory.json"
    vault = args.vault or os.environ.get("OP_VAULT")

    entries = []
    errors = 0
    sops_files = find_sops_files(root, args.include_archived)

    for sops_path in sops_files:
        try:
            inference = infer_namespace_app(sops_path, root)
        except RuntimeError as exc:
            print(f"WARNING: {exc}", file=sys.stderr)
            errors += 1
            continue

        fields = extract_keys_from_sops(sops_path)
        if not fields:
            print(f"WARNING: No fields found in {sops_path}", file=sys.stderr)

        purpose = infer_purpose(sops_path)
        section = infer_section(purpose)
        item_name = build_item_name(inference.namespace, inference.app)

        entries.append(
            {
                "sops_path": str(sops_path),
                "namespace": inference.namespace,
                "app": inference.app,
                "purpose": purpose,
                "section": section,
                "item_name": item_name,
                "fields": fields,
                "ks_path": str(inference.ks_path),
                "helmrelease_path": str(inference.helmrelease_path),
            }
        )

    inventory = Inventory(
        root=str(root),
        vault=vault,
        entries=[InventoryEntry(**entry) for entry in entries],
    )
    inventory_path.write_text(inventory.model_dump_json(indent=2, exclude_none=True))
    os.chmod(inventory_path, 0o600)
    print(f"Wrote inventory to {inventory_path}")

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
