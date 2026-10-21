"""Minimal Supervisor API client (sync; callers in async code use asyncio.to_thread)."""

from __future__ import annotations

import ipaddress
import json
import logging
import os
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
