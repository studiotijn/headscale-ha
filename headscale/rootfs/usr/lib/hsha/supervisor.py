"""Minimal Supervisor API client (sync; callers in async code use asyncio.to_thread)."""

from __future__ import annotations

import ipaddress
import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

SUPERVISOR = os.environ.get("HSHA_SUPERVISOR_URL", "http://supervisor")

# Docker networks of the Supervisor and the tailnet itself are never "LAN".
_EXCLUDED = [
    ipaddress.IPv4Network("172.30.32.0/23"),
    ipaddress.IPv4Network("172.17.0.0/16"),
    ipaddress.IPv4Network("100.64.0.0/10"),
]


def _get(path: str) -> dict | None:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(f"{SUPERVISOR}{path}", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
    except Exception as exc:
        log.warning("Supervisor API %s failed: %s", path, exc)
        return None
    return body.get("data") if body.get("result") == "ok" else None


def ingress_port() -> int:
    if os.environ.get("HSHA_INGRESS_PORT"):
        return int(os.environ["HSHA_INGRESS_PORT"])
    info = _get("/addons/self/info") or {}
    return int(info.get("ingress_port") or 8099)


def lan_interfaces() -> list[ipaddress.IPv4Interface]:
    """IPv4 addresses (with prefix) of the host's primary/enabled interfaces."""
    override = os.environ.get("HSHA_LAN_CIDRS")
    if override:
        return [ipaddress.IPv4Interface(c.strip()) for c in override.split(",") if c.strip()]
    info = _get("/network/info") or {}
    result: list[ipaddress.IPv4Interface] = []
    ifaces = sorted(info.get("interfaces", []), key=lambda i: not i.get("primary"))
    for iface in ifaces:
        if not iface.get("enabled", True) or not iface.get("connected", True):
            continue
        for addr in (iface.get("ipv4") or {}).get("address", []) or []:
            try:
                itf = ipaddress.IPv4Interface(addr)
            except ValueError:
                continue
            if (
                itf.ip.is_private
                and not itf.ip.is_loopback
                and not itf.ip.is_link_local
                and not any(itf.ip in net for net in _EXCLUDED)
            ):
                result.append(itf)
    return result


def lan_ip() -> str | None:
    if os.environ.get("HSHA_LAN_IP"):
        return os.environ["HSHA_LAN_IP"]
    ifaces = lan_interfaces()
    return str(ifaces[0].ip) if ifaces else None


class SupervisorError(RuntimeError):
    pass


def available() -> bool:
    return bool(os.environ.get("SUPERVISOR_TOKEN"))


def _post(path: str, payload: dict | None = None, timeout: float = 30) -> dict:
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise SupervisorError("Supervisor API not available")
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        f"{SUPERVISOR}{path}",
        data=data,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode())
        except Exception:
            body = {}
        raise SupervisorError(body.get("message") or f"HTTP {exc.code}") from exc
    except Exception as exc:
        raise SupervisorError(str(exc)) from exc
    if body.get("result") != "ok":
        raise SupervisorError(body.get("message") or "Supervisor refused the request")
    return body.get("data") or {}


def self_options() -> dict | None:
    info = _get("/addons/self/info")
    return dict(info["options"]) if info and isinstance(info.get("options"), dict) else None


def validate_options(options: dict) -> None:
    result = _post("/addons/self/options/validate", options)
    if result and result.get("valid") is False:
        raise SupervisorError(result.get("message") or "Invalid options")


def save_options(options: dict) -> None:
    _post("/addons/self/options", {"options": options})


def restart_self() -> None:
    # The Supervisor stops this container while handling the call, so the
    # response may never arrive; that is expected.
    try:
        _post("/addons/self/restart", timeout=5)
    except SupervisorError as exc:
        log.info("Restart requested (%s)", exc)


def other_tailscale_apps() -> list[dict]:
    """Other Tailscale apps (e.g. the community Tailscale app) that compete for port 41641 / routes."""
    data = _get("/addons") or {}
    out = []
    for app in data.get("addons", []):
        slug = str(app.get("slug", ""))
        if slug.endswith("tailscale") or "tailscale" in str(app.get("name", "")).lower():
            out.append({"slug": slug, "name": app.get("name"), "state": app.get("state")})
    return out


def self_info() -> dict:
    return _get("/addons/self/info") or {}


def store_reload() -> None:
    _post("/store/reload", timeout=120)


def update_self(slug: str) -> None:
    # The Supervisor replaces this container while handling the call; a lost
    # connection afterwards is expected.
    try:
        _post(f"/store/addons/{slug}/update", {"backup": False}, timeout=600)
    except SupervisorError as exc:
        if "connection" not in str(exc).lower() and "remote end" not in str(exc).lower():
            raise


def rebuild_self(slug: str) -> None:
    try:
        _post(f"/addons/{slug}/rebuild", timeout=600)
    except SupervisorError as exc:
        if "connection" not in str(exc).lower() and "remote end" not in str(exc).lower():
            raise
