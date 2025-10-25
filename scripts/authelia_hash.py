#!/usr/bin/env -S uv run --script

"""Generate a random password and its PBKDF2-SHA512 hash suitable for Authelia."""

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

# === Derive PBKDF2-SHA512 hash ===
dk = hashlib.pbkdf2_hmac(digest, password.encode(), salt, iterations)


def authelia_b64(data: bytes) -> str:
    """Encode bytes using Authelia's PBKDF2 base64 variant."""
    return base64.b64encode(data, altchars=b"./").decode().rstrip("=")


# === Output ===
print("Password:", password)
# print("Salt (base64)", authelia_b64(salt))
print("PBKDF2 Digest", f"$pbkdf2-{digest}${iterations}${authelia_b64(salt)}${authelia_b64(dk)}")
