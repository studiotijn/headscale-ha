"""Ingress web UI + JSON API.

Only reachable through Home Assistant ingress: requests must come from the
Supervisor's ingress proxy (172.30.32.2). Home Assistant authenticates the user.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import time

from aiohttp import web

from . import __version__, hs, ipp, paths, printers, supervisor
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
            await hs.approve_routes(node_id, node.get("available_routes") or [])
        else:
            raise web.HTTPNotFound()
        self.manager.poke()
        return web.json_response({"ok": True})

    # ------------------------------------------------------------------ keys
    async def authkey(self, request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else {}
        hours = max(1, min(int(body.get("hours", 1)), 24 * 7))
        reusable = bool(body.get("reusable", False))
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
        await hs.register(auth_id, self.opts.admin_user)
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
    def _printer_view(self, p: dict) -> dict:
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
        return {**p, "fqdn": fqdn, "urls": urls}

    async def printers_list(self, _request: web.Request) -> web.Response:
        return web.json_response(
            {
                "printers": [self._printer_view(p) for p in self.manager.state["printers"]],
                "networks": [str(n) for n in self.manager.lan_networks()],
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
        return web.json_response(self._printer_view(printer))

    async def printers_delete(self, request: web.Request) -> web.Response:
        if not await self.manager.remove_printer(request.match_info["id"]):
            raise web.HTTPNotFound()
        return web.json_response({"ok": True})

    async def printers_test(self, request: web.Request) -> web.Response:
        p = next((x for x in self.manager.state["printers"] if x["id"] == request.match_info["id"]), None)
        if p is None:
            raise web.HTTPNotFound()
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
        app.router.add_get("/api/printers", self.printers_list)
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
