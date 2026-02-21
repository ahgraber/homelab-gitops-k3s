#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2",
# ]
# ///
"""Push 1Password ESO inventory entries via the op CLI.

Warnings
--------
- This script decrypts SOPS secrets locally to build payloads.
- Secrets are sent to the `op` CLI via stdin templates.

Usage:
    ./scripts/onepassword/push.py --inventory ./migration-out/inventory.json
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, TextIO, Tuple

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from onepassword.models import Inventory, InventoryEntry


class DecryptedSecret:
    """Wrapper for decrypted secret content with redacted repr."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    def __repr__(self) -> str:
        return "<DecryptedSecret redacted>"


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
    parser.add_argument("--check", action="store_true", help="Validate CLI auth and vault access before pushing.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without running op commands.")
    return parser.parse_args()


def load_inventory(path: Path) -> Inventory:
    """Load inventory JSON from disk."""
    return Inventory.model_validate_json(path.read_text())


def save_inventory(path: Path, payload: Inventory) -> None:
    """Persist inventory JSON to disk atomically."""
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(payload.model_dump_json(indent=2, exclude_none=True))
    os.chmod(tmp_path, 0o600)
    tmp_path.replace(path)
    os.chmod(path, 0o600)


def decrypt_sops(path: Path) -> DecryptedSecret:
    """Decrypt a SOPS file and return parsed JSON."""
    try:
        output = subprocess.check_output(  # NOQA: S603
            ["sops", "--decrypt", "--output-type", "json", str(path)]
        )
    except FileNotFoundError as exc:
        raise RuntimeError("sops is required but was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"sops failed to decrypt {path}") from exc
    return DecryptedSecret(json.loads(output.decode("utf-8")))


def extract_secret_value(secret: DecryptedSecret, key: str) -> str:
    """Extract a secret value from stringData/data, decoding base64 when needed."""
    payload = secret.payload
    string_data = payload.get("stringData", {})
    if key in string_data:
        return str(string_data[key])

    data = payload.get("data", {})
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
    """Redact concealed values in 1Password-style JSON structures."""
    if isinstance(payload, dict):
        redacted: Dict[str, Any] = {}
        field_type = str(payload.get("type") or payload.get("k") or "").upper()
        is_concealed = field_type == "CONCEALED"
        for key, value in payload.items():
            lowered = key.lower()
            if is_concealed and lowered in {"value", "v"}:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact_value_fields(value)
        return redacted
    if isinstance(payload, list):
        return [redact_value_fields(item) for item in payload]
    return payload


def sanitize_text_output(text: str) -> Optional[str]:
    """Redact sensitive content from command output text."""
    if not text:
        return None

    try:
        payload = json.loads(text)
        return json.dumps(redact_value_fields(payload), indent=2, sort_keys=True)
    except json.JSONDecodeError:
        pass

    redacted_lines: List[str] = []
    for line in text.splitlines():
        key_value_match = re.match(r"^(\s*[^:=]+?\s*[:=]\s*)(.*)$", line)
        if key_value_match:
            redacted_lines.append(f"{key_value_match.group(1)}<redacted>")
            continue
        redacted_lines.append(line)
    return "\n".join(redacted_lines)


def print_redacted_payload(payload: Dict[str, Any], *, stream: TextIO = sys.stderr) -> None:
    """Print a redacted JSON request payload."""
    print("  redacted request body:", file=stream)
    rendered = json.dumps(redact_value_fields(payload), indent=2, sort_keys=True)
    for line in rendered.splitlines():
        print(f"    {line}", file=stream)


def report_command_error(prefix: str, exc: subprocess.CalledProcessError) -> None:
    """Print a sanitized CLI failure with optional stdout/stderr."""
    stderr = sanitize_text_output((exc.stderr or "").strip())
    stdout = sanitize_text_output((exc.stdout or "").strip())
    print(prefix, file=sys.stderr)
    if stdout:
        print("  stdout:", file=sys.stderr)
        print(stdout, file=sys.stderr)
    if stderr:
        print("  stderr:", file=sys.stderr)
        print(stderr, file=sys.stderr)


def parse_existing_items(output: str) -> Tuple[Dict[str, str], List[str]]:
    """Parse `op item list` JSON into title->id map plus duplicate titles."""
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
            title = str(item.get("title") or "")
            if not title:
                continue
            if title in items and title not in duplicates:
                duplicates.append(title)
            items[title] = str(item.get("id") or "")
    return items, duplicates


def prompt_choice(existing_names: List[str]) -> str:
    """Prompt how to handle already-existing 1Password items."""
    print("Existing items detected:")
    for name in existing_names:
        print(f"  - {name}")
    print("Choose action: [p]er-item prompt, [a]pply all, [s]kip all")
    while True:
        choice = input("Choice (p/a/s): ").strip().lower()
        if choice in {"p", "a", "s"}:
            return choice


def should_apply(choice: str, item_title: str) -> bool:
    """Resolve apply/skip decision for an existing item title."""
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


def ensure_vault(vault: Optional[str]) -> str:
    """Require a vault value or raise a runtime error."""
    if not vault:
        raise RuntimeError("Missing vault; supply --vault or OP_VAULT.")
    return vault


def validate_vault_access(vault: str) -> None:
    """Validate that the configured vault is accessible via `op`."""
    try:
        run_command(["op", "vault", "get", vault, "--format", "json"])
    except subprocess.CalledProcessError as exc:
        report_command_error(f"ERROR: unable to access vault {vault}", exc)
        raise RuntimeError(f"Vault validation failed for {vault}") from exc


def sanitize_id_component(value: str, fallback: str) -> str:
    """Normalize a label into an ID-safe component with fallback."""
    candidate = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return candidate[:40] or fallback


def unique_id(base: str, used_ids: set[str]) -> str:
    """Return a unique ID by suffixing `_N` when required."""
    field_id = base
    counter = 1
    while field_id in used_ids:
        counter += 1
        field_id = f"{base}_{counter}"
    used_ids.add(field_id)
    return field_id


def make_custom_field_id(label: str, used_ids: set[str], section_label: Optional[str] = None) -> str:
    """Build a stable custom field ID (optionally namespaced by section)."""
    label_part = sanitize_id_component(label, "field")
    if section_label:
        section_part = sanitize_id_component(section_label, "section")
        return unique_id(f"{section_part}_{label_part}", used_ids)
    return unique_id(label_part, used_ids)


def make_section_id(label: str, used_ids: set[str]) -> str:
    """Build a stable section ID."""
    return unique_id(sanitize_id_component(label, "section"), used_ids)


def normalize_base_template(template: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize template shape and required defaults for payload building."""
    normalized = copy.deepcopy(template)
    if not str(normalized.get("category") or ""):
        normalized["category"] = "LOGIN"
    if not isinstance(normalized.get("fields"), list):
        normalized["fields"] = []
    if not isinstance(normalized.get("sections"), list):
        normalized["sections"] = []
    return normalized


def load_op_template() -> Dict[str, Any]:
    """Load a Login template from `op`, with a minimal fallback."""
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
            return normalize_base_template(payload)
    return {"category": "LOGIN", "fields": [], "sections": []}


def load_entry_fields(entry: InventoryEntry) -> Optional[Dict[str, str]]:
    """Load one inventory entry's decrypted field values."""
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
    try:
        for field in entry.fields:
            try:
                field_values[field] = extract_secret_value(secret, field)
            except (KeyError, RuntimeError) as exc:
                print(f"WARNING: {entry.sops_path}: {exc}", file=sys.stderr)
                return None
        return field_values
    finally:
        secret.payload.clear()
        del secret


def prepare_item_batches(entries: List[InventoryEntry]) -> List[Dict[str, Any]]:
    """Group inventory entries into per-item batches."""
    by_item: Dict[str, Dict[str, Any]] = {}
    ordered_names: List[str] = []

    for entry in entries:
        batch = by_item.get(entry.item_name)
        if batch is None:
            batch = {
                "item_name": entry.item_name,
                "entries": [],
            }
            by_item[entry.item_name] = batch
            ordered_names.append(entry.item_name)

        batch["entries"].append(entry)

    prepared: List[Dict[str, Any]] = []
    for item_name in ordered_names:
        batch = by_item[item_name]
        if not batch["entries"]:
            continue
        prepared.append(batch)

    return prepared


def collect_batch_values(entries: List[InventoryEntry], item_name: str) -> Optional[Dict[str, Dict[str, str]]]:
    """Decrypt and merge fields for one item batch, detecting conflicts."""
    field_values: Dict[str, str] = {}
    field_sources: Dict[str, str] = {}
    section_fields: Dict[Optional[str], Dict[str, str]] = {}
    conflicts: List[str] = []

    for entry in entries:
        entry_fields = load_entry_fields(entry)
        if entry_fields is None:
            return None
        for field_name, field_value in entry_fields.items():
            existing = field_values.get(field_name)
            if existing is None:
                field_values[field_name] = field_value
                field_sources[field_name] = entry.sops_path
                section_name = entry.section or None
                section_bucket = section_fields.setdefault(section_name, {})
                section_bucket[field_name] = field_value
                continue
            if existing != field_value:
                conflicts.append(f"field {field_name!r}: {field_sources[field_name]} != {entry.sops_path}")

    if conflicts:
        print(f"ERROR: conflicting values detected for item {item_name}; skipping item.", file=sys.stderr)
        for conflict in sorted(set(conflicts)):
            print(f"  - {conflict}", file=sys.stderr)
        return None
    if not field_values:
        print(f"WARNING: no fields to apply for item {item_name}; skipping.", file=sys.stderr)
        return None

    return {"field_values": field_values, "section_fields": section_fields}


def build_item_payload(
    base_template: Dict[str, Any],
    item_title: str,
    fields_by_section: Dict[Optional[str], Dict[str, str]],
) -> Dict[str, Any]:
    """Build an `op item create/edit` payload for one item title."""
    payload = copy.deepcopy(base_template)
    payload["title"] = item_title

    template_fields = payload.get("fields") if isinstance(payload.get("fields"), list) else []
    payload["fields"] = template_fields

    template_sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
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
        if isinstance(label, str) and isinstance(section_id, str):
            section_lookup.setdefault(label, section_id)

    def ensure_section(label: str) -> str:
        section_id = section_lookup.get(label)
        if section_id:
            return section_id
        section_id = make_section_id(label, used_section_ids)
        template_sections.append({"id": section_id, "label": label})
        section_lookup[label] = section_id
        return section_id

    remaining_default = dict(fields_by_section.get(None, {}))
    for field in template_fields:
        if not isinstance(field, dict):
            continue
        field_id = field.get("id")
        label = field.get("label")
        for key in (field_id, label):
            if isinstance(key, str) and key in remaining_default:
                field["value"] = remaining_default.pop(key)
                break

    for key, value in sorted(remaining_default.items()):
        template_fields.append(
            {
                "id": make_custom_field_id(key, used_ids),
                "type": "CONCEALED",
                "label": key,
                "value": value,
            }
        )

    for section_label, section_fields in sorted(
        fields_by_section.items(), key=lambda item: (item[0] is None, str(item[0]))
    ):
        if section_label is None:
            continue
        section_id = ensure_section(section_label)
        for key, value in sorted(section_fields.items()):
            template_fields.append(
                {
                    "id": make_custom_field_id(key, used_ids, section_label=section_label),
                    "type": "CONCEALED",
                    "label": key,
                    "section": {"id": section_id},
                    "value": value,
                }
            )

    return payload


def list_existing_items(vault: str) -> Tuple[Dict[str, str], List[str]]:
    """List existing items in a vault and return lookup + duplicates."""
    try:
        result = run_command(["op", "item", "list", "--vault", vault, "--format", "json"])
    except subprocess.CalledProcessError as exc:
        report_command_error(f"WARNING: list command failed for vault {vault}", exc)
        return {}, []
    return parse_existing_items((result.stdout or "").strip())


def apply_item_batches(
    batches: List[Dict[str, Any]],
    existing_lookup: Dict[str, str],
    choice: str,
    vault: str,
    args: argparse.Namespace,
    base_template: Dict[str, Any],
) -> bool:
    """Apply all prepared item batches and return whether inventory changed."""
    updated = False

    for batch in batches:
        item_title = batch["item_name"]
        entries: List[InventoryEntry] = batch["entries"]
        merged = collect_batch_values(entries, item_title)
        if merged is None:
            continue
        field_values = merged["field_values"]
        section_fields = merged["section_fields"]

        empty_fields = sorted(name for name, value in field_values.items() if value == "")
        if empty_fields:
            joined = ", ".join(empty_fields)
            print(
                f"WARNING: skipping {item_title} due to empty secret values: {joined}",
                file=sys.stderr,
            )
            continue

        item_id = existing_lookup.get(item_title) or next((entry.item_id for entry in entries if entry.item_id), None)

        if item_title in existing_lookup:
            existing_id = existing_lookup.get(item_title)
            if existing_id:
                item_id = existing_id
                for entry in entries:
                    if entry.item_id != existing_id:
                        entry.item_id = existing_id
                        updated = True
            if not should_apply(choice, item_title):
                continue

        payload = build_item_payload(base_template, item_title, section_fields)
        payload_json = json.dumps(payload)

        print(f"Applying {item_title} (vault: {vault})")
        try:
            if args.dry_run:
                print_redacted_payload(payload, stream=sys.stdout)
                continue

            if item_id:
                response = run_command(
                    ["op", "item", "edit", item_id, "--vault", vault, "--format", "json"],
                    input_text=payload_json,
                )
            else:
                response = run_command(
                    ["op", "item", "create", "--vault", vault, "--format", "json", "-"],
                    input_text=payload_json,
                )

            try:
                response_obj = json.loads((response.stdout or "").strip())
            except json.JSONDecodeError:
                response_obj = None

            new_item_id = response_obj.get("id") if isinstance(response_obj, dict) else None
            if isinstance(new_item_id, str) and new_item_id:
                existing_lookup[item_title] = new_item_id
                for entry in entries:
                    if entry.item_id != new_item_id:
                        entry.item_id = new_item_id
                        updated = True
        except subprocess.CalledProcessError as exc:
            report_command_error(f"ERROR: failed to apply item {item_title}", exc)
            print_redacted_payload(payload, stream=sys.stderr)
            continue
        finally:
            payload_json = ""
            field_values.clear()
            section_fields.clear()
            payload.clear()
            del payload

    return updated


def resolve_vault(args: argparse.Namespace, inventory: Inventory) -> Optional[str]:
    """Resolve vault from CLI args, inventory default, or environment."""
    return args.vault or inventory.vault or get_env("OP_VAULT")


def main() -> int:
    """Run the push workflow end-to-end."""
    os.umask(0o077)
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
    if not inventory.entries:
        print("No entries to process.")
        return 0

    try:
        vault = ensure_vault(resolve_vault(args, inventory))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        validate_vault_access(vault)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    base_template = load_op_template()

    existing_lookup, duplicates = list_existing_items(vault)
    if duplicates:
        print(
            "WARNING: duplicate 1Password item titles detected; updates apply to the last-seen ID:",
            file=sys.stderr,
        )
        print("  " + ", ".join(sorted(duplicates)), file=sys.stderr)

    batches = prepare_item_batches(inventory.entries)
    if not batches:
        print("No valid entries to process.")
        return 0

    existing_names = sorted(batch["item_name"] for batch in batches if batch["item_name"] in existing_lookup)
    choice = "p"
    if existing_names:
        choice = prompt_choice(existing_names)
        if choice == "s":
            print("Skipping existing items.")
        elif choice == "a":
            print("Applying to existing items.")

    updated = apply_item_batches(batches, existing_lookup, choice, vault, args, base_template)

    if inventory.vault != vault:
        inventory.vault = vault
        updated = True

    if args.write_inventory and updated:
        save_inventory(inventory_path, inventory)
        print(f"Updated inventory: {inventory_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
