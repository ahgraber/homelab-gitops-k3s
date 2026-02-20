#!/usr/bin/env python3
"""Push 1Password ESO inventory entries via the op CLI.

Warnings
--------
- Best-effort parsing only; this script does not validate your intent.
- This script decrypts SOPS secrets locally to build payloads.
- Secrets are sent to the `op` CLI via stdin templates.

Usage:
    ./scripts/onepassword/push.py --inventory ./migration-out/inventory.json
"""

from __future__ import annotations

import argparse
import base64
import copy
from dataclasses import dataclass, field as dataclass_field
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.onepassword.models import Inventory, InventoryEntry


@dataclass
class ItemBatch:
    """Prepared payload input for a single 1Password item."""

    item_name: str
    entries: List[InventoryEntry] = dataclass_field(default_factory=list)
    field_values: Dict[str, str] = dataclass_field(default_factory=dict)
    section_fields: Dict[Optional[str], Dict[str, str]] = dataclass_field(default_factory=dict)
    field_sources: Dict[str, str] = dataclass_field(default_factory=dict)
    conflicts: List[str] = dataclass_field(default_factory=list)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Push 1Password ESO inventory entries via op CLI.",
    )
    parser.add_argument(
        "--inventory",
        help="Path to inventory.json created by the crawl script.",
    )
    parser.add_argument(
        "--vault",
        help="Default 1Password vault name (used when inventory lacks vault).",
    )
    parser.add_argument(
        "--write-inventory",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write back item_id updates to the inventory file.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate CLI auth and vault access before pushing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without running op commands.",
    )
    return parser.parse_args()


def load_inventory(path: Path) -> Inventory:
    """Load inventory JSON from disk."""
    return Inventory.model_validate_json(path.read_text())


def save_inventory(path: Path, payload: Inventory) -> None:
    """Persist inventory JSON to disk atomically."""
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(payload.model_dump_json(indent=2, exclude_none=True))
    tmp_path.replace(path)


def decrypt_sops(path: Path) -> Dict[str, Any]:
    """Decrypt a SOPS file into a JSON dict."""
    try:
        output = subprocess.check_output(  # NOQA: S603
            ["sops", "--decrypt", "--output-type", "json", str(path)]
        )
    except FileNotFoundError as exc:
        raise RuntimeError("sops is required but was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"sops failed to decrypt {path}") from exc

    return json.loads(output.decode("utf-8"))


def extract_secret_value(secret: Dict[str, Any], key: str) -> str:
    """Extract a secret value from stringData/data."""
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


def get_env(*names: str) -> Optional[str]:
    """Return the first matching environment variable."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def run_command(args: List[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    """Run a CLI command and return the completed process."""
    return subprocess.run(  # NOQA: S603
        args,
        input=input_text,
        text=True,
        check=True,
        capture_output=True,
    )


def redact_value_fields(payload: Any) -> Any:
    """Redact common sensitive value fields in a JSON payload."""
    if isinstance(payload, dict):
        redacted = {}
        for key, value in payload.items():
            lowered = key.lower()
            if lowered in {"value", "token", "password", "op_session", "op_connect_token"}:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact_value_fields(value)
        return redacted
    if isinstance(payload, list):
        return [redact_value_fields(item) for item in payload]
    return payload


def sanitize_output(text: str) -> Optional[str]:
    """Sanitize JSON output by redacting value fields when possible."""
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    sanitized = redact_value_fields(payload)
    return json.dumps(sanitized, indent=2, sort_keys=True)


def report_command_error(prefix: str, exc: subprocess.CalledProcessError) -> None:
    """Report a command failure without leaking sensitive values."""
    stderr = (exc.stderr or "").strip()
    stdout = (exc.stdout or "").strip()
    print(prefix, file=sys.stderr)
    if stdout and stdout == stderr:
        sanitized = sanitize_output(stdout)
        if sanitized:
            print("  output:", file=sys.stderr)
            print(sanitized, file=sys.stderr)
        else:
            print("  output: <redacted>", file=sys.stderr)
        return
    if stdout:
        sanitized = sanitize_output(stdout)
        if sanitized:
            print("  stdout:", file=sys.stderr)
            print(sanitized, file=sys.stderr)
        else:
            print("  stdout: <redacted>", file=sys.stderr)
    if stderr:
        sanitized = sanitize_output(stderr)
        if sanitized:
            print("  stderr:", file=sys.stderr)
            print(sanitized, file=sys.stderr)
        else:
            print("  stderr: <redacted>", file=sys.stderr)


def parse_existing_items(output: str) -> Tuple[Dict[str, str], List[str]]:
    """Parse op list output into a title->id mapping and duplicate titles."""
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return {}, []

    items: Dict[str, str] = {}
    duplicates: List[str] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            item_id = item.get("id")
            if not title:
                continue
            if title in items and title not in duplicates:
                duplicates.append(title)
            items[str(title)] = str(item_id or "")
    return items, duplicates


def prompt_choice(existing_names: List[str]) -> str:
    """Prompt for how to handle existing items."""
    print("Existing items detected:")
    for name in existing_names:
        print(f"  - {name}")
    print("Choose action: [p]er-item prompt, [a]pply all, [s]kip all")
    while True:
        choice = input("Choice (p/a/s): ").strip().lower()
        if choice in {"p", "a", "s"}:
            return choice


def ensure_vault(vault: Optional[str]) -> str:
    """Ensure a vault is configured."""
    if not vault:
        raise RuntimeError("Missing vault; supply --vault or OP_VAULT.")
    return vault


def validate_vault_access(vault: str) -> None:
    """Validate vault access via op CLI."""
    try:
        run_command(["op", "vault", "get", vault, "--format", "json"])
    except subprocess.CalledProcessError as exc:
        report_command_error(f"ERROR: unable to access vault {vault}", exc)
        raise RuntimeError(f"Vault validation failed for {vault}") from exc


def should_apply(choice: str, item_title: str) -> bool:
    """Decide whether to apply for an existing item based on choice."""
    if choice == "s":
        print(f"Skipping {item_title} (exists).")
        return False
    if choice == "a":
        return True
    answer = input(f"Item {item_title} exists. Apply? [y/N]: ").strip().lower()
    if answer == "y":
        return True
    print(f"Skipping {item_title}.")
    return False


def make_custom_field_id(label: str, used_ids: set[str]) -> str:
    """Generate a stable custom field id for a label."""
    candidate = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "field"
    candidate = candidate[:40]
    base = f"custom_{candidate}"
    field_id = base
    counter = 1
    while field_id in used_ids:
        counter += 1
        field_id = f"{base}_{counter}"
    used_ids.add(field_id)
    return field_id


def make_section_id(label: str, used_ids: set[str]) -> str:
    """Generate a stable section id from a section label."""
    candidate = re.sub(r"[^a-zA-Z0-9_-]+", "_", label).strip("_") or "section"
    candidate = candidate[:40]
    base = f"section_{candidate}"
    section_id = base
    counter = 1
    while section_id in used_ids:
        counter += 1
        section_id = f"{base}_{counter}"
    used_ids.add(section_id)
    return section_id


def build_item_payload(
    base_template: Dict[str, Any],
    item_title: str,
    fields_by_section: Dict[Optional[str], Dict[str, str]],
) -> Dict[str, Any]:
    """Build an item payload from a Login template and secret field values."""
    payload = copy.deepcopy(base_template)
    payload["title"] = item_title

    template_fields = payload.get("fields")
    if not isinstance(template_fields, list):
        template_fields = []
        payload["fields"] = template_fields

    template_sections = payload.get("sections")
    if not isinstance(template_sections, list):
        template_sections = []
        payload["sections"] = template_sections

    used_ids = {
        str(field.get("id"))
        for field in template_fields
        if isinstance(field, dict) and isinstance(field.get("id"), str)
    }
    used_section_ids = {
        str(section.get("id"))
        for section in template_sections
        if isinstance(section, dict) and isinstance(section.get("id"), str)
    }
    section_lookup: Dict[str, str] = {}
    for section in template_sections:
        if not isinstance(section, dict):
            continue
        label = section.get("label")
        section_id = section.get("id")
        if isinstance(label, str) and isinstance(section_id, str) and label not in section_lookup:
            section_lookup[label] = section_id

    def ensure_section(label: str) -> str:
        section_id = section_lookup.get(label)
        if section_id:
            return section_id
        section_id = make_section_id(label, used_section_ids)
        template_sections.append({"id": section_id, "label": label})
        section_lookup[label] = section_id
        return section_id

    # Map common built-in login fields first to avoid duplicate labels.
    default_fields = dict(fields_by_section.get(None, {}))
    remaining = dict(default_fields)
    for field in template_fields:
        if not isinstance(field, dict):
            continue
        field_id = field.get("id")
        label = field.get("label")
        for key in (field_id, label):
            if isinstance(key, str) and key in remaining:
                field["value"] = remaining.pop(key)
                break

    for key, value in sorted(remaining.items()):
        template_fields.append(
            {
                "id": make_custom_field_id(key, used_ids),
                "type": "CONCEALED",
                "purpose": "custom",
                "label": key,
                "value": value,
            }
        )

    for section_label, section_fields in sorted(
        fields_by_section.items(),
        key=lambda item: (item[0] is None, str(item[0])),
    ):
        if section_label is None:
            continue
        section_id = ensure_section(section_label)
        for key, value in sorted(section_fields.items()):
            template_fields.append(
                {
                    "id": make_custom_field_id(f"{section_label}_{key}", used_ids),
                    "type": "CONCEALED",
                    "purpose": "custom",
                    "label": key,
                    "section": {"id": section_id},
                    "value": value,
                }
            )

    return payload


def load_login_template() -> Dict[str, Any]:
    """Load a Login item template from op CLI."""
    commands = [
        ["op", "item", "template", "get", "Login", "--format", "json"],
        ["op", "item", "template", "get", "Login"],
    ]
    for command in commands:
        try:
            result = run_command(command)
        except subprocess.CalledProcessError:
            continue
        raw = (result.stdout or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise RuntimeError("Unable to load Login template via `op item template get Login`")


def load_entry_fields(entry: InventoryEntry) -> Optional[Dict[str, str]]:
    """Load and decrypt fields for one inventory entry."""
    sops_path = Path(entry.sops_path)
    if not sops_path.exists():
        print(f"WARNING: SOPS file not found: {sops_path}", file=sys.stderr)
        return None

    try:
        secret = decrypt_sops(sops_path)
    except RuntimeError as exc:
        print(f"WARNING: {exc}", file=sys.stderr)
        return None

    field_values: Dict[str, str] = {}
    missing_fields = False
    for field in entry.fields:
        try:
            field_values[field] = extract_secret_value(secret, field)
        except (KeyError, RuntimeError) as exc:
            print(f"WARNING: {entry.sops_path}: {exc}", file=sys.stderr)
            missing_fields = True
    if missing_fields:
        print(f"Skipping {entry.item_name} due to missing/decode errors.", file=sys.stderr)
        return None

    return field_values


def prepare_item_batches(entries: List[InventoryEntry]) -> List[ItemBatch]:
    """Prepare per-item payloads from inventory entries."""
    by_item: Dict[str, ItemBatch] = {}
    ordered_names: List[str] = []

    for entry in entries:
        entry_fields = load_entry_fields(entry)
        if entry_fields is None:
            continue

        batch = by_item.get(entry.item_name)
        if batch is None:
            batch = ItemBatch(item_name=entry.item_name)
            by_item[entry.item_name] = batch
            ordered_names.append(entry.item_name)
        batch.entries.append(entry)

        for field_name, field_value in entry_fields.items():
            if field_name not in batch.field_values:
                batch.field_values[field_name] = field_value
                batch.field_sources[field_name] = entry.sops_path
                section_name = entry.section or None
                section_bucket = batch.section_fields.setdefault(section_name, {})
                section_bucket[field_name] = field_value
                continue
            if batch.field_values[field_name] == field_value:
                continue
            batch.conflicts.append(
                f"field {field_name!r}: {batch.field_sources[field_name]} != {entry.sops_path}"
            )

    prepared: List[ItemBatch] = []
    for item_name in ordered_names:
        batch = by_item[item_name]
        if batch.conflicts:
            print(
                f"ERROR: conflicting values detected for item {batch.item_name}; skipping item.",
                file=sys.stderr,
            )
            for conflict in sorted(set(batch.conflicts)):
                print(f"  - {conflict}", file=sys.stderr)
            continue
        if not batch.field_values:
            print(f"WARNING: no fields to apply for item {batch.item_name}; skipping.", file=sys.stderr)
            continue
        prepared.append(batch)

    return prepared


def apply_item_batches(
    batches: List[ItemBatch],
    existing_lookup: Dict[str, str],
    choice: str,
    vault: str,
    args: argparse.Namespace,
    login_template: Dict[str, Any],
) -> bool:
    """Apply prepared item batches using op and return whether inventory changed."""
    updated = False
    for batch in batches:
        item_title = batch.item_name
        exists = item_title in existing_lookup
        item_id = existing_lookup.get(item_title)
        if not item_id:
            item_id = next((entry.item_id for entry in batch.entries if entry.item_id), None)

        if exists:
            existing_id = existing_lookup.get(item_title)
            if existing_id:
                item_id = existing_id
                for entry in batch.entries:
                    if entry.item_id != existing_id:
                        entry.item_id = existing_id
                        updated = True
            if not should_apply(choice, item_title):
                continue

        payload = build_item_payload(login_template, item_title, batch.section_fields)
        payload_json = json.dumps(payload)

        print(f"Applying {item_title} (vault: {vault})")
        if args.dry_run:
            continue

        try:
            if item_id:
                response = run_command(
                    ["op", "item", "edit", item_id, "--vault", vault, "--template", "-", "--format", "json"],
                    input_text=payload_json,
                )
            else:
                response = run_command(
                    ["op", "item", "create", "--vault", vault, "--template", "-", "--format", "json"],
                    input_text=payload_json,
                )
        except subprocess.CalledProcessError as exc:
            report_command_error(f"ERROR: failed to apply item {item_title}", exc)
            continue

        new_item_id = None
        raw_output = (response.stdout or "").strip()
        if raw_output:
            try:
                payload_obj = json.loads(raw_output)
            except json.JSONDecodeError:
                payload_obj = None
            if isinstance(payload_obj, dict):
                new_item_id = payload_obj.get("id")

        if isinstance(new_item_id, str) and new_item_id:
            existing_lookup[item_title] = new_item_id
            for entry in batch.entries:
                if entry.item_id != new_item_id:
                    entry.item_id = new_item_id
                    updated = True

    return updated


def resolve_vault(args: argparse.Namespace, inventory: Inventory) -> Optional[str]:
    """Resolve vault from args/env/inventory."""
    return args.vault or inventory.vault or get_env("OP_VAULT")


def list_existing_items(vault: str) -> Tuple[Dict[str, str], List[str]]:
    """List existing 1Password items in a vault."""
    list_cmd = ["op", "item", "list", "--vault", vault, "--format", "json"]
    try:
        result = run_command(list_cmd)
    except subprocess.CalledProcessError as exc:
        report_command_error(f"WARNING: list command failed for vault {vault}", exc)
        return {}, []
    return parse_existing_items((result.stdout or "").strip())


def main() -> int:
    """Run the push workflow against 1Password."""
    args = parse_args()

    if args.check and not args.inventory:
        try:
            vault = ensure_vault(args.vault or get_env("OP_VAULT"))
            validate_vault_access(vault)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("check succeeded.")
        return 0

    if not args.inventory:
        print("--inventory is required unless --check is used", file=sys.stderr)
        return 1

    inventory_path = Path(args.inventory)
    if not inventory_path.exists():
        print(f"Inventory file not found: {inventory_path}", file=sys.stderr)
        return 1

    inventory = load_inventory(inventory_path)
    entries = inventory.entries
    if not entries:
        print("No entries to process.")
        return 0

    try:
        vault = ensure_vault(resolve_vault(args, inventory))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.check:
        try:
            validate_vault_access(vault)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    try:
        login_template = load_login_template()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    existing_lookup, duplicates = list_existing_items(vault)
    if duplicates:
        print(
            "WARNING: duplicate 1Password item titles detected; updates apply to the last-seen ID:",
            file=sys.stderr,
        )
        print("  " + ", ".join(sorted(duplicates)), file=sys.stderr)

    batches = prepare_item_batches(entries)
    if not batches:
        print("No valid entries to process.")
        return 0

    existing_names = sorted(
        {
            batch.item_name
            for batch in batches
            if batch.item_name in existing_lookup
        }
    )

    choice = "p"
    if existing_names:
        choice = prompt_choice(existing_names)
        if choice == "s":
            print("Skipping existing items.")
        elif choice == "a":
            print("Applying to existing items.")

    updated = apply_item_batches(batches, existing_lookup, choice, vault, args, login_template)

    if inventory.vault != vault:
        inventory.vault = vault
        updated = True

    if args.write_inventory and updated:
        save_inventory(inventory_path, inventory)
        print(f"Updated inventory: {inventory_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
