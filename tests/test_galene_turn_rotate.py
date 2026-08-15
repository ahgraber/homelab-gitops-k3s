"""Regression tests for Galene TURN credential rotation."""

from __future__ import annotations

from collections.abc import Iterator
import importlib.util
import pathlib
from types import ModuleType

import pytest

SCRIPT_PATH = pathlib.Path(__file__).parents[1] / "kubernetes/apps/default/galene/app/config/turn_rotate.py"


def load_turn_rotate() -> ModuleType:
    """Load the deployed script as a module."""
    spec = importlib.util.spec_from_file_location("galene_turn_rotate", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ice_server(username: str = "credential-1") -> dict[str, object]:
    """Return a complete Cloudflare ICE server response object."""
    return {
        "urls": ["turn:turn.cloudflare.com:3478?transport=udp"],
        "username": username,
        "credential": "secret",
    }


@pytest.mark.parametrize("response", [[], {}, {"iceServers": "invalid"}])
def test_mint_rejects_invalid_provider_response(monkeypatch: pytest.MonkeyPatch, response: object) -> None:
    """The provider response must contain an ICE server object."""
    turn_rotate = load_turn_rotate()
    monkeypatch.setattr(turn_rotate, "_request", lambda *_args: response)

    with pytest.raises(ValueError, match="Cloudflare response"):
        turn_rotate.mint("key-id", "api-token", 3600)


@pytest.mark.parametrize(
    "ice_servers",
    [
        [],
        {},
        {"urls": [], "username": "credential-1", "credential": "secret"},
        {
            "urls": ["turn:turn.cloudflare.com:3478?transport=udp"],
            "username": "credential-1",
        },
    ],
)
def test_mint_rejects_unusable_ice_servers(monkeypatch: pytest.MonkeyPatch, ice_servers: object) -> None:
    """An unusable ICE server must fail before it can be written."""
    turn_rotate = load_turn_rotate()
    monkeypatch.setattr(
        turn_rotate,
        "_request",
        lambda *_args: {"iceServers": ice_servers},
    )

    with pytest.raises(ValueError, match="iceServers"):
        turn_rotate.mint("key-id", "api-token", 3600)


def test_mint_accepts_complete_ice_server(monkeypatch: pytest.MonkeyPatch) -> None:
    """A complete provider response is converted to Galene's list format."""
    turn_rotate = load_turn_rotate()
    server = ice_server()
    monkeypatch.setattr(
        turn_rotate,
        "_request",
        lambda *_args: {"iceServers": server},
    )

    assert turn_rotate.mint("key-id", "api-token", 3600) == [server]


def test_main_leaves_rotated_credentials_to_expire(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Rotation must not revoke credentials retained by connected clients."""
    turn_rotate = load_turn_rotate()
    responses: Iterator[list[dict[str, object]]] = iter([[ice_server("credential-1")], [ice_server("credential-2")]])
    requested_urls: list[str] = []
    sleeps = 0

    def request(url: str, _token: str, _payload: object = None) -> dict[str, object]:
        requested_urls.append(url)
        if url.endswith("/credentials/generate-ice-servers"):
            return {"iceServers": next(responses)}
        return {}

    def stop_after_second_rotation(_interval: int) -> None:
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            raise RuntimeError("test complete")

    monkeypatch.setenv("CF_TURN_KEY_ID", "key-id")
    monkeypatch.setenv("CF_TURN_API_TOKEN", "api-token")
    monkeypatch.setenv("ICE_SERVERS_PATH", str(tmp_path / "ice-servers.json"))
    monkeypatch.setattr(turn_rotate, "_request", request)
    monkeypatch.setattr(turn_rotate.time, "sleep", stop_after_second_rotation)

    with pytest.raises(RuntimeError, match="test complete"):
        turn_rotate.main()

    assert not any(url.endswith("/revoke") for url in requested_urls)
