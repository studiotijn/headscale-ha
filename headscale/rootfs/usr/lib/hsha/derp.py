"""Tailscale DERP map cache.

Headscale 0.29 exits at startup when it cannot download a DERP map listed in
`derp.urls` (for example when the internet connection is down while Home
Assistant boots). We therefore download Tailscale's map ourselves, convert it
to Headscale's YAML format and point `derp.paths` at the cached copy, so a
missing internet connection never prevents Headscale from starting.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request

import yaml

from . import paths
from .store import write_text_atomic

log = logging.getLogger("hsha.derp")

URL = os.environ.get("HSHA_DERPMAP_URL", "https://controlplane.tailscale.com/derpmap/default")
CACHE = paths.HS_DIR / "derp-tailscale.yaml"


def _lower_keys(value):
    """tailcfg.DERPMap JSON -> YAML that Headscale decodes (lower-case field names)."""
    if isinstance(value, dict):
        return {(k.lower() if isinstance(k, str) else k): _lower_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_lower_keys(v) for v in value]
    return value


def convert(derpmap: dict) -> dict:
    regions = {}
    for key, region in (derpmap.get("Regions") or {}).items():
        regions[int(key)] = _lower_keys(region)
    if not regions:
        raise ValueError("DERP map contains no regions")
    return {"regions": regions}


def refresh(timeout: float = 10) -> bool:
    """Download and cache the map. Returns True when a usable cache exists."""
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "headscale-ha"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        write_text_atomic(CACHE, yaml.safe_dump(convert(data), sort_keys=True), 0o644)
        log.info("Tailscale DERP map refreshed (%d regions)", len(data.get("Regions") or {}))
    except Exception as exc:
        if CACHE.exists():
            log.warning("Could not refresh Tailscale DERP map (%s); using cached copy", exc)
        else:
            log.warning(
                "Could not download Tailscale DERP map (%s); only the embedded DERP relay is "
                "available until the next restart with internet access",
                exc,
            )
    return CACHE.exists()
