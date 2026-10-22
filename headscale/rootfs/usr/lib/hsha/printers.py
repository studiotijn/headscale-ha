"""Printer discovery on the home LAN (mDNS/DNS-SD + optional port sweep).

mDNS does not cross a Tailscale tunnel, so remote devices cannot discover the
printers themselves. The app discovers them at home and gives every printer a
stable MagicDNS name (``<name>.<base_domain>``) that resolves to its LAN address
through the subnet router.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import re
import socket
import unicodedata

from zeroconf import IPVersion, ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

log = logging.getLogger("hsha.printers")

SERVICE_TYPES = {
    "_ipps._tcp.local.": "ipps",
    "_ipp._tcp.local.": "ipp",
    "_pdl-datastream._tcp.local.": "raw",
    "_printer._tcp.local.": "lpd",
}
# Preference when a printer announces several protocols.
PROTOCOL_RANK = {"ipp": 0, "ipps": 1, "raw": 2, "lpd": 3}
SWEEP_PORTS = {631: "ipp", 9100: "raw"}
MAX_SWEEP_HOSTS = 1024


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (text[:40].strip("-")) or "printer"


def _txt(info: AsyncServiceInfo) -> dict[str, str]:
    out = {}
    for k, v in (info.properties or {}).items():
        try:
            key = k.decode() if isinstance(k, bytes) else str(k)
            out[key.lower()] = v.decode("utf-8", "replace") if isinstance(v, bytes) else (v or "")
        except Exception:
            continue
    return out


async def mdns_scan(duration: float = 4.0) -> list[dict]:
    found: dict[tuple[str, str], dict] = {}
    pending: set[tuple[str, str]] = set()

    def on_change(zeroconf, service_type, name, state_change):
        if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
            pending.add((service_type, name))

    azc = AsyncZeroconf(ip_version=IPVersion.V4Only)
    browser = AsyncServiceBrowser(azc.zeroconf, list(SERVICE_TYPES), handlers=[on_change])
    try:
        await asyncio.sleep(duration)
        for service_type, name in list(pending):
            info = AsyncServiceInfo(service_type, name)
            if not await info.async_request(azc.zeroconf, 2000):
                continue
            addrs = info.parsed_addresses(IPVersion.V4Only)
            if not addrs:
                continue
            txt = _txt(info)
            protocol = SERVICE_TYPES[service_type]
            instance = name[: -len(service_type) - 1] if name.endswith(service_type) else name
            entry = {
                "ip": addrs[0],
                "port": info.port,
                "protocol": protocol,
                "name": instance,
                "model": txt.get("ty") or txt.get("product", "").strip("()") or None,
                "resource": txt.get("rp") or ("ipp/print" if protocol in ("ipp", "ipps") else ""),
                "admin_url": txt.get("adminurl"),
                "location": txt.get("note") or None,
                "source": "mdns",
                "txt": {k: v for k, v in txt.items() if len(k) <= 32 and len(v) <= 200},
            }
            found[(entry["ip"], protocol)] = entry
    finally:
        await browser.async_cancel()
        await azc.async_close()
    return list(found.values())


async def _probe(ip: str, port: int, sem: asyncio.Semaphore, timeout: float) -> bool:
    async with sem:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout)
        except (TimeoutError, OSError):
            return False
        writer.close()
        with contextlib.suppress(OSError):
            await writer.wait_closed()
        return True


async def sweep(networks: list[ipaddress.IPv4Network], timeout: float = 0.6) -> list[dict]:
    hosts: list[str] = []
    for net in networks:
        if net.num_addresses > MAX_SWEEP_HOSTS + 2:
            log.info("Skipping port sweep of %s (too large)", net)
            continue
        hosts += [str(h) for h in net.hosts()]
    sem = asyncio.Semaphore(256)
    checks = [(ip, port) for ip in hosts for port in SWEEP_PORTS]
    results = await asyncio.gather(*(_probe(ip, port, sem, timeout) for ip, port in checks))
    found = []
    for (ip, port), ok in zip(checks, results, strict=False):
        if ok:
            found.append(
                {
                    "ip": ip,
                    "port": port,
                    "protocol": SWEEP_PORTS[port],
                    "name": _reverse_name(ip) or f"Printer {ip}",
                    "model": None,
                    "resource": "ipp/print" if port == 631 else "",
                    "admin_url": None,
                    "location": None,
                    "source": "sweep",
                }
            )
    return found


def _reverse_name(ip: str) -> str | None:
    try:
        return socket.gethostbyaddr(ip)[0].split(".")[0]
    except (OSError, UnicodeError):
        return None


def merge(entries: list[dict]) -> list[dict]:
    """One entry per IP, preferring mDNS data and the best protocol."""
    by_ip: dict[str, dict] = {}
    for e in sorted(entries, key=lambda x: (x["source"] != "mdns", PROTOCOL_RANK.get(x["protocol"], 9))):
        current = by_ip.get(e["ip"])
        if current is None:
            by_ip[e["ip"]] = {**e, "protocols": [e["protocol"]]}
            continue
        if e["protocol"] not in current["protocols"]:
            current["protocols"].append(e["protocol"])
        for key in ("model", "admin_url", "location"):
            current[key] = current.get(key) or e.get(key)
    return sorted(by_ip.values(), key=lambda x: ipaddress.IPv4Address(x["ip"]))


async def discover(networks: list[ipaddress.IPv4Network], do_sweep: bool) -> list[dict]:
    tasks = [mdns_scan()]
    if do_sweep:
        tasks.append(sweep(networks))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    entries: list[dict] = []
    for res in results:
        if isinstance(res, Exception):
            log.warning("Printer discovery step failed: %s", res)
            continue
        entries += res
    return merge(entries)


# ---------------------------------------------------------------- iOS profile
def airprint_profile(printers: list[dict], base_domain: str) -> bytes | None:
    """A .mobileconfig with an AirPrint payload for every IPP printer (by IP address)."""
    import plistlib
    import uuid

    ns = uuid.uuid5(uuid.NAMESPACE_DNS, f"headscale-ha.{base_domain}")
    entries = [
        {
            "IPAddress": p["ip"],
            "ResourcePath": "/" + (p.get("resource") or "ipp/print").lstrip("/"),
            "Port": int(p.get("port") or 631),
            "ForceTLS": p["protocol"] == "ipps",
        }
        for p in printers
        if p.get("protocol") in ("ipp", "ipps")
    ]
    if not entries:
        return None
    ids = ",".join(sorted(f"{e['IPAddress']}:{e['Port']}{e['ResourcePath']}" for e in entries))
    payload = {
        "PayloadType": "com.apple.airprint",
        "PayloadVersion": 1,
        "PayloadIdentifier": "nl.headscale-ha.airprint.printers",
        "PayloadUUID": str(uuid.uuid5(ns, "airprint:" + ids)).upper(),
        "PayloadDisplayName": "AirPrint",
        "AirPrint": entries,
    }
    profile = {
        "PayloadType": "Configuration",
        "PayloadVersion": 1,
        "PayloadIdentifier": "nl.headscale-ha.printers",
        "PayloadUUID": str(uuid.uuid5(ns, "profile")).upper(),
        "PayloadDisplayName": "Printers via Tailscale",
        "PayloadDescription": "Home printers, reachable through the Headscale subnet router. "
        + ", ".join(p["name"] for p in printers if p.get("protocol") in ("ipp", "ipps")),
        "PayloadOrganization": "Headscale HA",
        "PayloadRemovalDisallowed": False,
        "PayloadContent": [payload],
    }
    return plistlib.dumps(profile)
