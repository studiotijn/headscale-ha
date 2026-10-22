"""Ingress web UI + JSON API.

Only reachable through Home Assistant ingress: requests must come from the
Supervisor's ingress proxy (172.30.32.2). Home Assistant authenticates the user.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import re
import sys
import time

from aiohttp import web

from . import __version__, hs, ipp, paths, printers, services, supervisor
from .manager import Manager
from .options import load
from .store import read_json
from .wizard import Wizard

log = logging.getLogger("hsha.web")

INGRESS_PROXY = {"172.30.32.2"}
LOCAL = {"127.0.0.1", "::1"}


@web.middleware
async def ingress_only(request: web.Request, handler):
    peer = request.remote or ""
    if peer not in INGRESS_PROXY and not (peer in LOCAL and os.environ.get("HSHA_ALLOW_LOCAL")):
        raise web.HTTPForbidden(text="Only available through Home Assistant ingress")
    return await handler(request)


@web.middleware
async def json_errors(request: web.Request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except (hs.HeadscaleError, supervisor.SupervisorError, ValueError, KeyError) as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception as exc:
        log.exception("Unhandled error on %s", request.path)
        return web.json_response({"error": str(exc)}, status=500)


def _ts(value) -> int | None:
    if isinstance(value, dict):
        return int(value.get("seconds") or 0) or None
    return None


def _node(n: dict) -> dict:
    return {
        "id": int(n.get("id")),
        "name": n.get("given_name") or n.get("name"),
        "hostname": n.get("name"),
        "user": (n.get("user") or {}).get("name"),
        "tags": n.get("tags") or n.get("valid_tags") or [],
        "ips": n.get("ip_addresses") or [],
        "online": bool(n.get("online")),
        "last_seen": _ts(n.get("last_seen")),
        "expiry": _ts(n.get("expiry")),
        "available_routes": n.get("available_routes") or [],
        "approved_routes": n.get("approved_routes") or [],
    }


class App:
    def __init__(self):
        self.opts = load()
        self.manager = Manager(self.opts)
        self.wizard = Wizard(self)
        self.started = int(time.time())

    # ---------------------------------------------------------------- status
    async def status(self, _request: web.Request) -> web.Response:
        o = self.opts
        runtime = read_json(paths.RUNTIME, {})
        try:
            version = await hs.version()
            healthy = await hs.healthy()
        except Exception:
            version, healthy = None, False
        lan_ip = supervisor.lan_ip()
        return web.json_response(
            {
                "app_version": __version__,
                "headscale_version": version,
                "healthy": healthy,
                "ready": self.manager.ready,
                "error": self.manager.error,
                "warnings": runtime.get("warnings", []),
                "server_url": o.server_url_clean,
                "tls_mode": o.tls_mode,
                "derp": {
                    "embedded": o.derp_enabled,
                    "stun_port": o.stun_port,
                    "tailscale_fallback": o.tailscale_derp_fallback,
                },
                "listen_port": o.listen_port,
                "base_domain": o.base_domain,
                "admin_user": o.admin_user,
                "multi_tenant": self.manager.mt.status() if self.manager.mt else None,
                "router": self.manager.router,
                "lan_routes": self.manager.lan_routes(),
                "headplane": {
                    "enabled": o.headplane,
                    "url": f"http://{lan_ip}:{o.headplane_port}/admin/" if (o.headplane and lan_ip) else None,
                },
                "lan_ip": lan_ip,
            }
        )

    # ----------------------------------------------------------------- nodes
    async def nodes(self, _request: web.Request) -> web.Response:
        return web.json_response([_node(n) for n in await hs.nodes()])

    async def node_action(self, request: web.Request) -> web.Response:
        node_id = int(request.match_info["id"])
        action = request.match_info["action"]
        if action == "expire":
            await hs.expire_node(node_id)
        elif action == "delete":
            await hs.delete_node(node_id)
        elif action == "approve":
            node = next((n for n in await hs.nodes() if int(n["id"]) == node_id), None)
            if node is None:
                raise web.HTTPNotFound()
            routes = node.get("available_routes") or []
            if self.manager.mt is not None:
                # Only routes the model allows (an Edgebox may offer only its own location).
                allowed = set(self.manager.mt.allowed_routes_for(node))
                refused = sorted(set(routes) - allowed - {"0.0.0.0/0", "::/0"})
                routes = sorted((set(routes) & allowed) | set(node.get("approved_routes") or []) & allowed)
                if refused:
                    log.warning("Not approving routes outside the model on node %s: %s", node_id, refused)
            await hs.approve_routes(node_id, routes)
        else:
            raise web.HTTPNotFound()
        self.manager.poke()
        return web.json_response({"ok": True})

    # ------------------------------------------------------------------ keys
    async def authkey(self, request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else {}
        hours = max(1, min(int(body.get("hours", 1)), 24 * 7))
        reusable = bool(body.get("reusable", False))
        if self.manager.mt is not None:
            name = self.manager.mt.user_for(body.get("domain"), body.get("user"))
            user_id = (await hs.ensure_user(name))["id"]
        else:
            user_id = self.manager.state.get("admin_user_id")
            if user_id is None:
                user_id = (await hs.ensure_user(self.opts.admin_user))["id"]
        key = await hs.create_preauthkey(user_id=int(user_id), reusable=reusable, expiration=f"{hours}h")
        return web.json_response(
            {
                "key": key,
                "hours": hours,
                "reusable": reusable,
                "login_server": self.opts.server_url_clean,
                "command": f"tailscale up --login-server {self.opts.server_url_clean} --auth-key {key}",
            }
        )

    async def register(self, request: web.Request) -> web.Response:
        """Approve a device that signed in through the browser flow (mobile apps).

        Accepts the auth ID, the registration URL or the full CLI command the
        Headscale registration page shows.
        """
        body = await request.json()
        text = str(body.get("auth_id", "")).strip()
        match = re.search(r"--auth-id[ =]([A-Za-z0-9_-]+)", text) or re.search(r"/register/([A-Za-z0-9_-]+)", text)
        auth_id = match.group(1) if match else text
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,128}", auth_id):
            raise ValueError("Not a valid auth ID")
        user = self.opts.admin_user
        if self.manager.mt is not None:
            user = self.manager.mt.user_for(body.get("domain"), body.get("user"))
            await hs.ensure_user(user)
        await hs.register(auth_id, user)
        self.manager.poke()
        return web.json_response({"ok": True})

    async def apikey(self, _request: web.Request) -> web.Response:
        key = await hs.create_apikey("90d")
        self.wizard.mark("apikey_created")
        return web.json_response({"key": key, "days": 90})

    # ---------------------------------------------------------------- wizard
    async def wizard_get(self, request: web.Request) -> web.Response:
        refresh = request.query.get("refresh") == "1"
        force_tls = request.query.get("tls") == "1"
        return web.json_response(await self.wizard.evaluate(refresh=refresh, force_tls=force_tls))

    async def wizard_answer(self, request: web.Request) -> web.Response:
        body = await request.json()
        self.wizard.answer(str(body.get("key")), body.get("value"))
        return web.json_response(await self.wizard.evaluate())

    async def wizard_skip(self, request: web.Request) -> web.Response:
        body = await request.json()
        self.wizard.skip(str(body.get("step")), bool(body.get("skipped", True)))
        return web.json_response(await self.wizard.evaluate())

    async def porttest_start(self, request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else {}
        return web.json_response(self.wizard.start_port_test(str(body.get("mode", "auto"))))

    async def external_test(self, _request: web.Request) -> web.Response:
        return web.json_response(await self.wizard.external_test())

    async def dns_test(self, _request: web.Request) -> web.Response:
        return web.json_response(await self.wizard.dns_test())

    async def porttest_get(self, _request: web.Request) -> web.Response:
        return web.json_response(self.wizard.port_test_view())

    async def wizard_options(self, request: web.Request) -> web.Response:
        body = await request.json()
        try:
            result = await self.wizard.apply_options(body.get("changes") or {})
        except supervisor.SupervisorError as exc:
            raise ValueError(str(exc)) from exc
        return web.json_response(result)

    # ---------------------------------------------------------------- update
    async def update_get(self, _request: web.Request) -> web.Response:
        info = await asyncio.to_thread(supervisor.self_info)
        return web.json_response(
            {
                "version": info.get("version") or __version__,
                "version_latest": info.get("version_latest"),
                "update_available": bool(info.get("update_available")),
                "auto_update": info.get("auto_update"),
                "available": supervisor.available(),
            }
        )

    async def update_post(self, request: web.Request) -> web.Response:
        """check: reload the app store (git pull of the repository); update/rebuild: replace this app."""
        action = (await request.json()).get("action")
        info = await asyncio.to_thread(supervisor.self_info)
        slug = info.get("slug")
        if not slug:
            raise ValueError("Supervisor API not available")
        if action == "check":
            await asyncio.to_thread(supervisor.store_reload)
            return await self.update_get(request)
        if action in ("update", "rebuild"):
            if action == "rebuild":
                # Pull the newest code from the repository first; rebuild uses that checkout.
                await asyncio.to_thread(supervisor.store_reload)
            func = supervisor.update_self if action == "update" else supervisor.rebuild_self
            # Run after the response: the Supervisor stops this container while it works.
            asyncio.get_running_loop().call_later(0.5, lambda: asyncio.ensure_future(asyncio.to_thread(func, slug)))
            return web.json_response({"started": action})
        raise ValueError(f"Unknown action {action}")

    async def qr(self, request: web.Request) -> web.Response:
        import io

        import segno

        text = request.query.get("text", "")[:512]
        if not text:
            raise web.HTTPBadRequest()
        buf = io.BytesIO()
        segno.make(text, error="m").save(buf, kind="svg", scale=5, border=2, dark="#000", light="#fff")
        return web.Response(
            body=buf.getvalue(), content_type="image/svg+xml", headers={"Cache-Control": "max-age=3600"}
        )

    # -------------------------------------------------------------- printers
    @staticmethod
    def _via_view(p: dict, nodes: dict[int, dict]) -> dict | None:
        if not p.get("via_node"):
            return None
        n = nodes.get(int(p["via_node"]))
        route = f"{p['ip']}/32"
        addr = ipaddress.ip_address(p["ip"])

        def covers(routes):
            return any(addr in ipaddress.ip_network(r, strict=False) for r in routes or [] if "/" in r)

        if n is None:
            return {"id": p["via_node"], "missing": True, "route": route}
        return {
            "id": int(n["id"]),
            "name": n.get("given_name") or n.get("name"),
            "online": bool(n.get("online")),
            "advertised": covers(n.get("available_routes")),
            "approved": covers(n.get("approved_routes")),
            "route": route,
        }

    async def _nodes_by_id(self) -> dict[int, dict]:
        try:
            return {int(n["id"]): n for n in await hs.nodes()}
        except Exception:
            return {}

    def _printer_view(self, p: dict, nodes: dict[int, dict] | None = None) -> dict:
        fqdn = self.manager.printer_fqdn(p)
        res = p.get("resource") or "ipp/print"
        urls = {}
        if p["protocol"] in ("ipp", "ipps"):
            port = "" if p["port"] == 631 else f":{p['port']}"
            urls["ipp"] = f"{p['protocol']}://{fqdn}{port}/{res}"
            urls["windows"] = f"{'https' if p['protocol'] == 'ipps' else 'http'}://{fqdn}:{p['port']}/{res}"
        elif p["protocol"] == "raw":
            urls["socket"] = f"socket://{fqdn}:{p['port']}"
        elif p["protocol"] == "lpd":
            urls["lpd"] = f"lpd://{fqdn}/queue"
        return {**p, "fqdn": fqdn, "urls": urls, "via": self._via_view(p, nodes or {})}

    async def printers_mobileconfig(self, _request: web.Request) -> web.Response:
        """iOS/iPadOS configuration profile with an AirPrint payload.

        iOS only browses for printers with Bonjour on the local network; over a VPN it
        often never asks for the wide-area DNS-SD records. A profile adds the printers
        by IP address instead, and the iPhone reaches them through the subnet router.
        """
        body = printers.airprint_profile(self.manager.state["printers"], self.opts.base_domain)
        if body is None:
            raise web.HTTPNotFound(text="No IPP printers added")
        return web.Response(
            body=body,
            content_type="application/x-apple-aspen-config",
            # inline + top-level tab: iOS then offers to install it instead of saving it to Files.
            headers={"Content-Disposition": 'inline; filename="headscale-printers.mobileconfig"'},
        )

    async def printers_list(self, _request: web.Request) -> web.Response:
        nodes = await self._nodes_by_id()
        router_ips = set(self.manager.router.get("ips") or [])
        return web.json_response(
            {
                "printers": [self._printer_view(p, nodes) for p in self.manager.state["printers"]],
                "networks": [str(n) for n in self.manager.lan_networks()],
                # Devices a printer elsewhere can be reached through (not the app's own router).
                "via_nodes": [
                    {"id": i, "name": n.get("given_name") or n.get("name"), "online": bool(n.get("online"))}
                    for i, n in sorted(nodes.items())
                    if not router_ips.intersection(n.get("ip_addresses") or [])
                ],
            }
        )

    async def printers_scan(self, request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else {}
        found = await printers.discover(self.manager.lan_networks(), bool(body.get("sweep")))
        added = {p["ip"] for p in self.manager.state["printers"]}
        for f in found:
            f["added"] = f["ip"] in added
            f["suggested_slug"] = printers.slugify(f.get("name") or f["ip"])
        return web.json_response({"found": found})

    async def printers_add(self, request: web.Request) -> web.Response:
        printer = await self.manager.add_printer(await request.json())
        return web.json_response(self._printer_view(printer, await self._nodes_by_id()))

    async def printers_delete(self, request: web.Request) -> web.Response:
        if not await self.manager.remove_printer(request.match_info["id"]):
            raise web.HTTPNotFound()
        return web.json_response({"ok": True})

    async def printers_test(self, request: web.Request) -> web.Response:
        p = next((x for x in self.manager.state["printers"] if x["id"] == request.match_info["id"]), None)
        if p is None:
            raise web.HTTPNotFound()
        if p.get("via_node"):
            # The app's own router does not use other nodes' routes, so check the path instead.
            via = self._via_view(p, await self._nodes_by_id()) or {}
            if via.get("missing"):
                return web.json_response({"ok": False, "error": "via_missing", "via": via})
            if not via.get("online"):
                return web.json_response({"ok": False, "error": "via_offline", "via": via})
            if not via.get("advertised"):
                return web.json_response({"ok": False, "error": "via_not_advertised", "via": via})
            if not via.get("approved"):
                return web.json_response({"ok": False, "error": "via_not_approved", "via": via})
            return web.json_response({"ok": True, "state": "via_ready", "via": via})
        if p["protocol"] in ("ipp", "ipps"):
            try:
                info = await ipp.get_printer_attributes(
                    p["ip"], p["port"], p.get("resource") or "ipp/print", tls=p["protocol"] == "ipps"
                )
                return web.json_response({"ok": True, **info})
            except Exception as exc:
                return web.json_response({"ok": False, "error": str(exc)})
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(p["ip"], p["port"]), 4)
            writer.close()
            return web.json_response({"ok": True, "state": "port open"})
        except (TimeoutError, OSError) as exc:
            return web.json_response({"ok": False, "error": str(exc) or "timeout"})

    # -------------------------------------------------------------- services
    def _service_view(self, svc: dict) -> dict:
        fqdn = f"{svc['slug']}.{self.opts.base_domain}"
        ports = set(svc.get("ports") or [])
        urls: dict[str, str] = {}
        if svc["kind"] == "unifi":
            urls["app"] = f"https://{fqdn}"
            urls["rtsps"] = f"rtsps://{fqdn}:7441/<token>?enableSrtp"
            urls["rtsp"] = f"rtsp://{fqdn}:7447/<token>"
        elif svc["kind"] == "prusa":
            if svc.get("prusalink") or 80 in ports:
                urls["web"] = f"http://{fqdn}"
            if svc.get("camera") or 554 in ports:
                urls["camera"] = f"rtsp://{fqdn}/live"
        elif svc["kind"] == "plex":
            port = next(iter(sorted(ports)), 32400)
            urls["custom"] = f"http://{fqdn}:{port}"
            urls["web"] = f"http://{fqdn}:{port}/web"
        return {**svc, "fqdn": fqdn, "urls": urls}

    async def services_list(self, request: web.Request) -> web.Response:
        kind = request.query.get("kind")
        items = [s for s in self.manager.state.get("services", []) if not kind or s["kind"] == kind]
        return web.json_response(
            {
                "services": [self._service_view(s) for s in items],
                "networks": [str(n) for n in self.manager.lan_networks()],
            }
        )

    async def services_scan(self, request: web.Request) -> web.Response:
        kind = (await request.json()).get("kind")
        found = await services.scan(str(kind), self.manager.lan_networks())
        added = {(s["kind"], s["ip"]) for s in self.manager.state.get("services", [])}
        for f in found:
            f["added"] = (f["kind"], f["ip"]) in added
        return web.json_response({"found": found})

    async def services_add(self, request: web.Request) -> web.Response:
        return web.json_response(self._service_view(await self.manager.add_service(await request.json())))

    async def services_delete(self, request: web.Request) -> web.Response:
        if not await self.manager.remove_service(request.match_info["id"]):
            raise web.HTTPNotFound()
        return web.json_response({"ok": True})

    def _find_service(self, service_id: str) -> dict:
        svc = next((s for s in self.manager.state.get("services", []) if s["id"] == service_id), None)
        if svc is None:
            raise web.HTTPNotFound()
        return svc

    async def services_test(self, request: web.Request) -> web.Response:
        svc = self._find_service(request.match_info["id"])
        svc["last_test"] = await services.test(svc)
        from .store import save_state

        save_state(self.manager.state)
        return web.json_response(self._service_view(svc))

    async def services_share(self, request: web.Request) -> web.Response:
        body = await request.json()
        svc = await self.manager.set_shared(request.match_info["id"], bool(body.get("shared")))
        return web.json_response(self._service_view(svc))

    # ----------------------------------------------------------- multi-tenant
    def _mt(self):
        if self.manager.mt is None:
            raise web.HTTPNotFound(text="Multi-tenant mode is off (app option multi_tenant)")
        return self.manager.mt

    @staticmethod
    def _actor(request: web.Request) -> str:
        h = request.headers
        return h.get("X-Remote-User-Display-Name") or h.get("X-Remote-User-Name") or "ingress"

    async def tenancy_get(self, _request: web.Request) -> web.Response:
        from . import tenancy

        mt = self._mt()
        nodes = await hs.nodes()
        view = []
        for n in nodes:
            item = _node(n)
            item["domain"] = tenancy.node_domain(mt.model, n)
            item["location"] = tenancy.node_location(mt.model, n)
            item["ipv4"] = tenancy.node_ipv4(n)
            view.append(item)
        by_id = {int(n["id"]): n for n in nodes}
        devices = []
        for d in mt.model["devices"]:
            item = {**d, "vpn_ip": str(tenancy.device_vpn_ip(mt.model, d))}
            via = tenancy.via_node_id(d)
            if via is not None:
                node = by_id.get(via)
                route = f"{d['ip']}/32"
                addr = ipaddress.ip_address(d["ip"])

                def covers(routes, addr=addr):
                    return any(addr in ipaddress.ip_network(r, strict=False) for r in routes or [])

                item["route"] = {
                    "route": route,
                    "node": (node.get("given_name") or node.get("name")) if node else None,
                    "online": bool(node and node.get("online")),
                    "advertised": bool(node and covers(node.get("available_routes"))),
                    "approved": bool(node and covers(node.get("approved_routes"))),
                    "in_use": tenancy.device_in_use(mt.model, d["id"]),
                }
            devices.append(item)
        locations = []
        for loc in mt.model["locations"]:
            edge = tenancy.edge_node(mt.model, loc, nodes)
            locations.append(
                {
                    **loc,
                    "tag": tenancy.edge_tag(loc),
                    "edge": _node(edge) if edge else None,
                    "route_approved": bool(edge and loc["vpn_subnet"] in (edge.get("approved_routes") or [])),
                }
            )
        return web.json_response(
            {
                "model": {**mt.model, "devices": devices, "locations": locations},
                "status": mt.status(),
                "nodes": view,
                "server_url": self.opts.server_url_clean,
            }
        )

    async def tenancy_change(self, request: web.Request) -> web.Response:
        mt = self._mt()
        body = await request.json()
        await mt.change(request.match_info["kind"], request.match_info["action"], body, self._actor(request))
        return web.json_response({"ok": True, "status": mt.status()})

    async def tenancy_validate(self, request: web.Request) -> web.Response:
        body = await request.json()
        mt = self._mt()
        return web.json_response(
            await mt.dry_run(str(body.get("kind")), str(body.get("action")), body.get("data") or {})
        )

    async def tenancy_access(self, request: web.Request) -> web.Response:
        return web.json_response(await self._mt().access(request.query.get("ref", "")))

    async def tenancy_preview(self, _request: web.Request) -> web.Response:
        return web.json_response(await self._mt().preview())

    async def tenancy_apply(self, request: web.Request) -> web.Response:
        mt = self._mt()
        applied = await mt.apply(self._actor(request))
        self.manager.poke()
        return web.json_response({"ok": True, "applied": applied, "status": mt.status()})

    async def tenancy_edge_key(self, request: web.Request) -> web.Response:
        mt = self._mt()
        return web.json_response(await mt.edge_key(request.match_info["id"], self._actor(request)))

    async def tenancy_edge_nft(self, request: web.Request) -> web.Response:
        text = await self._mt().edge_nftables(request.match_info["id"])
        name = f"hsha-edge-{request.match_info['id']}.nft"
        return web.Response(
            text=text,
            content_type="text/plain",
            headers={"Content-Disposition": f'inline; filename="{name}"'},
        )

    async def tenancy_audit(self, _request: web.Request) -> web.Response:
        from . import audit

        self._mt()
        return web.json_response({"entries": audit.recent(100)})

    # ------------------------------------------------------------------ app
    async def index(self, _request: web.Request) -> web.FileResponse:
        return web.FileResponse(paths.WWW / "index.html", headers={"Cache-Control": "no-cache"})

    def build(self) -> web.Application:
        app = web.Application(middlewares=[ingress_only, json_errors])
        app.router.add_get("/", self.index)
        app.router.add_static("/static/", paths.WWW / "static")
        app.router.add_get("/api/status", self.status)
        app.router.add_get("/api/nodes", self.nodes)
        app.router.add_post("/api/nodes/{id:\\d+}/{action}", self.node_action)
        app.router.add_post("/api/authkey", self.authkey)
        app.router.add_post("/api/register", self.register)
        app.router.add_post("/api/apikey", self.apikey)
        app.router.add_get("/api/wizard", self.wizard_get)
        app.router.add_post("/api/wizard/answer", self.wizard_answer)
        app.router.add_post("/api/wizard/skip", self.wizard_skip)
        app.router.add_post("/api/wizard/options", self.wizard_options)
        app.router.add_post("/api/wizard/porttest", self.porttest_start)
        app.router.add_get("/api/wizard/porttest", self.porttest_get)
        app.router.add_post("/api/wizard/external", self.external_test)
        app.router.add_post("/api/wizard/dnstest", self.dns_test)
        app.router.add_get("/api/qr", self.qr)
        app.router.add_get("/api/update", self.update_get)
        app.router.add_post("/api/update", self.update_post)
        app.router.add_get("/api/services", self.services_list)
        app.router.add_post("/api/services/scan", self.services_scan)
        app.router.add_post("/api/services", self.services_add)
        app.router.add_delete("/api/services/{id}", self.services_delete)
        app.router.add_post("/api/services/{id}/test", self.services_test)
        app.router.add_post("/api/services/{id}/share", self.services_share)
        app.router.add_get("/api/tenancy", self.tenancy_get)
        app.router.add_get("/api/tenancy/preview", self.tenancy_preview)
        app.router.add_post("/api/tenancy/validate", self.tenancy_validate)
        app.router.add_get("/api/tenancy/access", self.tenancy_access)
        app.router.add_post("/api/tenancy/apply", self.tenancy_apply)
        app.router.add_get("/api/tenancy/audit", self.tenancy_audit)
        app.router.add_post("/api/tenancy/locations/{id}/key", self.tenancy_edge_key)
        app.router.add_get("/api/tenancy/locations/{id}/nftables", self.tenancy_edge_nft)
        app.router.add_post(
            "/api/tenancy/{kind:domain|location|device|connection|group|profile}/{action:create|update|delete}",
            self.tenancy_change,
        )
        app.router.add_get("/api/printers", self.printers_list)
        app.router.add_get("/api/printers.mobileconfig", self.printers_mobileconfig)
        app.router.add_post("/api/printers/scan", self.printers_scan)
        app.router.add_post("/api/printers", self.printers_add)
        app.router.add_delete("/api/printers/{id}", self.printers_delete)
        app.router.add_post("/api/printers/{id}/test", self.printers_test)
        app.on_startup.append(self._start_manager)
        app.on_cleanup.append(self._stop_manager)
        return app

    async def _start_manager(self, app: web.Application) -> None:
        app["manager_task"] = asyncio.create_task(self.manager.run())

    async def _stop_manager(self, app: web.Application) -> None:
        app["manager_task"].cancel()


def main() -> int:
    logging.basicConfig(
        level=getattr(logging, os.environ.get("HSHA_LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="[hsha] %(levelname)s %(message)s",
    )
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    port = supervisor.ingress_port()
    app = App().build()
    log.info("Ingress UI listening on port %s", port)
    web.run_app(app, host=os.environ.get("HSHA_BIND", "0.0.0.0"), port=port, print=None, access_log=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
