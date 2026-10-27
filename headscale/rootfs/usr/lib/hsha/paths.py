"""Filesystem layout. Everything persistent lives under /data (included in HA backups)."""

from __future__ import annotations

import os
from pathlib import Path

DATA = Path(os.environ.get("HSHA_DATA", "/data"))
RUN = Path(os.environ.get("HSHA_RUN", "/run/hsha"))

OPTIONS = DATA / "options.json"

HS_DIR = DATA / "headscale"
HS_CONFIG = HS_DIR / "config.yaml"
# Separate directory: Headplane may write here, but not next to the server config.
DNS_DIR = DATA / "dns"
HS_EXTRA_RECORDS = DNS_DIR / "extra-records.json"
HS_SOCKET = Path(os.environ.get("HSHA_HS_SOCKET", "/run/headscale/headscale.sock"))

HP_DIR = DATA / "headplane"
HP_CONFIG = HP_DIR / "config.yaml"
HP_COOKIE_SECRET = HP_DIR / "cookie_secret"

TS_DIR = DATA / "tailscale"
TS_STATE = TS_DIR / "tailscaled.state"
TS_SOCKET = Path(os.environ.get("HSHA_TS_SOCKET", "/run/tailscale/tailscaled.sock"))

STATE = DATA / "hsha" / "state.json"
RUNTIME = RUN / "runtime.json"
# Browser sign-ins waiting for approval, noted from the Headscale log (regwatch.py).
PENDING = RUN / "pending.jsonl"
HS_STARTED = RUN / "headscale-started"

SSL = Path(os.environ.get("HSHA_SSL", "/ssl"))
ETC_HOSTS = Path(os.environ.get("HSHA_ETC_HOSTS", "/etc/hosts"))
WWW = Path(os.environ.get("HSHA_WWW", "/usr/share/hsha/www"))

# Multi-tenant mode (option multi_tenant)
TENANCY = DATA / "hsha" / "tenancy.json"
AUDIT = DATA / "hsha" / "audit.jsonl"  # .jsonl: *.log files are excluded from backups
POLICY_HISTORY = DATA / "hsha" / "policy-history"
