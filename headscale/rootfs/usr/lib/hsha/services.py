"""Home-network services the assistants can find and publish on the tailnet.

Supported kinds:

* ``unifi``  UniFi OS console running UniFi Protect (cameras stream through the console:
              RTSPS 7441 / RTSP 7447, Protect app on 443)
* ``prusa``  Prusa printer with PrusaLink (web UI on 80) and/or a Buddy3D camera
              (RTSP on 554, stream ``rtsp://<ip>/live``)
* ``plex``   Plex Media Server (32400), found with Plex's own GDM discovery and a port scan

Every added service gets a MagicDNS name (``<slug>.<base_domain>``); addresses outside
the advertised LAN get a /32 route on the subnet router. A service can be *shared*
with every user of the tailnet: the app then adds an ACL rule for exactly that
device and those ports.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import re
import socket
import time
import uuid

import aiohttp

from .printers import _probe, _reverse_name, slugify

log = logging.getLogger("hsha.services")

KINDS = {
    "unifi": {"ports": {443: "https", 7441: "rtsps", 7447: "rtsp"}, "required": [7441, 7447]},
    "prusa": {"ports": {80: "http", 554: "rtsp"}, "required": [80, 554]},
    "plex": {"ports": {32400: "http"}, "required": [32400]},
}
MAX_HOSTS = 1024
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=3)


# ---------------------------------------------------------------- helpers
def _hosts(networks: list[ipaddress.IPv4Network]) -> list[str]:
    out: list[str] = []
    for net in networks:
        if net.num_addresses <= MAX_HOSTS + 2:
            out += [str(h) for h in net.hosts()]
    return out


async def _open_ports(hosts: list[str], ports: list[int], timeout: float = 0.6) -> dict[str, set[int]]:
    sem = asyncio.Semaphore(256)
    checks = [(h, p) for h in hosts for p in ports]
    results = await asyncio.gather(*(_probe(h, p, sem, timeout) for h, p in checks))
    found: dict[str, set[int]] = {}
    for (h, p), ok in zip(checks, results, strict=True):
        if ok:
            found.setdefault(h, set()).add(p)
    return found


async def _http_get(session: aiohttp.ClientSession, url: str) -> tuple[int, dict, str]:
    try:
        async with session.get(url, ssl=False, allow_redirects=True) as resp:
            body = (await resp.content.read(65536)).decode("utf-8", "replace")
            return resp.status, dict(resp.headers), body
    except Exception:
        return 0, {}, ""


def _title(html: str) -> str | None:
    m = re.search(r"<title[^>]*>([^<]{1,120})</title>", html, re.I)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------- UniFi Protect
async def scan_unifi(networks: list[ipaddress.IPv4Network]) -> list[dict]:
    open_ = await _open_ports(_hosts(networks), [7441, 7447])
    out = []
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as s:
        for ip, ports in sorted(open_.items(), key=lambda x: ipaddress.IPv4Address(x[0])):
            status, _headers, body = await _http_get(s, f"https://{ip}/")
            title = _title(body) or ""
            name = title if "unifi" in title.lower() else (_reverse_name(ip) or "UniFi Protect")
            out.append(
                {
                    "kind": "unifi",
                    "ip": ip,
                    "name": name,
                    "ports": sorted(ports | ({443} if status else set())),
                    "detail": "UniFi OS" if "unifi" in (title + body[:2000]).lower() else "RTSP 7441/7447",
                }
            )
    return out


# ---------------------------------------------------------------- Prusa
def _prusa_fingerprint(headers: dict, body: str) -> str | None:
    text = (headers.get("Server", "") + " " + body[:4000]).lower()
    if "prusalink" in text or "prusa link" in text:
        return "PrusaLink"
    if "buddy3d" in text:
        return "Buddy3D camera"
    if "prusa" in text:
        return "Prusa"
    return None


async def scan_prusa(networks: list[ipaddress.IPv4Network]) -> list[dict]:
    open_ = await _open_ports(_hosts(networks), [80, 554])
    out = []
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as s:
        sem = asyncio.Semaphore(32)

        async def check(ip: str, ports: set[int]) -> dict | None:
            async with sem:
                fp = None
                if 80 in ports:
                    _, headers, body = await _http_get(s, f"http://{ip}/")
                    fp = _prusa_fingerprint(headers, body)
                if not fp and 554 not in ports:
                    return None
                name = _reverse_name(ip)
                kind_detail = fp or "RTSP camera"
                return {
                    "kind": "prusa",
                    "ip": ip,
                    "ports": sorted(ports),
                    "name": name or (f"Prusa {ip}" if fp else f"Camera {ip}"),
                    "detail": kind_detail,
                    "camera": 554 in ports,
                    "prusalink": bool(fp and fp != "Buddy3D camera" and 80 in ports),
                    "confidence": "high" if fp else "low",
                }

        results = await asyncio.gather(*(check(ip, p) for ip, p in open_.items()))
    out = [r for r in results if r]
    # Known Prusa devices first, generic RTSP cameras after.
    return sorted(out, key=lambda r: (r["confidence"] != "high", ipaddress.IPv4Address(r["ip"])))


# ---------------------------------------------------------------- Plex
class _Gdm(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.found: dict[str, dict] = {}

    def datagram_received(self, data, addr):
        text = data.decode("utf-8", "replace")
        if not text.startswith("HTTP/1.0 200"):
            return
        fields = {}
        for line in text.splitlines()[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                fields[k.strip().lower()] = v.strip()
        self.found[addr[0]] = fields


async def gdm_discover(duration: float = 2.5) -> dict[str, dict]:
    """Plex 'G'Day Mate' discovery: Plex servers answer an M-SEARCH on UDP 32414."""
    loop = asyncio.get_running_loop()
    proto = _Gdm()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("0.0.0.0", 0))
    transport, _ = await loop.create_datagram_endpoint(lambda: proto, sock=sock)
    try:
        msg = b"M-SEARCH * HTTP/1.1\r\n\r\n"
        for target in ("255.255.255.255", "239.0.0.250"):
            with contextlib.suppress(OSError):
                transport.sendto(msg, (target, 32414))
        await asyncio.sleep(duration)
    finally:
        transport.close()
    return proto.found


async def plex_identity(session: aiohttp.ClientSession, ip: str, port: int = 32400) -> dict | None:
    status, _, body = await _http_get(session, f"http://{ip}:{port}/identity")
    if status != 200 or "MediaContainer" not in body:
        return None
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', body))
    return {"machine_id": attrs.get("machineIdentifier"), "version": attrs.get("version")}


async def scan_plex(networks: list[ipaddress.IPv4Network]) -> list[dict]:
    gdm, open_ = await asyncio.gather(gdm_discover(), _open_ports(_hosts(networks), [32400]))
    candidates: dict[str, dict] = {}
    for ip, fields in gdm.items():
        candidates[ip] = {"name": fields.get("name"), "port": int(fields.get("port") or 32400)}
    for ip in open_:
        candidates.setdefault(ip, {"name": None, "port": 32400})
    out = []
    async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as s:
        for ip, c in sorted(candidates.items(), key=lambda x: ipaddress.IPv4Address(x[0])):
            ident = await plex_identity(s, ip, c["port"])
            if not ident:
                continue
            out.append(
                {
                    "kind": "plex",
                    "ip": ip,
                    "ports": [c["port"]],
                    "name": c["name"] or _reverse_name(ip) or "Plex",
                    "detail": f"Plex Media Server {ident.get('version') or ''}".strip(),
                    "machine_id": ident.get("machine_id"),
                }
            )
    return out


SCANNERS = {"unifi": scan_unifi, "prusa": scan_prusa, "plex": scan_plex}


async def scan(kind: str, networks: list[ipaddress.IPv4Network]) -> list[dict]:
    if kind not in SCANNERS:
        raise ValueError(f"Unknown kind {kind}")
    return await SCANNERS[kind](networks)


# ---------------------------------------------------------------- tests
async def test(service: dict) -> dict:
    """Check every port of an added service from the app (the same path the subnet router uses)."""
    sem = asyncio.Semaphore(8)
    ports = service.get("ports") or KINDS[service["kind"]]["required"]
    results = await asyncio.gather(*(_probe(service["ip"], int(p), sem, 2.0) for p in ports))
    out = {"ports": {str(p): ok for p, ok in zip(ports, results, strict=True)}, "time": int(time.time())}
    if service["kind"] == "plex" and any(results):
        async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as s:
            out["plex"] = await plex_identity(s, service["ip"], int(ports[0]))
    out["ok"] = any(results)
    return out


def make_service(data: dict, existing_slugs: set[str]) -> dict:
    kind = data.get("kind")
    if kind not in KINDS:
        raise ValueError("Unknown kind")
    ip = str(ipaddress.IPv4Address(str(data["ip"]).strip()))
    name = (str(data.get("name") or "").strip() or f"{kind} {ip}")[:64]
    default_slug = {"unifi": "unifi", "prusa": "prusa", "plex": "plex"}[kind]
    slug = slugify(str(data.get("slug") or default_slug))
    base, n = slug, 2
    while slug in existing_slugs:
        slug, n = f"{base}-{n}", n + 1
    ports = sorted({int(p) for p in (data.get("ports") or KINDS[kind]["required"]) if 0 < int(p) < 65536})
    return {
        "id": uuid.uuid4().hex[:12],
        "kind": kind,
        "name": name,
        "slug": slug,
        "ip": ip,
        "ports": ports,
        "detail": str(data.get("detail") or "")[:80],
        "camera": bool(data.get("camera")),
        "prusalink": bool(data.get("prusalink")),
        "shared": False,
        "added": int(time.time()),
    }
