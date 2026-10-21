"""Certificates in /ssl, provided by a separate app (Let's Encrypt, Duck DNS, ...).

This app never requests certificates itself: the Let's Encrypt / Duck DNS apps
use the DNS challenge, which needs no open port and cannot be locked out by
failed HTTP/TLS validations.
"""

from __future__ import annotations

import ssl
import time
from datetime import UTC, datetime
from pathlib import Path

from . import paths

# Apps that can put a certificate in /ssl (slug suffixes).
PROVIDER_APPS = {"letsencrypt": "Let's Encrypt", "duckdns": "Duck DNS"}


def decode(path: Path) -> dict | None:
    try:
        return ssl._ssl._test_decode_cert(str(path))
    except Exception:
        return None


def _expiry(info: dict) -> int | None:
    try:
        return int(datetime.strptime(info["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC).timestamp())
    except Exception:
        return None


def names(info: dict) -> list[str]:
    out = [v.lower() for k, v in info.get("subjectAltName", ()) if k == "DNS"]
    if not out:
        for rdn in info.get("subject", ()):
            for k, v in rdn:
                if k == "commonName":
                    out.append(v.lower())
    return out


def covers(cert_names: list[str], host: str) -> bool:
    host = host.lower()
    for n in cert_names:
        n = n.lower()
        if n == host:
            return True
        if n.startswith("*.") and host.endswith(n[1:]) and host.count(".") == n.count("."):
            return True
    return False


def _key_for(cert: Path) -> str | None:
    candidates = [
        "privkey.pem",
        cert.name.replace("fullchain", "privkey"),
        cert.name.replace(".crt", ".key"),
        cert.name.replace("cert", "key"),
    ]
    for cand in candidates:
        if cand != cert.name and (cert.parent / cand).is_file():
            return cand
    return None


def inventory() -> list[dict]:
    """All certificates in /ssl with the hostnames they cover and their expiry."""
    out = []
    if not paths.SSL.is_dir():
        return out
    seen = set()
    for f in sorted(paths.SSL.glob("*.pem")) + sorted(paths.SSL.glob("*.crt")):
        if f.name in seen or "key" in f.name.lower():
            continue
        info = decode(f)
        if not info:
            continue
        seen.add(f.name)
        expires = _expiry(info)
        out.append(
            {
                "file": f.name,
                "names": names(info),
                "expires": expires,
                "days_left": None if expires is None else int((expires - time.time()) // 86400),
                "keyfile": _key_for(f),
                "mtime": int(f.stat().st_mtime),
            }
        )
    return out


def check(certfile: str, keyfile: str, host: str) -> str | None:
    """Return a problem description, or None when the certificate can be used for host."""
    cert, key = paths.SSL / certfile, paths.SSL / keyfile
    if not cert.is_file():
        return f"/ssl/{certfile} not found. Let the Let's Encrypt or Duck DNS app create it first."
    if not key.is_file():
        return f"/ssl/{keyfile} not found."
    info = decode(cert)
    if not info:
        return f"/ssl/{certfile} is not a readable certificate."
    cert_names = names(info)
    if not covers(cert_names, host):
        return (
            f"/ssl/{certfile} is valid for {', '.join(cert_names) or '?'}, not for {host}. "
            "Use one of those names in server_url, or add the name to the certificate app."
        )
    expires = _expiry(info)
    if expires and expires < time.time():
        return f"/ssl/{certfile} expired. Check that the certificate app renews it."
    return None
