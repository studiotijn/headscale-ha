"""Start gate for the Headscale/Headplane services.

Called by the s6 run scripts before starting a service. Exit code 0 means
"start", anything else means "wait": the run script sleeps and s6 calls it
again, so the app (and its setup wizard) keeps running while the user fixes
the configuration or frees a port.
"""

from __future__ import annotations

import contextlib
import socket
import sys

from . import paths
from .options import load
from .store import read_json, write_json


def port_free(port: int, kind: int) -> bool:
    sock = socket.socket(socket.AF_INET, kind)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        with contextlib.suppress(OSError):
            sock.close()


def check_ports() -> dict:
    opts = load()
    return {
        "tcp": {"port": int(opts.listen_port), "free": port_free(int(opts.listen_port), socket.SOCK_STREAM)},
        "udp": {"port": int(opts.stun_port), "free": port_free(int(opts.stun_port), socket.SOCK_DGRAM)}
        if opts.derp_enabled
        else None,
    }


def main(argv: list[str]) -> int:
    service = argv[1] if len(argv) > 1 else "headscale"
    runtime = read_json(paths.RUNTIME, {})
    setup = runtime.get("setup_mode")
    if setup and setup.get("reason") in ("unconfigured", "invalid"):
        print(f"[hsha] {service}: waiting for the setup wizard ({setup['reason']})", flush=True)
        return 1
    if service == "headplane":
        # Headplane polls Headscale every 30 s. Without a certificate every poll makes
        # Headscale ask Let's Encrypt again, which quickly hits the hourly failure limit.
        opts = load()
        cert = paths.HS_DIR / "cache" / opts.server_host
        if opts.tls_mode == "letsencrypt" and not cert.exists():
            print("[hsha] headplane: waiting until Headscale has its Let's Encrypt certificate", flush=True)
            return 1
        return 0
    if service != "headscale":
        return 0
    ports = check_ports()
    runtime["ports"] = ports
    busy = [p for p in (ports["tcp"], ports["udp"]) if p and not p["free"]]
    if busy:
        runtime["setup_mode"] = {
            "reason": "port_in_use",
            "message": ", ".join(f"{p['port']}" for p in busy),
            "ports": [p["port"] for p in busy],
        }
        write_json(paths.RUNTIME, runtime, 0o644)
        print(
            f"[hsha] Port(s) {runtime['setup_mode']['message']} already in use on this host; "
            "Headscale waits. See the setup wizard for alternatives.",
            flush=True,
        )
        return 1
    if setup and setup.get("reason") == "port_in_use":
        runtime["setup_mode"] = None
    write_json(paths.RUNTIME, runtime, 0o644)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
