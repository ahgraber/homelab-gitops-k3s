#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "jinja2>=3.1",
#   "pydantic>=2",
# ]
# ///
"""Generate ExternalSecret manifests from a 1Password ESO inventory.

Warnings
--------
- Best-effort parsing only; this script does not validate your intent.
- Writes manifests next to each SOPS file; no kustomization updates.

Usage:
    ./scripts/onepassword/externalsecrets.py --inventory ./migration-out/inventory.json
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from jinja2 import Environment, StrictUndefined

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from onepassword.models import Inventory, InventoryEntry

_ENV = Environment(
    autoescape=False,  # NOQA: S701 # autoescape warning is for HTML
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=StrictUndefined,
)

_TEMPLATE = _ENV.from_string(
    """
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: &name {{ external_secret_name }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: onepassword
  target:
    name: *name
    template:
      data:
{% for field in fields %}
        {{ field }}: '{{ template_lookup(field) }}'
{% endfor %}
  dataFrom:
    - extract:
        # all available properties from the key will be synced
        key: "{{ remote_key }}"
""".strip()
)


def template_lookup(field: str) -> str:
    """Return a Go template expression safe for arbitrary map keys."""
    return f'{{{{ index . "{field}" }}}}'


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate ExternalSecret manifests from inventory.",
    )
    parser.add_argument(
        "--inventory",
        required=True,
        help="Path to inventory.json created by the crawl script.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned outputs without writing files.",
    )
    return parser.parse_args()


def load_inventory(path: Path) -> Inventory:
    """Load inventory JSON from disk."""
    return Inventory.model_validate_json(path.read_text())


def normalize_rfc1123_name(value: str) -> str:
    """Convert an arbitrary string to a Kubernetes RFC 1123 subdomain."""
    # Split camelCase/PascalCase boundaries before lowercasing.
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    name = name[:253].strip("-")
    return name or "secret"


def secret_name(entry: InventoryEntry) -> str:
    """Build the Kubernetes Secret name for the ExternalSecret target."""
    app = entry.app
    purpose = entry.purpose
    if purpose and purpose != "app":
        return normalize_rfc1123_name(f"{app}-{purpose}")
    return normalize_rfc1123_name(app)


def render_manifest(entry: InventoryEntry) -> str:
    """Render an ExternalSecret manifest for a single entry."""
    return (
        _TEMPLATE.render(
            external_secret_name=secret_name(entry),
            remote_key=entry.item_name,
            fields=entry.fields,
            template_lookup=template_lookup,
        )
        + "\n"
    )


def output_path(sops_path: Path) -> Path:
    """Compute the output path for an ExternalSecret manifest."""
    return sops_path.with_suffix("").with_suffix(".externalsecret.yaml")


def main() -> int:
    """Generate ExternalSecret manifests from inventory entries."""
    args = parse_args()
    inventory_path = Path(args.inventory)
    if not inventory_path.exists():
        print(f"Inventory file not found: {inventory_path}", file=sys.stderr)
        return 1

    inventory = load_inventory(inventory_path)
    entries = inventory.entries
    if not entries:
        print("No entries to process.")
        return 0

    for entry in entries:
        if not entry.fields:
            print(
                f"WARNING: no fields found for {entry.sops_path}; skipping",
                file=sys.stderr,
            )
            continue

        sops_path = Path(entry.sops_path)
        manifest = render_manifest(entry)
        target_path = output_path(sops_path)

        if args.dry_run:
            print(f"# {target_path}")
            print(manifest.rstrip())
            print()
            continue

        target_path.write_text(manifest)
        print(f"Wrote {target_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
