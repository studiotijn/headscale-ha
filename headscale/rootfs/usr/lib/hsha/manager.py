"""Long-running coordinator: bootstrap Headscale, keep the subnet router and printer DNS in sync."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import time
import uuid

from . import hs, netcheck, paths, supervisor, tailscale
from .options import Options
from .policy import ROUTER_TAG, initial_policy
from .store import load_state, read_json, save_state, write_json

log = logging.getLogger("hsha.manager")

EXIT_ROUTES = ["0.0.0.0/0", "::/0"]


class Manager:
    def __init__(self, opts: Options):
        self.opts = opts
        self.state = load_state()
        self.ready = False
        self.error: str | None = None
        self.router: dict = {"enabled": bool(opts.subnet_router), "state": "starting"}
        self._applied_routes: tuple | None = None
        self._router_parked = False
        self.tls: dict | None = None
        self._cert_mtime: float | None = None
        self._tls_at = 0.0
        self._lock = asyncio.Lock()
        self._wake = asyncio.Event()
        self.lan = supervisor.lan_interfaces()

    # ---------------------------------------------------------------- routes
    def lan_networks(self) -> list[ipaddress.IPv4Network]:
        if self.opts.advertise_routes:
            return [
                ipaddress.ip_network(r, strict=False)
                for r in self.opts.advertise_routes
                if ipaddress.ip_network(r, strict=False).version == 4
            ]
        return sorted({itf.network for itf in self.lan}, key=str)

    def lan_routes(self) -> list[str]:
        if self.opts.advertise_routes:
            return sorted({str(ipaddress.ip_network(r, strict=False)) for r in self.opts.advertise_routes})
        return [str(n) for n in self.lan_networks()]

    def printer_routes(self) -> list[str]:
        nets = [ipaddress.ip_network(r, strict=False) for r in self.lan_routes()]
        out = []
        for p in self.state["printers"] + self.state.get("services", []):
            if p.get("via_node"):
                continue  # reached through another subnet router (e.g. a PC at work)
            ip = ipaddress.ip_address(p["ip"])
            if not any(ip in n for n in nets):
                out.append(f"{ip}/32")
        return sorted(set(out))

    def desired_routes(self) -> list[str]:
        return sorted(set(self.lan_routes()) | set(self.printer_routes()))

    # ------------------------------------------------------------------- TLS
    async def tls_probe(self, force: bool = False) -> dict:
        """Check the served certificate like a client does (loopback, with SNI).

        The certificate comes from /ssl, so a check never contacts Let's Encrypt.
        """
        if not self.opts.tls:
            return {"ok": True, "skipped": True}
        now = time.monotonic()
        max_age = 300 if (self.tls and self.tls.get("ok")) else 30
        if not force and self.tls is not None and now - self._tls_at < max_age:
            return self.tls
        self.tls = await asyncio.to_thread(netcheck.tls_check, self.opts.server_host, int(self.opts.listen_port), 20)
        self._tls_at = time.monotonic()
        if self.tls.get("ok"):
            self.poke()
        return self.tls

    async def _record_router_ip(self, me: dict) -> None:
        """Remember the router's tailnet IPv4; DNS features point devices at it."""
        ipv4 = next((ip for ip in me.get("TailscaleIPs") or [] if "." in ip), None)
        if not ipv4 or ipv4 == self.state.get("router_ipv4"):
            return
        self.state["router_ipv4"] = ipv4
        save_state(self.state)
        if self.opts.airprint_dns or self.opts.dns_via_home:
            from .render import render

            log.info("Router tailnet IP is %s: updating the DNS settings pushed to devices", ipv4)
            await asyncio.to_thread(render, self.opts)
            await self._restart_headscale()

    async def _restart_headscale(self) -> None:
        proc = await asyncio.create_subprocess_exec(
            "s6-svc",
            "-r",
            "/run/service/headscale",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()

    async def watch_certificate(self) -> None:
        """Restart Headscale when the certificate app has renewed the certificate in /ssl.

        Headscale reads the certificate only at start; without this a renewed
        certificate would not be used and the old one would eventually expire.
        """
        if self.opts.tls_mode != "ha_certificate":
            return
        cert = paths.SSL / self.opts.certfile
        try:
            mtime = cert.stat().st_mtime
        except OSError:
            return
        if self._cert_mtime is None:
            self._cert_mtime = mtime
            return
        if mtime != self._cert_mtime:
            self._cert_mtime = mtime
            log.info("Certificate /ssl/%s changed: restarting Headscale to load it", self.opts.certfile)
            await self._restart_headscale()
            self.tls = None

    # ------------------------------------------------------------- bootstrap
    async def bootstrap(self) -> None:
        await hs.wait_healthy(timeout=300)
        user = await hs.ensure_user(self.opts.admin_user)
        self.state["admin_user_id"] = user["id"]
        if await hs.get_policy() is None:
            log.info("No ACL policy yet: installing the initial policy")
            await hs.set_policy(initial_policy(self.opts.admin_user, self.lan_routes(), self.opts.exit_node))
        self.write_dns_records()
        save_state(self.state)
        self.ready = True
        log.info("Headscale ready (admin user '%s')", self.opts.admin_user)

    # ---------------------------------------------------------------- router
    async def reconcile_router(self) -> None:
        if not self.opts.subnet_router:
            self.router = {"enabled": False, "state": "disabled"}
            return
        if not tailscale.available():
            self.router.update(state="waiting for tailscaled")
            return
        routes = self.desired_routes()
        exit_node = bool(self.opts.exit_node)
        status = await tailscale.status()
        backend = status.get("BackendState")
        if backend in ("NeedsLogin", "NoState", "Stopped", "NeedsMachineAuth") or not status.get("Self"):
            # Logging in without a trusted certificate only produces endless retries.
            tls = await self.tls_probe()
            if not tls.get("ok"):
                if not self._router_parked:
                    with contextlib.suppress(tailscale.TailscaleError):
                        await tailscale.run("down")
                    self._router_parked = True
                    log.info("Subnet router waits until Headscale serves a valid certificate")
                self.router = {"enabled": True, "state": "waiting for certificate", "routes": routes}
                return
            self._router_parked = False
            log.info("Registering the subnet router with Headscale")
            key = await hs.create_preauthkey(tags=[ROUTER_TAG], expiration="10m")
            await tailscale.up(self.opts.internal_url, key, routes, exit_node)
            self._applied_routes = (tuple(routes), exit_node)
            status = await tailscale.status()
        elif self._applied_routes != (tuple(routes), exit_node):
            await tailscale.set_routes(routes, exit_node)
            self._applied_routes = (tuple(routes), exit_node)

        approved = await self._approve_router_routes(status, routes + (EXIT_ROUTES if exit_node else []))
        me = status.get("Self") or {}
        await self._record_router_ip(me)
        self.router = {
            "enabled": True,
            "state": status.get("BackendState", "unknown"),
            "hostname": me.get("HostName"),
            "ips": me.get("TailscaleIPs") or [],
            "routes": routes,
            "approved": approved,
            "exit_node": exit_node,
        }

    async def _approve_router_routes(self, status: dict, wanted: list[str]) -> list[str]:
        me = status.get("Self") or {}
        my_ips = set(me.get("TailscaleIPs") or [])
        for node in await hs.nodes():
            if my_ips and not my_ips.intersection(node.get("ip_addresses") or []):
                continue
            approved = sorted(node.get("approved_routes") or [])
            if approved != sorted(wanted):
                log.info("Approving router routes: %s", ", ".join(wanted) or "(none)")
                await hs.approve_routes(int(node["id"]), wanted)
                approved = sorted(wanted)
            return approved
        return []

    # ------------------------------------------------------------------- DNS
    def write_dns_records(self) -> None:
        """Merge printer A-records into Headscale's extra-records file (Headplane may add others)."""
        records = read_json(paths.HS_EXTRA_RECORDS, [])
        managed_before = set(self.state.get("dns_managed", []))
        kept = [r for r in records if r.get("name") not in managed_before]
        ours = [
            {"name": f"{p['slug']}.{self.opts.base_domain}", "type": "A", "value": p["ip"]}
            for p in self.state["printers"] + self.state.get("services", [])
        ]
        names = {r["name"] for r in ours}
        kept = [r for r in kept if r.get("name") not in names]
        new = kept + ours
        if new != records:
            write_json(paths.HS_EXTRA_RECORDS, new, 0o660)
        self.state["dns_managed"] = sorted(names)

    # -------------------------------------------------------------- printers
    def printer_fqdn(self, printer: dict) -> str:
        return f"{printer['slug']}.{self.opts.base_domain}"

    def check_via_node(self, ip: str, via_node) -> int | None:
        """A printer elsewhere (work) is reached through the node that advertises it."""
        if via_node in (None, "", 0, "0", "home"):
            return None
        addr = ipaddress.ip_address(ip)
        if any(addr in ipaddress.ip_network(r, strict=False) for r in self.lan_routes()):
            raise ValueError(
                f"{ip} is part of your home network ({', '.join(self.lan_routes())}); "
                "a printer elsewhere needs an address outside it"
            )
        return int(via_node)

    async def reconcile_remote_routes(self) -> None:
        """Approve <ip>/32 on the nodes that printers are reached through; withdraw what we approved before."""
        wanted: dict[str, set[str]] = {}
        for p in self.state["printers"]:
            if p.get("via_node"):
                wanted.setdefault(str(p["via_node"]), set()).add(f"{p['ip']}/32")
        managed: dict[str, list[str]] = self.state.get("remote_routes", {})
        if not wanted and not managed:
            return
        nodes = {str(n["id"]): n for n in await hs.nodes()}
        new_managed: dict[str, list[str]] = {}
        for node_id in set(wanted) | set(managed):
            node = nodes.get(node_id)
            if node is None:
                continue
            approved = set(node.get("approved_routes") or [])
            target = (approved - set(managed.get(node_id, []))) | wanted.get(node_id, set())
            if target != approved:
                log.info("Routes for %s: %s", node.get("given_name") or node_id, ", ".join(sorted(target)) or "(none)")
                await hs.approve_routes(int(node_id), sorted(target))
            if wanted.get(node_id):
                new_managed[node_id] = sorted(wanted[node_id])
        if new_managed != managed:
            self.state["remote_routes"] = new_managed
            save_state(self.state)

    async def add_printer(self, data: dict) -> dict:
        ip = str(ipaddress.IPv4Address(str(data["ip"]).strip()))
        via_node = self.check_via_node(ip, data.get("via_node"))
        protocol = data.get("protocol") if data.get("protocol") in ("ipp", "ipps", "raw", "lpd") else "ipp"
        default_port = {"ipp": 631, "ipps": 631, "raw": 9100, "lpd": 515}[protocol]
        name = (str(data.get("name") or "").strip() or f"Printer {ip}")[:64]
        default_resource = "ipp/print" if protocol.startswith("ipp") else ""
        async with self._lock:
            from .printers import slugify

            slug = slugify(str(data.get("slug") or name))
            existing = {p["slug"] for p in self.state["printers"] if p["ip"] != ip}
            base, n = slug, 2
            while slug in existing:
                slug, n = f"{base}-{n}", n + 1
            self.state["printers"] = [p for p in self.state["printers"] if p["ip"] != ip]
            printer = {
                "id": uuid.uuid4().hex[:12],
                "name": name,
                "slug": slug,
                "ip": ip,
                "port": int(data.get("port") or default_port),
                "protocol": protocol,
                "resource": str(data.get("resource") or default_resource).lstrip("/"),
                "model": data.get("model"),
                "via_node": via_node,
                # mDNS TXT record of the printer, replayed for AirPrint via DNS-SD.
                "txt": {str(k)[:32]: str(v)[:200] for k, v in (data.get("txt") or {}).items()}
                if isinstance(data.get("txt"), dict)
                else {},
                "added": int(time.time()),
            }
            self.state["printers"].append(printer)
            self.write_dns_records()
            save_state(self.state)
        self.poke()
        return printer

    async def remove_printer(self, printer_id: str) -> bool:
        async with self._lock:
            before = len(self.state["printers"])
            self.state["printers"] = [p for p in self.state["printers"] if p["id"] != printer_id]
            changed = len(self.state["printers"]) != before
            if changed:
                self.write_dns_records()
                save_state(self.state)
        self.poke()
        return changed

    # -------------------------------------------------------------- services
    def all_slugs(self, exclude_id: str | None = None) -> set[str]:
        items = self.state["printers"] + self.state.get("services", [])
        return {i["slug"] for i in items if i.get("id") != exclude_id}

    async def add_service(self, data: dict) -> dict:
        from .services import make_service

        async with self._lock:
            services = self.state.setdefault("services", [])
            svc = make_service(data, self.all_slugs())
            services[:] = [s for s in services if not (s["ip"] == svc["ip"] and s["kind"] == svc["kind"])]
            services.append(svc)
            self.write_dns_records()
            save_state(self.state)
        self.poke()
        return svc

    async def remove_service(self, service_id: str) -> bool:
        async with self._lock:
            services = self.state.setdefault("services", [])
            svc = next((s for s in services if s["id"] == service_id), None)
            if not svc:
                return False
            services.remove(svc)
            if svc.get("shared"):
                await self._write_shares()
            self.write_dns_records()
            save_state(self.state)
        self.poke()
        return True

    async def set_shared(self, service_id: str, shared: bool) -> dict:
        async with self._lock:
            svc = next((s for s in self.state.get("services", []) if s["id"] == service_id), None)
            if not svc:
                raise KeyError("unknown service")
            svc["shared"] = bool(shared)
            await self._write_shares()
            save_state(self.state)
        return svc

    async def _write_shares(self) -> None:
        import json as _json

        from .policy import apply_shares, dump, strip_hujson

        current = await hs.get_policy() or "{}"
        policy = _json.loads(strip_hujson(current))
        shared = [s for s in self.state.get("services", []) if s.get("shared")]
        await hs.set_policy(dump(apply_shares(policy, shared)))

    # ------------------------------------------------------------------ loop
    def poke(self) -> None:
        self._wake.set()

    async def run(self) -> None:
        while not self.ready:
            setup = read_json(paths.RUNTIME, {}).get("setup_mode")
            if setup:
                # Headscale is not started yet; the setup wizard explains why.
                self.error = None
                self.router = {"enabled": bool(self.opts.subnet_router), "state": "waiting for setup"}
                await asyncio.sleep(5)
                continue
            try:
                await self.bootstrap()
                self.error = None
            except Exception as exc:
                self.error = str(exc)
                log.error("Bootstrap failed: %s (retrying in 15s)", exc)
                await asyncio.sleep(15)
        while True:
            try:
                await self.watch_certificate()
                await self.reconcile_router()
                await self.reconcile_remote_routes()
                self.error = None
            except Exception as exc:
                self.error = str(exc)
                log.warning("Router reconcile failed: %s", exc)
            self._wake.clear()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._wake.wait(), timeout=30)
