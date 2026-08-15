"""Mint Cloudflare Realtime TURN credentials into Galene's ice-servers.json.

Galene hands its ICE configuration verbatim to every browser that joins a
group, so any long-lived TURN credential placed in ice-servers.json is
effectively published to every participant. Galene can generate ephemeral
credentials itself via coturn's `use-auth-secret` scheme
(``credentialType: hmac-sha1``), but Cloudflare does not implement that
scheme - its only credential path is a server-to-server REST call. This script
closes that gap: it mints short-lived credentials from the API, writes them
where Galene expects them, and leaves replaced credentials to expire naturally.

Galene re-reads ice-servers.json within roughly five minutes without a
restart, so rotation needs no pod churn.

Runs as an init container (ONESHOT=1) to seed the file before Galene starts,
and again as a sidecar to refresh it on an interval.

Uses only the standard library so the runtime image needs no package installs.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import sys
import time
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format='{"level":"%(levelname)s","msg":"%(message)s"}',
    stream=sys.stdout,
)
log = logging.getLogger("turn-rotate")

API_ROOT = "https://rtc.live.cloudflare.com/v1/turn/keys"
TIMEOUT = 30


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, falling back to a default."""
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        log.warning("invalid %s, using default %s", name, default)
        return default


def _request(url: str, token: str, payload: dict | None = None) -> object:
    """POST to the Cloudflare Realtime API and return the decoded response."""
    data = json.dumps(payload).encode() if payload is not None else b"{}"

    req = urllib.request.Request(  # noqa: S310
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310
        return json.load(resp)


def _validate_ice_servers(value: object) -> list[dict[str, object]]:
    """Validate Cloudflare's ICE servers before Galene can publish them."""
    servers = value if isinstance(value, list) else [value]
    if not servers:
        raise ValueError("Cloudflare response iceServers must contain at least one server")

    validated: list[dict[str, object]] = []
    for server in servers:
        # TRY004 wants TypeError for an isinstance guard, which fits a wrong
        # argument type. This validates an untrusted API payload, where the
        # value is malformed rather than misused, and every other check in this
        # function raises ValueError; one category keeps callers simple.
        if not isinstance(server, dict):
            raise ValueError("Cloudflare response iceServers entries must be objects")  # noqa: TRY004

        urls = server.get("urls")
        if (
            not isinstance(urls, list)
            or not urls
            or not all(isinstance(url, str) and url and url.startswith(("turn:", "turns:")) for url in urls)
        ):
            raise ValueError("Cloudflare response iceServers urls must be a non-empty list of TURN URLs")

        for field in ("username", "credential"):
            if not isinstance(server.get(field), str) or not server[field]:
                raise ValueError(f"Cloudflare response iceServers {field} must be a non-empty string")

        validated.append(server)

    return validated


def mint(key_id: str, token: str, ttl: int) -> list[dict[str, object]]:
    """Mint a credential and return it as Galene's ice-servers.json structure.

    Cloudflare returns a single object under ``iceServers``; Galene expects a
    list. Both documented shapes are accepted after strict validation.
    """
    body = _request(
        f"{API_ROOT}/{key_id}/credentials/generate-ice-servers",
        token,
        {"ttl": ttl},
    )
    if not isinstance(body, dict) or "iceServers" not in body:
        raise ValueError("Cloudflare response must contain iceServers")
    return _validate_ice_servers(body["iceServers"])


def write_atomic(path: pathlib.Path, servers: list[dict[str, object]]) -> None:
    """Write ice-servers.json atomically.

    Galene may read this file at any moment; a torn write would hand a client
    an unparsable ICE configuration and fail the call.
    """
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(servers, indent=2))
    tmp.replace(path)


def main() -> None:
    """Seed ice-servers.json, then refresh it on an interval unless ONESHOT."""
    key_id = os.environ["CF_TURN_KEY_ID"]
    token = os.environ["CF_TURN_API_TOKEN"]
    path = pathlib.Path(os.environ.get("ICE_SERVERS_PATH", "/data/ice-servers.json"))
    ttl = _env_int("CREDENTIAL_TTL", 86400)
    # Refresh at half the TTL so a credential is always replaced well before it
    # expires, leaving room for a failed attempt or two.
    interval = _env_int("REFRESH_INTERVAL", ttl // 2)
    oneshot = os.environ.get("ONESHOT", "").lower() in {"1", "true", "yes"}

    while True:
        servers = mint(key_id, token, ttl)
        write_atomic(path, servers)
        log.info("wrote %s with %d ice server(s)", path, len(servers))

        if oneshot:
            return
        time.sleep(interval)


if __name__ == "__main__":
    main()
