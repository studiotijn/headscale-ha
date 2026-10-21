"""Render Headscale and Headplane configuration from the app options.

Runs once per container start (s6 oneshot `init-hsha`). The app options are the
single source of truth for the server configuration; ACL policy, users, nodes
and DNS extra records live in Headscale's database / extra-records file and are
managed through Headplane or the ingress UI.
"""

from __future__ import annotations

import contextlib
import grp
import logging
import os
import secrets
import sys

import yaml

from . import derp, paths
from .options import Options, OptionsError, load
from .store import read_json, write_json, write_text_atomic

log = logging.getLogger("hsha.render")

# Loopback-only ports; chosen to avoid common host services (e.g. Cockpit/Prometheus on 9090).
METRICS_PORT = 19090
GRPC_PORT = 50443


def headscale_config(opts: Options, derp_cached: bool = False) -> dict:
    cfg: dict = {
        "server_url": opts.server_url_clean,
        "listen_addr": f"0.0.0.0:{opts.listen_port}",
        "metrics_listen_addr": f"127.0.0.1:{METRICS_PORT}",
        "grpc_listen_addr": f"127.0.0.1:{GRPC_PORT}",
        "grpc_allow_insecure": False,
        "noise": {"private_key_path": str(paths.HS_DIR / "noise_private.key")},
        "prefixes": {"v4": "100.64.0.0/10", "v6": "fd7a:115c:a1e0::/48", "allocation": "sequential"},
        "derp": {
            "server": {
                "enabled": bool(opts.derp_enabled),
                "region_id": 999,
                "region_code": "home",
                "region_name": "Home Assistant",
                "verify_clients": True,
                "stun_listen_addr": f"0.0.0.0:{opts.stun_port}",
                "private_key_path": str(paths.HS_DIR / "derp_server_private.key"),
                "automatically_add_embedded_derp_region": True,
            },
            # Never `urls`: Headscale refuses to start when that download fails.
            # derp.refresh() caches Tailscale's map locally instead.
            "urls": [],
            "paths": [str(derp.CACHE)] if (opts.tailscale_derp_fallback and derp_cached) else [],
            "auto_update_enabled": False,
        },
        "disable_check_updates": True,
        "node": {
            "expiry": f"{int(opts.node_expiry_days) * 24}h" if opts.node_expiry_days else "0",
            "ephemeral": {"inactivity_timeout": "30m"},
        },
        "database": {
            "type": "sqlite",
            "sqlite": {"path": str(paths.HS_DIR / "db.sqlite"), "write_ahead_log": True},
        },
        "log": {"level": opts.log_level, "format": "text"},
        "policy": {"mode": "database"},
        "dns": {
            "magic_dns": True,
            "base_domain": opts.base_domain,
            "override_local_dns": True,
            "nameservers": {"global": list(opts.nameservers or ["1.1.1.1"])},
            "search_domains": [],
            "extra_records_path": str(paths.HS_EXTRA_RECORDS),
        },
        "unix_socket": str(paths.HS_SOCKET),
        "unix_socket_permission": "0770",
        "logtail": {"enabled": False},
        "taildrop": {"enabled": True},
    }
    # Certificates come from a separate app (Let's Encrypt / Duck DNS) via /ssl;
    # Headscale's own ACME client is never used.
    if opts.tls_mode == "ha_certificate":
        cfg.update(
            {
                "tls_cert_path": str(paths.SSL / opts.certfile),
                "tls_key_path": str(paths.SSL / opts.keyfile),
            }
        )
    return cfg


def headplane_config(opts: Options, cookie_secret: str) -> dict:
    return {
        "server": {
            "host": "0.0.0.0",
            "port": int(opts.headplane_port),
            "cookie_secret": cookie_secret,
            # Served over plain HTTP on the LAN / tailnet.
            "cookie_secure": False,
            "data_path": str(paths.HP_DIR),
        },
        "headscale": {
            "url": opts.internal_url,
            "public_url": opts.server_url_clean,
            "config_path": str(paths.HS_CONFIG),
            "config_strict": False,
            "dns_records_path": str(paths.HS_EXTRA_RECORDS),
        },
        # No `integration` block: every integration is off by default, and Headplane
        # validates the fields of an integration as soon as its key is present.
    }


def _ensure_cookie_secret() -> str:
    if paths.HP_COOKIE_SECRET.exists():
        secret = paths.HP_COOKIE_SECRET.read_text().strip()
        if len(secret) == 32:
            return secret
    secret = secrets.token_hex(16)  # exactly 32 characters
    write_text_atomic(paths.HP_COOKIE_SECRET, secret + "\n", 0o600)
    return secret


def _ensure_hosts_entry(opts: Options) -> None:
    """Resolve our own public hostname to loopback inside the container.

    Local clients (Headplane, the subnet router, the UI) then reach Headscale
    directly with a valid certificate and without NAT loopback on the router.
    """
    if not opts.tls:
        return
    marker = "# hsha"
    line = f"127.0.0.1 {opts.server_host} {marker}"
    try:
        current = paths.ETC_HOSTS.read_text().splitlines()
    except FileNotFoundError:
        current = []
    kept = [ln for ln in current if not ln.rstrip().endswith(marker)]
    kept.append(line)
    # /etc/hosts is a bind mount: rewrite in place instead of replacing the inode.
    with open(paths.ETC_HOSTS, "w", encoding="utf-8") as fh:
        fh.write("\n".join(kept) + "\n")


def _chgrp(path, group: str, mode: int) -> None:
    try:
        gid = grp.getgrnam(group).gr_gid
    except KeyError:
        return
    try:
        os.chown(path, 0, gid)
        os.chmod(path, mode)
    except PermissionError:
        pass


def render(opts: Options) -> None:
    for d in (
        paths.HS_DIR,
        paths.HS_DIR / "cache",
        paths.DNS_DIR,
        paths.HP_DIR,
        paths.TS_DIR,
        paths.STATE.parent,
        paths.RUN,
    ):
        d.mkdir(parents=True, exist_ok=True)
    paths.HS_SOCKET.parent.mkdir(parents=True, exist_ok=True)

    derp_cached = derp.refresh() if opts.tailscale_derp_fallback else False
    write_text_atomic(
        paths.HS_CONFIG,
        "# Generated by the Headscale app on every start. Change the app options instead.\n"
        + yaml.safe_dump(headscale_config(opts, derp_cached), sort_keys=False),
        0o640,
    )
    if not paths.HS_EXTRA_RECORDS.exists():
        write_json(paths.HS_EXTRA_RECORDS, [], 0o660)

    if opts.headplane:
        secret = _ensure_cookie_secret()
        write_text_atomic(
            paths.HP_CONFIG,
            yaml.safe_dump(headplane_config(opts, secret), sort_keys=False),
            0o640,
        )
        # Headplane runs unprivileged: it may read the configs, edit DNS records
        # and write its own data, but cannot rewrite the generated server config.
        # It must be able to traverse /data to reach its folders.
        with contextlib.suppress(OSError):
            os.chmod(paths.DATA, os.stat(paths.DATA).st_mode | 0o711)
        _chgrp(paths.HP_DIR, "headplane", 0o770)
        _chgrp(paths.HP_CONFIG, "headplane", 0o640)
        _chgrp(paths.HS_DIR, "headplane", 0o750)
        _chgrp(paths.HS_CONFIG, "headplane", 0o640)
        _chgrp(paths.DNS_DIR, "headplane", 0o770)
        _chgrp(paths.HS_EXTRA_RECORDS, "headplane", 0o660)
        with contextlib.suppress(KeyError, PermissionError):
            os.chown(paths.HP_DIR, _uid("headplane"), grp.getgrnam("headplane").gr_gid)

    _ensure_hosts_entry(opts)

    runtime = read_json(paths.RUNTIME, {})
    runtime.update({"internal_url": opts.internal_url, "warnings": opts.warnings()})
    write_json(paths.RUNTIME, runtime, 0o644)


def _uid(user: str) -> int:
    import pwd

    return pwd.getpwnam(user).pw_uid


def set_setup_mode(reason: str | None, message: str = "", **extra) -> None:
    """Record why Headscale must not start yet; the wizard shows it and the app keeps running."""
    runtime = read_json(paths.RUNTIME, {})
    runtime["setup_mode"] = {"reason": reason, "message": message, **extra} if reason else None
    write_json(paths.RUNTIME, runtime, 0o644)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[hsha] %(message)s")
    paths.RUN.mkdir(parents=True, exist_ok=True)
    opts = load()
    if not opts.configured:
        log.warning("Not configured yet: open the Headscale panel in the sidebar and follow the setup wizard.")
        set_setup_mode("unconfigured")
        return 0
    try:
        opts.validate()
    except OptionsError as exc:
        log.error("Invalid configuration: %s", exc)
        log.error("Headscale is not started. Fix it in the setup wizard (Headscale panel in the sidebar).")
        set_setup_mode("invalid", str(exc))
        return 0
    for warning in opts.warnings():
        log.warning(warning)
    render(opts)
    set_setup_mode(None)
    log.info("Configuration written (server_url=%s, tls_mode=%s)", opts.server_url_clean, opts.tls_mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
