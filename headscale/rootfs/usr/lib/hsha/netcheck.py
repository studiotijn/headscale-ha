"""Network diagnostics used by the setup wizard (all blocking; call via asyncio.to_thread)."""

from __future__ import annotations

import contextlib
import ipaddress
import os
import random
import socket
import ssl
import struct
import time
import urllib.request
from datetime import UTC, datetime

PUBLIC_IP_URLS = [
    "https://api.ipify.org",
    "https://ipv4.icanhazip.com",
    "https://v4.ident.me",
]
RESOLVERS = ["1.1.1.1", "9.9.9.9", "8.8.8.8"]


def public_ipv4(timeout: float = 5) -> str | None:
    override = os.environ.get("HSHA_PUBLIC_IP")
    if override:
        return override
    for url in PUBLIC_IP_URLS:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                text = resp.read().decode().strip()
            return str(ipaddress.IPv4Address(text))
        except Exception:
            continue
    return None


def _encode_name(name: str) -> bytes:
    out = b""
    for label in name.strip(".").split("."):
        raw = label.encode("idna")
        out += bytes([len(raw)]) + raw
    return out + b"\x00"


def _skip_name(data: bytes, pos: int) -> int:
    while True:
        length = data[pos]
        if length == 0:
            return pos + 1
        if length & 0xC0 == 0xC0:
            return pos + 2
        pos += 1 + length


def resolve_a(name: str, timeout: float = 3) -> list[str]:
    """Resolve A records through public resolvers, bypassing /etc/hosts and the local network."""
    override = os.environ.get("HSHA_DNS_OVERRIDE")
    if override is not None:
        return [x for x in override.split(",") if x]
    query_id = random.randint(0, 0xFFFF)
    packet = struct.pack(">HHHHHH", query_id, 0x0100, 1, 0, 0, 0) + _encode_name(name) + struct.pack(">HH", 1, 1)
    for resolver in RESOLVERS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(packet, (resolver, 53))
            data, _ = sock.recvfrom(2048)
        except OSError:
            continue
        finally:
            sock.close()
        rid, flags, qd, an, _, _ = struct.unpack(">HHHHHH", data[:12])
        if rid != query_id:
            continue
        if flags & 0x000F == 3:  # NXDOMAIN
            return []
        pos = 12
        for _ in range(qd):
            pos = _skip_name(data, pos) + 4
        out = []
        for _ in range(an):
            pos = _skip_name(data, pos)
            rtype, _rclass, _ttl, rdlen = struct.unpack(">HHIH", data[pos : pos + 10])
            pos += 10
            if rtype == 1 and rdlen == 4:
                out.append(socket.inet_ntoa(data[pos : pos + 4]))
            pos += rdlen
        return out
    raise OSError("no DNS resolver reachable")


def tls_check(host: str, port: int, timeout: float = 20) -> dict:
    """Connect to Headscale over loopback with SNI and verify the certificate like a client would."""
    ctx = ssl.create_default_context()
    started = time.monotonic()
    try:
        with (
            socket.create_connection(("127.0.0.1", port), timeout=timeout) as raw,
            ctx.wrap_socket(raw, server_hostname=host) as tls,
        ):
            cert = tls.getpeercert() or {}
    except ssl.SSLCertVerificationError as exc:
        return {"ok": False, "error": "untrusted", "detail": exc.verify_message or str(exc)}
    except ssl.SSLError as exc:
        # Headscale answers "internal error" while it has no certificate (ACME failed or pending).
        code = "no_cert" if "INTERNAL_ERROR" in str(exc).upper() else "tls"
        return {"ok": False, "error": code, "detail": str(exc)}
    except TimeoutError:
        return {"ok": False, "error": "timeout", "detail": f"no answer within {timeout:.0f}s"}
    except OSError as exc:
        return {"ok": False, "error": "connect", "detail": str(exc)}
    issuer = dict(x[0] for x in cert.get("issuer", ()))
    not_after = cert.get("notAfter")
    expires = None
    with contextlib.suppress(Exception):
        expires = int(datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC).timestamp())
    org = issuer.get("organizationName") or issuer.get("commonName") or ""
    return {
        "ok": True,
        "issuer": org,
        "lets_encrypt": "let's encrypt" in org.lower(),
        "expires": expires,
        "seconds": round(time.monotonic() - started, 1),
    }


def tcp_listening(port: int, host: str = "127.0.0.1", timeout: float = 2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
