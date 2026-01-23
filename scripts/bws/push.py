#!/usr/bin/env python3
"""Push Bitwarden ESO inventory entries via the bws CLI.

Warnings
--------
- Best-effort parsing only; this script does not validate your intent.
- This script decrypts SOPS secrets locally to build payloads.
- Each field is stored as a separate Bitwarden secret key.
- Secrets are sent via the CLI; avoid logging plaintext values.

Usage:
    ./scripts/bws/push.py --inventory ./migration-out/inventory.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from scripts.bws.models import Inventory, InventoryEntry


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Push Bitwarden ESO inventory entries via bws CLI.",
    )
    parser.add_argument(
        "--inventory",
        help="Path to inventory.json created by the crawl script.",
    )
    parser.add_argument(
        "--project-id",
        help="Default Bitwarden project ID (used when entries lack project_id).",
    )
    parser.add_argument(
        "--write-inventory",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write back secret_id updates to the inventory file.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate project/org configuration before pushing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without running bws commands.",
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


def run_command(args: List[str]) -> subprocess.CompletedProcess[str]:
    """Run a CLI command and return the completed process."""
    return subprocess.run(  # NOQA: S603
        args,
        text=True,
        check=True,
        capture_output=True,
    )


def redact_value_fields(payload: Any) -> Any:
    """Redact value fields in a JSON payload."""
    if isinstance(payload, dict):
        return {
            key: ("<redacted>" if key == "value" else redact_value_fields(value)) for key, value in payload.items()
        }
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
    """Parse bws list output into a key->id mapping and duplicate keys."""
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
            key = item.get("key") or item.get("name")
            item_id = item.get("id")
            if key:
                if key in items and key not in duplicates:
                    duplicates.append(key)
                items[key] = item_id or ""
    return items, duplicates


def prompt_choice(existing_names: List[str]) -> str:
    """Prompt for how to handle existing items."""
    print("Existing secrets detected:")
    for name in existing_names:
        print(f"  - {name}")
    print("Choose action: [p]er-item prompt, [a]pply all, [s]kip all")
    while True:
        choice = input("Choice (p/a/s): ").strip().lower()
        if choice in {"p", "a", "s"}:
            return choice


def ensure_project_id(project_id: str | None) -> str:
    """Ensure a project_id is available."""
    if not project_id:
        raise RuntimeError("Missing project_id; supply --project-id.")
    return project_id


def validate_project_org(project_id: str, expected_org_id: Optional[str]) -> None:
    """Validate the project belongs to the expected org, if provided."""
    if not expected_org_id:
        return
    try:
        result = run_command(["bws", "project", "get", project_id, "--output", "json"])
    except subprocess.CalledProcessError as exc:
        report_command_error("WARNING: project lookup failed", exc)
        return
    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        print("WARNING: project lookup returned non-JSON output; skipping org check", file=sys.stderr)
        return
    org_id = payload.get("organizationId") or payload.get("orgId")
    if not org_id:
        print("WARNING: project lookup missing organizationId; skipping org check", file=sys.stderr)
        return
    if str(org_id) != expected_org_id:
        raise RuntimeError(f"Project {project_id} org mismatch: {org_id} != {expected_org_id}")


def should_apply(choice: str, secret_key: str) -> bool:
    """Decide whether to apply for an existing secret based on choice."""
    if choice == "s":
        print(f"Skipping {secret_key} (exists).")
        return False
    if choice == "a":
        return True
    answer = input(f"Secret {secret_key} exists. Apply? [y/N]: ").strip().lower()
    if answer == "y":
        return True
    print(f"Skipping {secret_key}.")
    return False


def entry_key_name(namespace: str, app: str, purpose: str) -> str:
    """Build the Bitwarden secret key name for a SOPS entry."""
    return f"{namespace}/{app}-{purpose}"


def apply_entries(
    entries: List[InventoryEntry],
    existing_lookup: Dict[str, str],
    choice: str,
    project_id: str,
    args: argparse.Namespace,
) -> bool:
    """Apply inventory entries using bws and return whether inventory changed."""
    updated = False
    for entry in entries:
        existing_items = existing_lookup
        sops_path = Path(entry.sops_path)

        if not sops_path.exists():
            print(f"WARNING: SOPS file not found: {sops_path}", file=sys.stderr)
            continue

        secret = decrypt_sops(sops_path)
        fields = entry.fields
        note = f"{entry.namespace}/{entry.app}"
        key = entry_key_name(entry.namespace, entry.app, entry.purpose)
        exists = key in existing_items
        secret_id = entry.secret_id
        if exists:
            existing_id = existing_items.get(key)
            if existing_id and entry.secret_id != existing_id:
                entry.secret_id = existing_id
                updated = True
            secret_id = existing_id or entry.secret_id
            if not should_apply(choice, key):
                continue

        payload = {field: extract_secret_value(secret, field) for field in fields}
        value = json.dumps(payload, sort_keys=True, indent=2)
        print(f"Applying {key} (project: {project_id})")
        if args.dry_run:
            continue

        try:
            if secret_id:
                response = run_command(
                    [
                        "bws",
                        "secret",
                        "edit",
                        "--value",
                        value,
                        "--note",
                        note,
                        "--project-id",
                        project_id,
                        secret_id,
                        "--output",
                        "json",
                    ]
                )
            else:
                response = run_command(
                    [
                        "bws",
                        "secret",
                        "create",
                        key,
                        value,
                        project_id,
                        "--note",
                        note,
                        "--output",
                        "json",
                    ]
                )
        except subprocess.CalledProcessError as exc:
            report_command_error(f"ERROR: failed to apply secret {key}", exc)
            continue

        new_secret_id = None
        raw_output = response.stdout.strip()
        if raw_output:
            try:
                payload = json.loads(raw_output)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                new_secret_id = payload.get("id")
        if new_secret_id and entry.secret_id != new_secret_id:
            entry.secret_id = str(new_secret_id)
            updated = True

    return updated


def resolve_project_id(args: argparse.Namespace, inventory: Inventory) -> Optional[str]:
    """Resolve Bitwarden project ID from args/env/inventory."""
    return args.project_id or inventory.project_id or get_env("BWS_PROJECT_ID", "PROJECT_ID")


def list_existing_items(project_id: str) -> Tuple[Dict[str, str], List[str]]:
    """List existing Bitwarden secrets for a project."""
    list_cmd = ["bws", "secret", "list", project_id, "--output", "json"]
    try:
        result = run_command(list_cmd)
    except subprocess.CalledProcessError as exc:
        report_command_error(f"WARNING: list command failed for project {project_id}", exc)
        return {}, []
    return parse_existing_items(result.stdout.strip())


def main() -> int:
    """Run the push workflow against Bitwarden."""
    args = parse_args()
    if args.check and not args.inventory:
        project_id = args.project_id or get_env("BWS_PROJECT_ID", "PROJECT_ID")
        if not project_id:
            print("Missing project_id; supply --project-id or BWS_PROJECT_ID.", file=sys.stderr)
            return 1
        expected_org_id = get_env("BWS_ORG_ID", "ORGANIZATION_ID")
        if not expected_org_id:
            print("Missing org_id; supply --org-id or BWS_ORG_ID.", file=sys.stderr)
            return 1
        try:
            validate_project_org(project_id, expected_org_id)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print("`check` succeeded.")
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
        project_id = ensure_project_id(resolve_project_id(args, inventory))
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.check:
        expected_org_id = inventory.org_id or get_env("BWS_ORG_ID", "ORGANIZATION_ID")
        try:
            validate_project_org(project_id, expected_org_id)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    existing_lookup, duplicates = list_existing_items(project_id)
    if duplicates:
        print(
            "WARNING: duplicate Bitwarden keys detected; overwrites apply to the last-seen ID:",
            file=sys.stderr,
        )
        print("  " + ", ".join(sorted(duplicates)), file=sys.stderr)
    existing_names = sorted(
        {
            entry_key_name(entry.namespace, entry.app, entry.purpose)
            for entry in entries
            if entry_key_name(entry.namespace, entry.app, entry.purpose) in existing_lookup
        }
    )

    choice = "p"
    if existing_names:
        choice = prompt_choice(existing_names)
        if choice == "s":
            print("Skipping existing secrets.")
        elif choice == "a":
            print("Applying to existing secrets (command may overwrite).")

    updated = apply_entries(entries, existing_lookup, choice, project_id, args)

    if args.write_inventory and updated:
        save_inventory(inventory_path, inventory)
        print(f"Updated inventory: {inventory_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
