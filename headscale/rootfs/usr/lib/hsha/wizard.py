"""Setup wizard: evaluates each setup step, runs live checks and applies option changes.

The frontend renders the texts (NL/EN); this module returns step ids, statuses,
problem codes and the data needed to explain them.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import time
from urllib.parse import urlsplit

from . import certs, hs, netcheck, paths, probe, supervisor
from .options import DEFAULTS, Options, OptionsError
from .policy import ROUTER_TAG
from .store import read_json, save_state, write_json

log = logging.getLogger("hsha.wizard")

# Options the wizard may change.
EDITABLE = {
    "server_url": str,
    "tls_mode": str,
    "certfile": str,
    "keyfile": str,
    "listen_port": int,
    "stun_port": int,
    "base_domain": str,
    "admin_user": str,
    "subnet_router": bool,
    "exit_node": bool,
    "derp_enabled": bool,
    "tailscale_derp_fallback": bool,
    "headplane": bool,
    "airprint_dns": bool,
    "dns_via_home": bool,
}
# Answers / confirmations the user can give.
ANSWERS = {
    "router443": {"free", "busy", "unknown"},
    "forwards_done": {True, False},
    "external_ok": {True, False},
    "proxy_ok": {True, False},
}
OPTIONAL_STEPS = {"headplane", "printers", "airprint"}
STEP_ORDER = [
    "certificate",
    "address",
    "ports",
    "tls",
    "external",
    "tailscale",
    "device",
    "headplane",
    "printers",
    "airprint",
]


class Wizard:
    def __init__(self, app):
        self.app = app  # web.App: provides .opts and .manager
        self._cache: dict[str, tuple[float, object]] = {}
        self.port_test: probe.PortTest | None = None
        self._port_task: asyncio.Task | None = None

    # ------------------------------------------------------------ helpers
    @property
    def opts(self) -> Options:
        return self.app.opts

    @property
    def wstate(self) -> dict:
        state = self.app.manager.state
        state.setdefault("wizard", {})
        state["wizard"].setdefault("answers", {})
        state["wizard"].setdefault("skipped", [])
        return state["wizard"]

    async def _cached(self, key: str, ttl: float, refresh: bool, func, *args):
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit and not refresh and now - hit[0] < ttl:
            return hit[1]
        try:
            value = await asyncio.to_thread(func, *args)
        except Exception as exc:
            value = {"error": str(exc)}
        self._cache[key] = (now, value)
        return value

    # ------------------------------------------------------------ steps
    async def evaluate(self, refresh: bool = False, force_tls: bool = False) -> dict:
        o = self.opts
        runtime = read_json(paths.RUNTIME, {})
        setup = runtime.get("setup_mode")
        answers = self.wstate["answers"]
        skipped = set(self.wstate["skipped"])
        hs_running = await asyncio.to_thread(netcheck.tcp_listening, int(o.listen_port))
        steps: dict[str, dict] = {}

        # 1. Certificate (from a separate app via /ssl) ------------------------------
        inventory = await asyncio.to_thread(certs.inventory)
        providers = await self._cached("certapps", 60, refresh, supervisor.certificate_apps)
        providers = providers if isinstance(providers, list) else []
        cert_problem = None
        issues = []
        if o.tls_mode == "none":
            status = "ok" if answers.get("proxy_ok") else "todo"
        elif o.tls_mode == "letsencrypt":
            status, issues = "fail", ["builtin_le_removed"]
        elif not inventory:
            status, issues = "todo", ["no_certificates"]
        else:
            cert_problem = certs.check(o.certfile, o.keyfile, o.server_host) if o.configured else None
            chosen = next((c for c in inventory if c["file"] == o.certfile), None)
            if not o.configured:
                status = "todo"
            elif cert_problem:
                status, issues = "fail", ["cert_problem"]
            elif chosen and chosen["days_left"] is not None and chosen["days_left"] < 14:
                status, issues = "warn", ["cert_expiring"]
            else:
                status = "ok"
        steps["certificate"] = {
            "status": status,
            "issues": issues,
            "data": {
                "tls_mode": o.tls_mode,
                "certfile": o.certfile,
                "keyfile": o.keyfile,
                "certificates": inventory,
                "providers": providers,
                "problem": cert_problem,
                "server_host": o.server_host if o.configured else "",
            },
        }

        # 2. Address ----------------------------------------------------------
        dns = {}
        if o.configured:
            resolved = await self._cached(f"dns:{o.server_host}", 60, refresh, netcheck.resolve_a, o.server_host)
            public_ip = await self._cached("publicip", 300, refresh, netcheck.public_ipv4)
            if isinstance(resolved, dict):
                dns = {"error": resolved["error"]}
            else:
                dns = {"resolved": resolved, "public_ip": public_ip}
                dns["match"] = bool(public_ip and public_ip in resolved)
                dns["cgnat_suspect"] = bool(
                    public_ip and ipaddress.IPv4Address(public_ip) in ipaddress.IPv4Network("100.64.0.0/10")
                )
        issues = []
        if not o.configured:
            status = "todo"
        elif setup and setup.get("reason") == "invalid":
            status, issues = "fail", ["invalid_options"]
        elif dns.get("error"):
            status, issues = "warn", ["dns_error"]
        elif not dns.get("resolved"):
            status, issues = "fail", ["dns_missing"]
        elif not dns.get("match"):
            status, issues = "warn", ["dns_mismatch"]
        else:
            status = "ok"
        steps["address"] = {
            "status": status,
            "issues": issues,
            "data": {
                "configured": o.configured,
                "server_url": o.server_url_clean if o.configured else "",
                "admin_user": o.admin_user,
                "base_domain": o.base_domain,
                "dns": dns,
                "invalid_message": setup.get("message") if setup and setup.get("reason") == "invalid" else None,
            },
        }

        # 2. Ports --------------------------------------------------------------
        ports = runtime.get("ports") or {}
        local_busy = [p for p in (ports.get("tcp"), ports.get("udp")) if p and not p.get("free")]
        if setup and setup.get("reason") == "port_in_use":
            local_busy = [{"port": p} for p in setup.get("ports", [])]
        test = self.wstate.get("port_test")
        issues = []
        if local_busy:
            status, issues = "fail", ["local_port_in_use"]
        elif test and test.get("tcp", {}).get("status") == "ok":
            status = "ok"
            if any(u["status"] != "ok" and not u["optional"] for u in test.get("udp", [])):
                issues = ["udp_not_seen"]
        elif test and test.get("tcp", {}).get("status") in ("elsewhere", "closed"):
            status, issues = "fail", [f"tcp_{test['tcp']['status']}"]
        elif answers.get("forwards_done"):
            status = "ok"
        elif answers.get("router443") == "busy":
            status, issues = "todo", ["router_443_busy"]
        else:
            status = "todo"
        steps["ports"] = {
            "status": status,
            "issues": issues,
            "data": {
                "listen_port": o.listen_port,
                "external_port": o.external_port,
                "stun_port": o.stun_port,
                "derp_enabled": o.derp_enabled,
                "lan_ip": supervisor.lan_ip(),
                "local_busy": [p["port"] for p in local_busy],
                "router443": answers.get("router443"),
                "forwards_done": bool(answers.get("forwards_done")),
                "certificates": inventory,
                "port_test": test,
                "port_test_running": self.port_test.view()
                if self.port_test and self.port_test.state not in ("done", "error")
                else None,
                "port_test_possible": o.tls_mode != "none" and not local_busy,
            },
        }

        # 4. HTTPS: Headscale serves a certificate clients trust -------------------
        tls = None
        issues = []
        if o.tls_mode == "none":
            status = "ok" if answers.get("proxy_ok") else "todo"
        elif not o.configured or (setup and setup.get("reason")):
            status = "todo"
        elif not hs_running:
            status, issues = "fail", ["headscale_down"]
        else:
            tls = await self.app.manager.tls_probe(force=force_tls or refresh)
            if tls.get("ok"):
                status = "ok"
            else:
                status, issues = "fail", [f"tls_{tls.get('error', 'unknown')}"]
        steps["tls"] = {
            "status": status,
            "issues": issues,
            "data": {"tls_mode": o.tls_mode, "check": tls, "listen_port": o.listen_port},
        }

        # 5. Reachable from the internet (HTTPS end-to-end) ------------------------
        ext = self.wstate.get("external_test")
        if ext and ext.get("server_url") != o.server_url_clean:
            ext = None
        if (ext and ext.get("ok")) or answers.get("external_ok") is True:
            status = "ok"
        elif (ext and ext.get("ok") is False) or answers.get("external_ok") is False:
            status = "fail"
        else:
            status = "todo"
        steps["external"] = {
            "status": status,
            "issues": [],
            "data": {
                "health_url": f"{o.server_url_clean}/health" if o.configured else "",
                "auto": ext,
                "answer": answers.get("external_ok"),
                "possible": steps["tls"]["status"] == "ok",
            },
        }

        # 5. Tailscale on Home Assistant (subnet router) ---------------------------
        router = self.app.manager.router or {}
        others = await self._cached("tsapps", 60, refresh, supervisor.other_tailscale_apps)
        others = others if isinstance(others, list) else []
        running_others = [a for a in others if a.get("state") == "started"]
        lan = self.app.manager.lan_routes()
        approved = set(router.get("approved") or [])
        issues = []
        if not o.subnet_router:
            status = "todo"
        elif running_others:
            status, issues = "warn", ["other_tailscale_running"]
        elif router.get("state") == "Running" and set(lan) <= approved:
            status = "ok"
        elif not self.app.manager.ready:
            status = "todo"
        else:
            status, issues = "warn", ["router_not_ready"]
        steps["tailscale"] = {
            "status": status,
            "issues": issues,
            "data": {
                "enabled": o.subnet_router,
                "exit_node": o.exit_node,
                "router": router,
                "lan_routes": lan,
                "other_apps": others,
            },
        }

        # 6. First device -------------------------------------------------------------
        nodes = []
        if self.app.manager.ready:
            with contextlib.suppress(Exception):
                nodes = await hs.nodes()
        own = [n for n in nodes if ROUTER_TAG not in (n.get("tags") or []) and (n.get("user") or {}).get("name")]
        steps["device"] = {
            "status": "ok" if own else "todo",
            "issues": [],
            "data": {
                "count": len(own),
                "online": sum(1 for n in own if n.get("online")),
                "login_server": o.server_url_clean if o.configured else "",
            },
        }

        # 7-9. Optional ----------------------------------------------------------------
        steps["headplane"] = {
            "status": "ok" if self.wstate.get("apikey_created") else "todo",
            "issues": [],
            "data": {"enabled": o.headplane},
        }
        steps["printers"] = {
            "status": "ok" if self.app.manager.state["printers"] else "todo",
            "issues": [],
            "data": {"count": len(self.app.manager.state["printers"])},
        }
        dns_rt = runtime.get("printer_dns") or {}
        dns_test = self.wstate.get("dns_test")
        ipp_printers = [p for p in self.app.manager.state["printers"] if p.get("protocol") in ("ipp", "ipps")]
        issues = []
        if not o.airprint_dns:
            status = "todo"
        elif not self.app.manager.state.get("router_ipv4"):
            status, issues = "warn", ["airprint_no_router"]
        elif dns_test and dns_test.get("ok"):
            status = "ok"
        elif dns_test:
            status, issues = "fail", ["airprint_test_failed"]
        else:
            status = "todo"
        steps["airprint"] = {
            "status": status,
            "issues": issues,
            "data": {
                "enabled": o.airprint_dns,
                "dns_via_home": o.dns_via_home,
                "domain": o.printer_domain,
                "mode": dns_rt.get("mode"),
                "port": dns_rt.get("port"),
                "router_ip": self.app.manager.state.get("router_ipv4"),
                "printers": len(ipp_printers),
                "test": dns_test,
                "recent_queries": read_json(paths.RUN / "dns-queries.json", [])[-25:],
                "pushed": self._pushed_dns(),
            },
        }
        out = []
        for sid in STEP_ORDER:
            step = steps[sid]
            if sid in skipped and step["status"] != "ok":
                step["status"] = "skipped"
            out.append({"id": sid, "optional": sid in OPTIONAL_STEPS, **step})
        done = sum(1 for s in out if s["status"] in ("ok", "skipped"))
        return {
            "progress": round(100 * done / len(out)),
            "done": done,
            "total": len(out),
            "setup_mode": setup,
            "headscale_running": hs_running,
            "supervisor": supervisor.available(),
            "steps": out,
        }

    # ------------------------------------------------------------ port test
    def start_port_test(self, mode: str) -> dict:
        if self.port_test and self.port_test.state not in ("done", "error"):
            return self.port_test.view()
        o = self.opts
        if mode not in ("auto", "phone"):
            raise ValueError("mode must be auto or phone")
        if o.tls_mode == "none":
            raise ValueError("The port test is not available behind your own reverse proxy (tls_mode none)")
        self.port_test = probe.PortTest(
            listen_port=int(o.listen_port),
            external_port=int(o.external_port),
            stun_port=int(o.stun_port) if o.derp_enabled else None,
            test_ts_port=bool(o.subnet_router),
            mode=mode,
            duration=25 if mode == "auto" else 120,
        )
        self._port_task = asyncio.create_task(self._run_port_test(self.port_test))
        return self.port_test.view()

    async def _run_port_test(self, test: probe.PortTest) -> None:
        await test.run()
        if test.results:
            self.wstate["port_test"] = {**test.results, "time": int(time.time())}
            if test.results["tcp"]["status"] == "ok":
                self.wstate["answers"]["forwards_done"] = True
            save_state(self.app.manager.state)
            self.app.manager.poke()

    async def external_test(self) -> dict:
        """Fetch https://<server>/health from check-host.net nodes (outside the home network)."""
        o = self.opts
        url = f"{o.server_url_clean}/health"
        result = await asyncio.to_thread(probe.external_https, url)
        result["server_url"] = o.server_url_clean
        result["time"] = int(time.time())
        self.wstate["external_test"] = result
        save_state(self.app.manager.state)
        return result

    @staticmethod
    def _pushed_dns() -> dict:
        """The DNS settings Headscale sends to devices (from the generated config)."""
        import yaml

        try:
            cfg = yaml.safe_load(paths.HS_CONFIG.read_text()) or {}
        except (OSError, yaml.YAMLError):
            return {}
        dns = cfg.get("dns") or {}
        ns = dns.get("nameservers") or {}
        return {
            "search_domains": dns.get("search_domains") or [],
            "split": ns.get("split") or {},
            "global": ns.get("global") or [],
            "override_local_dns": dns.get("override_local_dns"),
        }

    async def dns_test(self) -> dict:
        """Query 127.0.0.1:53 like a tailnet device does (the router forwards port 53 there)."""
        from . import dnssd

        d = self.opts.printer_domain
        browse = await asyncio.to_thread(dnssd.lookup, f"b._dns-sd._udp.{d}", "PTR")
        printers = await asyncio.to_thread(dnssd.lookup, f"_ipp._tcp.{d}", "PTR")
        normal = await asyncio.to_thread(dnssd.lookup, "www.home-assistant.io", "A")
        # The printer's own name (A record): this is what the iPhone asks right before printing.
        hosts = []
        for p in self.app.manager.state.get("printers", []):
            if p.get("protocol") not in ("ipp", "ipps"):
                continue
            name = f"{p['slug']}.{d}"
            via53 = await asyncio.to_thread(dnssd.lookup, name, "A")
            direct = await asyncio.to_thread(dnssd.lookup, name, "A", "127.0.0.1", dnssd.ALT_PORT, 2)
            hosts.append({"name": name, "ip": p.get("ip"), "via53": via53, "direct": direct})
        hosts_ok = all(h["via53"].get("ok") for h in hosts)
        result = {
            "ok": bool(browse.get("ok")) and hosts_ok,
            "browse": browse,
            "printers": printers,
            "hosts": hosts,
            "normal_dns": normal,
            "time": int(time.time()),
        }
        self.wstate["dns_test"] = result
        save_state(self.app.manager.state)
        return result

    def port_test_view(self) -> dict | None:
        return self.port_test.view() if self.port_test else None

    # ------------------------------------------------------------ answers
    def answer(self, key: str, value) -> None:
        if key not in ANSWERS or value not in ANSWERS[key]:
            raise ValueError(f"Unknown answer {key}={value!r}")
        self.wstate["answers"][key] = value
        save_state(self.app.manager.state)

    def skip(self, step: str, skipped: bool) -> None:
        if step not in STEP_ORDER:
            raise ValueError(f"Unknown step {step}")
        current = set(self.wstate["skipped"])
        current.add(step) if skipped else current.discard(step)
        self.wstate["skipped"] = sorted(current)
        save_state(self.app.manager.state)

    def mark(self, flag: str) -> None:
        self.wstate[flag] = True
        save_state(self.app.manager.state)

    # ------------------------------------------------------------ options
    @staticmethod
    def _coerce(changes: dict) -> dict:
        out = {}
        for key, value in changes.items():
            if key not in EDITABLE:
                raise ValueError(f"Option {key} cannot be changed here")
            typ = EDITABLE[key]
            if typ is bool:
                out[key] = bool(value)
            elif typ is int:
                out[key] = int(value)
            else:
                out[key] = str(value).strip()
        if "server_url" in out:
            url = out["server_url"]
            if "://" not in url:
                url = "https://" + url
            parts = urlsplit(url)
            out["server_url"] = f"{parts.scheme}://{parts.netloc}".lower()
        if "admin_user" in out:
            out["admin_user"] = out["admin_user"].lower()
        if "base_domain" in out:
            out["base_domain"] = out["base_domain"].lower().strip(".")
        return out

    async def apply_options(self, changes: dict) -> dict:
        changes = self._coerce(changes)
        current = await asyncio.to_thread(supervisor.self_options)
        if current is None:
            current = read_json(paths.OPTIONS, {})
        merged = {**DEFAULTS, **current, **changes}
        candidate = Options(merged)
        if not candidate.configured:
            raise ValueError("Enter your own server address first")
        try:
            candidate.validate()
        except OptionsError as exc:
            raise ValueError(str(exc)) from exc
        if all(current.get(k) == v for k, v in changes.items()):
            return {"changed": False, "restarting": False}
        if supervisor.available():
            await asyncio.to_thread(supervisor.validate_options, merged)
            await asyncio.to_thread(supervisor.save_options, merged)
            asyncio.get_running_loop().call_later(1.0, lambda: asyncio.ensure_future(self._restart()))
            return {"changed": True, "restarting": True}
        # Development / tests without a Supervisor.
        write_json(paths.OPTIONS, merged, 0o600)
        return {"changed": True, "restarting": False}

    async def _restart(self) -> None:
        log.info("Options changed by the setup wizard: restarting the app")
        await asyncio.to_thread(supervisor.restart_self)
