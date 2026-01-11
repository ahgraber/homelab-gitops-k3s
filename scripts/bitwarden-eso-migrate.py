#!/usr/bin/env python3
"""Bitwarden ESO migration helper.

Usage:
    ./scripts/bitwarden-eso-migrate.py --mapping docs/bitwarden-eso-migration-map.example.json
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class MappingEntry:
    name: str
    namespace: str
    sops_path: Path
    fields: Dict[str, str]
    project_id: Optional[str]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the migration helper."""
    parser = argparse.ArgumentParser(
        description="Plan (or apply) Bitwarden item creation from SOPS secrets.",
    )
    parser.add_argument(
        "--mapping",
        required=True,
        help="Path to the JSON mapping file.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute the command template for each entry (default: dry-run).",
    )
    parser.add_argument(
        "--command-template",
        help=(
            "Command template to execute when --apply is set. "
            "Supports {item_name}, {project_id}, {namespace} placeholders. "
            "Use --stdin to pass JSON payload via stdin."
        ),
    )
    parser.add_argument(
        "--check-template",
        help=(
            "Optional command template to detect existing items. "
            "If it exits 0, the item is treated as existing and skipped unless --force."
        ),
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Send JSON payload to stdin of the command template.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Apply even if the check command indicates the item exists.",
    )
    parser.add_argument(
        "--show-values",
        action="store_true",
        help="Show plaintext values in output (default: redact).",
    )
    parser.add_argument(
        "--namespace",
        help="Only process entries for this namespace.",
    )
    return parser.parse_args()


def load_mapping(path: Path) -> List[MappingEntry]:
    """Load the mapping file and return validated entries."""
    data = json.loads(path.read_text())
    defaults = data.get("defaults", {})
    default_project_id = defaults.get("project_id")
    entries: List[MappingEntry] = []

    for raw in data.get("entries", []):
        sops_path = Path(raw["sops_path"]).expanduser()
        entries.append(
            MappingEntry(
                name=raw["name"],
                namespace=raw["namespace"],
                sops_path=sops_path,
                fields=dict(raw.get("fields", {})),
                project_id=raw.get("project_id", default_project_id),
            )
        )

    return entries


def decrypt_sops(path: Path) -> Dict[str, Any]:
    """Decrypt a SOPS file and return it as JSON."""
    try:
        output = subprocess.check_output(  # NOQA: S603
            [
                "sops",
                "--decrypt",
                "--output-type",
                "json",
                str(path),
            ]
        )
    except FileNotFoundError as exc:
        raise RuntimeError("sops is required but was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"sops failed to decrypt {path}") from exc

    return json.loads(output.decode("utf-8"))


def extract_secret_value(secret: Dict[str, Any], key: str) -> str:
    """Extract a value from a Secret's stringData or data entry."""
    string_data = secret.get("stringData", {})
    if key in string_data:
        return str(string_data[key])

    data = secret.get("data", {})
    if key in data:
        try:
            return base64.b64decode(data[key]).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError(f"Failed to base64 decode data[{key}]") from exc

    raise KeyError(f"Key {key} not found in stringData or data")


def redact(value: str, show_values: bool) -> str:
    """Return either the plaintext value or a redacted placeholder."""
    if show_values:
        return value
    return f"<redacted len={len(value)}>"


def format_command(template: str, entry: MappingEntry) -> str:
    """Format a command template using mapping entry placeholders."""
    return template.format(
        item_name=entry.name,
        project_id=entry.project_id or "",
        namespace=entry.namespace,
    )


def run_command(command: str, payload: str | None, use_stdin: bool) -> None:
    """Run a shell command with optional stdin payload."""
    if use_stdin:
        subprocess.run(  # NOQA: S602
            command,
            input=payload,
            text=True,
            check=True,
            shell=True,
        )
    else:
        subprocess.run(command, check=True, shell=True)  # NOQA: S602


def main() -> int:
    """Run the migration helper and return an exit code."""
    args = parse_args()
    mapping_path = Path(args.mapping)
    if not mapping_path.exists():
        print(f"Mapping file not found: {mapping_path}", file=sys.stderr)
        return 1

    entries = load_mapping(mapping_path)
    if args.namespace:
        entries = [entry for entry in entries if entry.namespace == args.namespace]

    if args.apply and not args.command_template:
        print("--command-template is required when using --apply", file=sys.stderr)
        return 1

    if not entries:
        print("No entries to process.")
        return 0

    for entry in entries:
        secret = decrypt_sops(entry.sops_path)
        resolved_fields: Dict[str, str] = {}
        for bw_field, sops_key in entry.fields.items():
            try:
                resolved_fields[bw_field] = extract_secret_value(secret, sops_key)
            except KeyError as exc:
                raise RuntimeError(f"Missing key {sops_key} in {entry.sops_path}") from exc

        print(f"Item: {entry.name} (namespace: {entry.namespace})")
        for bw_field, value in resolved_fields.items():
            print(f"  - {bw_field}: {redact(value, args.show_values)}")

        payload = json.dumps(
            {
                "name": entry.name,
                "project_id": entry.project_id,
                "fields": resolved_fields,
            }
        )

        if not args.apply:
            continue

        if args.check_template:
            check_cmd = format_command(args.check_template, entry)
            result = subprocess.run(check_cmd, shell=True)  # NOQA: S602
            if result.returncode == 0 and not args.force:
                print("  - skipped (exists; use --force to override)")
                continue

        command = format_command(args.command_template, entry)
        run_command(command, payload, args.stdin)
        print("  - applied")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
