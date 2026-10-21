"""External port-forward test.

Headscale (and tailscaled) are paused for a moment and the app listens on the
forwarded ports itself. External probes then connect to the public IP. Because
the app sees the incoming connections, a passed test proves that the router
forwards each port to *this* app, not just that "something" answers (for example
Home Assistant on 8123). Headscale is not involved, so no Let's Encrypt attempt is
spent.

Probes: check-host.net nodes (TCP + UDP) and, optionally, the user's own phone on
mobile data opening a test link.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import json
import logging
import os
import secrets
import shutil
import time
import urllib.parse
import urllib.request

from . import netcheck

log = logging.getLogger("hsha.probe")

CHECK_HOST = os.environ.get("HSHA_CHECK_HOST", "https://check-host.net")
S6_SVC = shutil.which("s6-svc") or "/command/s6-svc"
SERVICE_DIR = os.environ.get("HSHA_SERVICE_DIR", "/run/service")
TS_PORT = 41641


def is_external(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip.split("%")[0]).is_global
    except ValueError:
        return False


class Hits:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, proto: str, port: int, peer: str, token_ok: bool = False) -> None:
        self.items.append(
            {
                "proto": proto,
                "port": port,
                "ip": peer,
                "external": is_external(peer),
                "token": token_ok,
                "t": time.time(),
            }
        )

    def seen(self, proto: str, port: int, external: bool = True) -> list[dict]:
        return [h for h in self.items if h["proto"] == proto and h["port"] == port and h["external"] == external]


class _Udp(asyncio.DatagramProtocol):
    def __init__(self, hits: Hits, port: int):
        self.hits, self.port = hits, port

    def datagram_received(self, data, addr):
        self.hits.add("udp", self.port, addr[0])


def _check_host(kind: str, host: str, nodes: int = 3) -> str | None:
    url = f"{CHECK_HOST}/check-{kind}?" + urllib.parse.urlencode({"host": host, "max_nodes": nodes})
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "headscale-ha"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("request_id")
    except Exception as exc:
        log.warning("check-host %s %s failed: %s", kind, host, exc)
        return None


def _check_result(request_id: str) -> dict:
    req = urllib.request.Request(
        f"{CHECK_HOST}/check-result/{request_id}", headers={"Accept": "application/json", "User-Agent": "headscale-ha"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()) or {}
    except Exception:
        return {}


def _tcp_connected(result: dict) -> bool | None:
    """True if any check-host node completed a TCP connect, False if all failed, None if unknown."""
    seen = False
    for value in result.values():
        if not value:
            continue
        for entry in value:
            if isinstance(entry, dict):
                seen = True
                if "time" in entry:
                    return True
    return False if seen else None


class PortTest:
    """One test run; the web layer keeps the latest instance."""

    def __init__(
        self,
        *,
        listen_port: int,
        external_port: int,
        stun_port: int | None,
        test_ts_port: bool,
        mode: str,
        duration: float,
    ):
        self.listen_port = listen_port
        self.external_port = external_port
        self.stun_port = stun_port
        self.test_ts_port = test_ts_port
        self.mode = mode  # "auto" | "phone"
        self.duration = duration
        self.token = secrets.token_urlsafe(8)
        self.hits = Hits()
        self.public_ip: str | None = None
        self.state = "starting"
        self.error: str | None = None
        self.started = time.time()
        self.ends_at: float | None = None
        self.results: dict | None = None
        self.checkhost: dict = {}
        self._paused: list[str] = []

    # ------------------------------------------------------------ s6
    async def _svc(self, flag: str, name: str) -> None:
        path = f"{SERVICE_DIR}/{name}"
        if not os.path.isdir(path):
            return
        proc = await asyncio.create_subprocess_exec(
            S6_SVC,
            "-wD" if flag == "-d" else "-wU",
            "-T",
            "15000",
            flag,
            path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

    async def _pause(self) -> None:
        for name in ("headscale", "tailscaled"):
            if os.path.isdir(f"{SERVICE_DIR}/{name}"):
                await self._svc("-d", name)
                self._paused.append(name)

    async def _resume(self) -> None:
        for name in reversed(self._paused):
            proc = await asyncio.create_subprocess_exec(
                S6_SVC,
                "-u",
                f"{SERVICE_DIR}/{name}",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        self._paused.clear()

    # ------------------------------------------------------------ listeners
    async def _tcp_handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = (writer.get_extra_info("peername") or ("?",))[0]
        token_ok = False
        with contextlib.suppress(Exception):
            line = await asyncio.wait_for(reader.readline(), 5)
            token_ok = self.token in line.decode("latin-1", "replace")
            if line:
                body = (
                    "<!doctype html><meta name=viewport content='width=device-width'>"
                    "<body style='font:20px system-ui;padding:24px'>"
                    "<h1 style='color:#2e7d32'>&#10003; Headscale HA</h1>"
                    f"<p>Port {self.external_port} works / werkt.</p></body>"
                ).encode()
                writer.write(
                    b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n"
                    + f"Content-Length: {len(body)}\r\n\r\n".encode()
                    + body
                )
                await writer.drain()
        self.hits.add("tcp", self.listen_port, peer, token_ok)
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()

    async def _bind_tcp(self) -> asyncio.base_events.Server:
        for _ in range(20):
            try:
                return await asyncio.start_server(self._tcp_handler, "0.0.0.0", self.listen_port, reuse_address=True)
            except OSError:
                await asyncio.sleep(0.5)
        raise OSError(f"port {self.listen_port}/tcp stays in use by another program")

    async def _bind_udp(self, port: int):
        loop = asyncio.get_running_loop()
        for _ in range(20):
            try:
                transport, _ = await loop.create_datagram_endpoint(
                    lambda: _Udp(self.hits, port), local_addr=("0.0.0.0", port), reuse_port=False
                )
                return transport
            except OSError:
                await asyncio.sleep(0.5)
        raise OSError(f"port {port}/udp stays in use by another program")

    # ------------------------------------------------------------ run
    @property
    def phone_url(self) -> str | None:
        if not self.public_ip:
            return None
        port = "" if self.external_port == 80 else f":{self.external_port}"
        return f"http://{self.public_ip}{port}/hsha-test/{self.token}"

    async def run(self) -> None:
        servers: list = []
        jobs: dict = {}
        try:
            self.public_ip = await asyncio.to_thread(netcheck.public_ipv4)
            if not self.public_ip:
                raise RuntimeError("no_public_ip")
            self.state = "pausing"
            await self._pause()
            self.state = "listening"
            servers.append(await self._bind_tcp())
            udp_ports = [p for p in (self.stun_port, TS_PORT if self.test_ts_port else None) if p]
            for port in udp_ports:
                servers.append(await self._bind_udp(port))

            # Hairpin (NAT loopback) check from inside: informative only.
            await asyncio.to_thread(netcheck.tcp_listening, self.external_port, self.public_ip, 3)

            self.ends_at = time.time() + self.duration
            if self.mode == "auto":
                jobs = {"tcp": await asyncio.to_thread(_check_host, "tcp", f"{self.public_ip}:{self.external_port}")}
                for port in udp_ports:
                    jobs[f"udp{port}"] = await asyncio.to_thread(_check_host, "udp", f"{self.public_ip}:{port}")
                self.checkhost = {"requested": {k: bool(v) for k, v in jobs.items()}}
            while time.time() < self.ends_at:
                await asyncio.sleep(1)
                if (
                    self.mode == "auto"
                    and self.hits.seen("tcp", self.listen_port)
                    and all(self.hits.seen("udp", p) for p in udp_ports)
                ):
                    break
                if self.mode == "phone" and any(h["token"] for h in self.hits.seen("tcp", self.listen_port)):
                    break
            if self.mode == "auto" and jobs.get("tcp"):
                self.checkhost["tcp_connected"] = _tcp_connected(await asyncio.to_thread(_check_result, jobs["tcp"]))
            self.results = self._summarise(udp_ports)
            self.state = "done"
        except Exception as exc:
            self.error = str(exc)
            self.state = "error"
            log.warning("Port test failed: %s", exc)
        finally:
            for srv in servers:
                with contextlib.suppress(Exception):
                    srv.close()
            await self._resume()

    def _summarise(self, udp_ports: list[int]) -> dict:
        tcp_ext = self.hits.seen("tcp", self.listen_port)
        tcp_int = self.hits.seen("tcp", self.listen_port, external=False)
        if tcp_ext:
            tcp = "ok"
        elif self.checkhost.get("tcp_connected"):
            tcp = "elsewhere"  # something answered on the public port, but not this app
        else:
            tcp = "closed"
        out = {
            "tcp": {
                "port": self.external_port,
                "internal": self.listen_port,
                "status": tcp,
                "sources": sorted({h["ip"] for h in tcp_ext}),
            },
            "udp": [],
            "hairpin": bool(tcp_int),
            "public_ip": self.public_ip,
            "mode": self.mode,
        }
        for port in udp_ports:
            seen = self.hits.seen("udp", port)
            out["udp"].append(
                {
                    "port": port,
                    "status": "ok" if seen else "not_seen",
                    "optional": port == TS_PORT,
                    "sources": sorted({h["ip"] for h in seen}),
                }
            )
        return out

    def view(self) -> dict:
        left = max(0, round(self.ends_at - time.time())) if self.ends_at and self.state == "listening" else None
        return {
            "state": self.state,
            "mode": self.mode,
            "error": self.error,
            "seconds_left": left,
            "phone_url": self.phone_url if self.mode == "phone" else None,
            "results": self.results,
            "started": self.started,
        }


def external_https(url: str, wait: float = 25) -> dict:
    """Let check-host.net nodes fetch url; ok when any node gets HTTP 200 with a valid certificate."""
    nodes_info: dict = {}
    req_url = f"{CHECK_HOST}/check-http?" + urllib.parse.urlencode({"host": url, "max_nodes": 3})
    req = urllib.request.Request(req_url, headers={"Accept": "application/json", "User-Agent": "headscale-ha"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            started = json.loads(resp.read().decode())
    except Exception as exc:
        return {"ok": None, "error": f"check-host.net unreachable: {exc}", "nodes": []}
    request_id = started.get("request_id")
    nodes_info = started.get("nodes") or {}
    deadline = time.time() + wait
    result: dict = {}
    while time.time() < deadline:
        time.sleep(2)
        result = _check_result(request_id) if request_id else {}
        if result and all(v is not None for v in result.values()):
            break
    nodes = []
    for node, value in (result or {}).items():
        loc = nodes_info.get(node) or []
        entry = value[0] if isinstance(value, list) and value else None
        if not isinstance(entry, list):
            nodes.append({"node": node, "location": ", ".join(loc[1:3]) if loc else node, "ok": None})
            continue
        success, _t, message, code = (entry + [None] * 4)[:4]
        nodes.append(
            {
                "node": node,
                "location": ", ".join(loc[1:3]) if loc else node,
                "ok": bool(success) and str(code) == "200",
                "code": code,
                "message": message,
            }
        )
    oks = [n["ok"] for n in nodes if n["ok"] is not None]
    return {"ok": (any(oks) if oks else None), "nodes": nodes, "report": started.get("permanent_link")}
