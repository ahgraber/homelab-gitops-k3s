#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Create a placeholder 1Password item for an app, to be filled in by hand.

Creates an item titled ``{namespace}.{app}`` in the homelab vault with the
requested fields set to a sentinel value, so the item and its ``op://``
references exist before the real values are known.

Existing fields are never touched. Re-running against an item that already
exists adds only the fields that are missing, so a half-filled item cannot be
reset to placeholders.

Usage:
    uv run scripts/onepassword/create_item.py <namespace> <app> [field ...]

Fields default to the ``concealed`` type; append ``[text]`` for values that
should stay readable in the 1Password UI, such as a username.

Examples
--------
    uv run scripts/onepassword/create_item.py default galene \
        'adminUsername[text]' adminPasswordHash turnKeyId turnApiToken
    uv run scripts/onepassword/create_item.py default galene --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess

# Deliberately loud rather than empty: an unfilled field that syncs to the
# cluster should be obvious in logs and greppable, not a silent empty string.
PLACEHOLDER = "REPLACE_ME"
CATEGORY = "login"
FIELD_RE = re.compile(r"^(?P<label>[A-Za-z0-9_.-]+)(?:\[(?P<type>text|concealed)\])?$")


def run_op(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Invoke the 1Password CLI, capturing output."""
    return subprocess.run(  # noqa: S603
        ["op", *args],
        text=True,
        check=True,
        capture_output=True,
    )


def parse_field(spec: str) -> tuple[str, str]:
    """Parse a ``label`` or ``label[text]`` spec into (label, type)."""
    match = FIELD_RE.match(spec)
    if not match:
        raise SystemExit(f"error: invalid field {spec!r} (expected 'label' or 'label[text]')")
    return match["label"], match["type"] or "concealed"


def get_item(vault: str, title: str) -> dict | None:
    """Return the item as a dict, or None when it does not exist."""
    try:
        result = run_op(["item", "get", title, "--vault", vault, "--format", "json"])
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def existing_labels(item: dict) -> set[str]:
    """Collect the labels already present on an item."""
    return {field.get("label") for field in item.get("fields", []) if field.get("label")}


def item_url(item: dict) -> str | None:
    """Build an ``onepassword://`` deep link for the item, if possible."""
    item_id = item.get("id")
    vault_id = (item.get("vault") or {}).get("id")
    if not (item_id and vault_id):
        return None
    url = f"onepassword://view-item?v={vault_id}&i={item_id}"
    try:
        accounts = json.loads(run_op(["account", "list", "--format", "json"]).stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return url
    # Only disambiguate when it matters; with several accounts the right one is
    # unknowable from here, so fall back to the account-less URL.
    if len(accounts) == 1:
        account = accounts[0].get("account_uuid") or accounts[0].get("user_uuid")
        if account:
            url = f"onepassword://view-item?a={account}&v={vault_id}&i={item_id}"
    return url


def open_url(url: str) -> bool:
    """Best-effort: ask the desktop to open the deep link."""
    opener = "open" if platform.system() == "Darwin" else "xdg-open"
    try:
        subprocess.run([opener, url], check=True, capture_output=True)  # noqa: S603
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create a placeholder 1Password item for an app.",
    )
    parser.add_argument("namespace", help="Kubernetes namespace (e.g., default)")
    parser.add_argument("app", help="Application name (e.g., galene)")
    parser.add_argument(
        "fields",
        nargs="*",
        help="Field labels to create, e.g. turnKeyId 'adminUsername[text]'",
    )
    parser.add_argument(
        "--vault",
        default=os.environ.get("OP_VAULT", "homelab"),
        help="1Password vault name (default: homelab or $OP_VAULT)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the item in the 1Password app afterwards",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without calling op",
    )
    return parser.parse_args()


def main() -> None:
    """Create or top up a placeholder item, then offer to open it."""
    args = parse_args()
    title = f"{args.namespace}.{args.app}"
    requested = [parse_field(spec) for spec in args.fields]

    item = None if args.dry_run else get_item(args.vault, title)
    present = existing_labels(item) if item else set()
    missing = [(label, kind) for label, kind in requested if label not in present]
    assignments = [f"{label}[{kind}]={PLACEHOLDER}" for label, kind in missing]

    if args.dry_run:
        print(f"Would ensure item '{title}' in vault '{args.vault}' with:")
        for label, kind in requested:
            print(f"  {label} [{kind}] = {PLACEHOLDER}")
        return

    if item is None:
        run_op(["item", "create", "--vault", args.vault, "--category", CATEGORY, "--title", title, *assignments])
        print(f"Created '{title}' in vault '{args.vault}'")
        item = get_item(args.vault, title)
    elif assignments:
        run_op(["item", "edit", title, "--vault", args.vault, *assignments])
        print(f"Added {len(assignments)} field(s) to existing item '{title}'")
        item = get_item(args.vault, title)
    else:
        print(f"Item '{title}' already exists with all requested fields; nothing to do")

    if missing:
        print("Fields to fill in: " + ", ".join(label for label, _ in missing))

    print(f"\nReference these from an ExternalSecret as op://{args.vault}/{title}/<field>")
    print("Then run `just secrets sync` so ExternalSecrets pick up the values.")

    if item and not args.no_open:
        url = item_url(item)
        if url and open_url(url):
            print(f"\nOpened {title} in 1Password")
        elif url:
            print(f"\nCould not open the 1Password app; the item is at:\n  {url}")


if __name__ == "__main__":
    main()
