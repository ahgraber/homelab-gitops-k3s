#!/usr/bin/env python3
"""Generate ExternalSecret manifests from a Bitwarden ESO inventory.

Warnings
--------
- Best-effort parsing only; this script does not validate your intent.
- Requires secret_ids plus project_id to build remoteRef keys.
- Writes manifests next to each SOPS file; no kustomization updates.

Usage:
    ./scripts/bws/externalsecrets.py --inventory ./migration-out/inventory.json
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List

from jinja2 import Environment, StrictUndefined
from scripts.bws.models import Inventory, InventoryEntry

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
  name: {{ external_secret_name }}
  namespace: {{ namespace }}
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: bitwarden-secret-manager
  target:
    creationPolicy: Owner
    deletionPolicy: Retain
    name: {{ secret_name }}
    template:
      data:
{% if fields %}
{% for field in fields %}
        {{ field }}: '{{ "{{" }} index (fromJson .value) "{{ field }}" {{ "}}" }}'
{% endfor %}
{% else %}
        {}
{% endif %}
  data:
    - secretKey: value
      remoteRef:
        key: {{ remote_key }}
""".strip()
)


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


def externalsecret_name(entry: InventoryEntry) -> str:
    """Build ExternalSecret resource name from inventory entry."""
    namespace = entry.namespace
    app = entry.app
    purpose = entry.purpose
    if purpose and purpose != "app":
        return f"{namespace}-{app}-{purpose}-bitwarden"
    return f"{namespace}-{app}-bitwarden"


def secret_name(entry: InventoryEntry) -> str:
    """Build the Kubernetes Secret name for the ExternalSecret target."""
    app = entry.app
    purpose = entry.purpose
    if purpose and purpose != "app":
        return f"{app}-{purpose}"
    return app


def render_manifest(entry: InventoryEntry, project_id: str) -> str:
    """Render an ExternalSecret manifest for a single entry."""
    namespace = entry.namespace
    item_name = entry.item_name
    remote_key = item_name
    return (
        _TEMPLATE.render(
            external_secret_name=externalsecret_name(entry),
            namespace=namespace,
            secret_name=secret_name(entry),
            remote_key=remote_key,
            fields=entry.fields,
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

    errors = 0
    project_id = inventory.project_id
    if not project_id:
        print("WARNING: missing project_id in inventory", file=sys.stderr)
        return 1

    for entry in entries:
        if not entry.fields:
            print(
                f"WARNING: no fields found for {entry.sops_path}; template data will be empty",
                file=sys.stderr,
            )
        sops_path = Path(entry.sops_path)
        manifest = render_manifest(entry, project_id)
        target_path = output_path(sops_path)

        if args.dry_run:
            print(f"# {target_path}")
            print(manifest.rstrip())
            print()
            continue

        target_path.write_text(manifest)
        print(f"Wrote {target_path}")

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
