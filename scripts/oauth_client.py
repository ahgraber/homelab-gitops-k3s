#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Generate an OAuth client secret for Authelia and store it in 1Password.

Creates a random client secret and its PBKDF2-SHA512 digest, then:
  1. Stores the plaintext secret in the app's 1Password item ({namespace}.{app})
  2. Stores the PBKDF2 digest in the Authelia 1Password item (security.authelia)

Usage:
    uv run scripts/oauth_client.py <namespace> <app> [--vault homelab] [--dry-run]

Examples
--------
    uv run scripts/oauth_client.py default actual-budget
    uv run scripts/oauth_client.py default actual-budget --dry-run
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import string
import subprocess
import sys

# --- Authelia PBKDF2 settings (must match authelia_hash.py) ---
PASSWORD_LENGTH = 72
ITERATIONS = 310000
DIGEST = "sha512"
SALT_LEN = 16
CHARSET = string.ascii_letters + string.digits + "-._~"

AUTHELIA_ITEM = "security.authelia"
AUTHELIA_SECTION = "Client Secrets"


def generate_password() -> str:
    """Generate a random RFC 3986 safe password."""
    return "".join(secrets.choice(CHARSET) for _ in range(PASSWORD_LENGTH))


def pbkdf2_derive(password: str, salt: bytes) -> bytes:
    """Return the PBKDF2 digest for the given password and salt."""
    return hashlib.pbkdf2_hmac(DIGEST, password.encode(), salt, ITERATIONS)


def authelia_b64(data: bytes) -> str:
    """Encode bytes using Authelia's PBKDF2 base64 variant."""
    return base64.b64encode(data, altchars=b"./").decode().rstrip("=")


def make_digest(password: str) -> str:
    """Generate the full PBKDF2 digest string for Authelia."""
    salt = os.urandom(SALT_LEN)
    derived = pbkdf2_derive(password, salt)
    return f"$pbkdf2-{DIGEST}${ITERATIONS}${authelia_b64(salt)}${authelia_b64(derived)}"


def run_op(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run an op CLI command."""
    return subprocess.run(  # NOQA: S603
        ["op", *args],
        input=input_text,
        text=True,
        check=True,
        capture_output=True,
    )


def item_exists(vault: str, item_title: str) -> str | None:
    """Check if a 1Password item exists, return its ID or None."""
    try:
        result = run_op(["item", "get", item_title, "--vault", vault, "--format", "json"])
        data = json.loads(result.stdout)
        return data.get("id")
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def upsert_field(
    vault: str,
    item_title: str,
    field_label: str,
    value: str,
    *,
    section: str | None = None,
    concealed: bool = True,
) -> None:
    """Create or update a field on a 1Password item.

    Uses 'op item edit' to set the field. If the item doesn't exist, creates it first.
    When *section* is provided, the field is placed under that section using
    the ``Section Name.field[type]=value`` assignment syntax.
    """
    item_id = item_exists(vault, item_title)
    field_type = "concealed" if concealed else "text"
    qualified = f"{section}.{field_label}" if section else field_label
    assignment = f"{qualified}[{field_type}]={value}"

    if item_id:
        run_op(["item", "edit", item_id, "--vault", vault, assignment])
        label_display = f"'{section}/{field_label}'" if section else f"'{field_label}'"
        print(f"  Updated field {label_display} on existing item '{item_title}'")
    else:
        run_op(
            [
                "item",
                "create",
                "--vault",
                vault,
                "--category",
                "login",
                "--title",
                item_title,
                assignment,
            ]
        )
        label_display = f"'{section}/{field_label}'" if section else f"'{field_label}'"
        print(f"  Created item '{item_title}' with field {label_display}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate OAuth client secret and store in 1Password.",
    )
    parser.add_argument("namespace", help="Kubernetes namespace (e.g., default)")
    parser.add_argument("app", help="Application name (e.g., actual-budget)")
    parser.add_argument(
        "--vault",
        default=os.environ.get("OP_VAULT", "homelab"),
        help="1Password vault name (default: homelab or $OP_VAULT)",
    )
    parser.add_argument(
        "--digest-field",
        help="Override the digest field name in the Authelia item (default: <APP_UPPER>_OAUTH_CLIENT_DIGEST)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and display the secret without writing to 1Password",
    )
    return parser.parse_args()


def main() -> int:
    """Run the OAuth client secret workflow."""
    args = parse_args()

    app_item = f"{args.namespace}.{args.app}"
    digest_field = args.digest_field or f"{args.app.upper().replace('-', '_')}_OAUTH_CLIENT_DIGEST"

    # Generate secret and digest
    password = generate_password()
    digest = make_digest(password)

    print(f"OAuth client secret generated for '{args.app}'")
    print()

    if args.dry_run:
        print("--- Dry Run (no 1Password writes) ---")
        print(f"Password:     {password}")
        print(f"PBKDF2 Digest: {digest}")
        print()
        print("Would perform:")
        print(f"  1. Set field 'client-secret' on item '{app_item}' in vault '{args.vault}'")
        print(f"  2. Set field '{AUTHELIA_SECTION}/{digest_field}' on item '{AUTHELIA_ITEM}' in vault '{args.vault}'")
        return 0

    # Validate op CLI is available and authenticated
    try:
        run_op(["vault", "get", args.vault, "--format", "json"])
    except FileNotFoundError:
        print("ERROR: 'op' CLI not found. Install 1Password CLI first.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError:
        print(
            f"ERROR: Cannot access vault '{args.vault}'. Run 'op signin' or check your 1Password CLI setup.",
            file=sys.stderr,
        )
        return 1

    print(f"Vault: {args.vault}")
    print()

    # 1. Store plaintext client secret on the app's item
    print(f"1. App item: {app_item}")
    upsert_field(args.vault, app_item, "client-secret", password)

    # 2. Store PBKDF2 digest on Authelia's item under "Client Secrets" section
    print(f"2. Authelia item: {AUTHELIA_ITEM} (section: {AUTHELIA_SECTION})")
    upsert_field(args.vault, AUTHELIA_ITEM, digest_field, digest, section=AUTHELIA_SECTION)

    print()
    print("Done! ExternalSecrets will pick up the new values on next reconciliation.")
    print(f"  App secret:     op://{args.vault}/{app_item}/client-secret")
    print(f"  Authelia digest: op://{args.vault}/{AUTHELIA_ITEM}/{AUTHELIA_SECTION}/{digest_field}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
