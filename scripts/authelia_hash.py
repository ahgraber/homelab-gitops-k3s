#!/usr/bin/env -S uv run --script

"""Generate a random password and its PBKDF2-SHA512 hash suitable for Authelia."""

import argparse
import base64
import hashlib
import os
import secrets
import string

# === Settings (mimic Authelia defaults) ===
length = 72  # random password length
iterations = 310000  # PBKDF2 iterations (Authelia default)
digest = "sha512"  # PBKDF2 variant
salt_len = 16  # salt length in bytes

# RFC 3986 safe charset: ALPHA / DIGIT / "-" / "." / "_" / "~"
charset = string.ascii_letters + string.digits + "-._~"

# === Generate random password and salt ===
password = "".join(secrets.choice(charset) for _ in range(length))
salt = os.urandom(salt_len)


def derive(password: str, salt: bytes) -> bytes:
    """Return the PBKDF2 digest for the given password and salt."""
    return hashlib.pbkdf2_hmac(digest, password.encode(), salt, iterations)


def authelia_b64(data: bytes) -> str:
    """Encode bytes using Authelia's PBKDF2 base64 variant."""
    return base64.b64encode(data, altchars=b"./").decode().rstrip("=")


def main() -> None:
    """Entry point for CLI usage."""
    parser = argparse.ArgumentParser(description="Generate Authelia PBKDF2 digests")
    parser.add_argument(
        "password",
        nargs="?",
        help="Use this password instead of generating a random one",
    )
    args = parser.parse_args()

    if args.password is None:
        pwd = password
        salt_bytes = salt
        digest_bytes = derive(pwd, salt_bytes)
        print("Password:", pwd)
        print(
            "PBKDF2 Digest:",
            f"$pbkdf2-{digest}${iterations}${authelia_b64(salt_bytes)}${authelia_b64(digest_bytes)}",
        )
    else:
        salt_bytes = os.urandom(salt_len)
        digest_bytes = derive(args.password, salt_bytes)
        print("Password:", args.password)
        print(
            "PBKDF2 Digest:",
            f"$pbkdf2-{digest}${iterations}${authelia_b64(salt_bytes)}${authelia_b64(digest_bytes)}",
        )


if __name__ == "__main__":
    main()
