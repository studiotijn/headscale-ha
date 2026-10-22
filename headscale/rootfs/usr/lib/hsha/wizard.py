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
    "multi_tenant": bool,
}
# Answers / confirmations the user can give.
ANSWERS = {
    "router443": {"free", "busy", "unknown"},
    "forwards_done": {True, False},
    "external_ok": {True, False},
    "proxy_ok": {True, False},
}
OPTIONAL_STEPS = {"headplane", "printers", "airprint"}
# A step that worked before only counts as broken after it has been failing this long,
# so a restart of the app (Headscale and the router come up again) never shows red.
BROKEN_GRACE = 600
# The setup card on the overview hides itself after this long at 100 %.
AUTO_HIDE_AFTER = 3600
CERT_NOTIFICATION = "headscale_certificate"
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
        w = state["wizard"]
        w.setdefault("answers", {})
        # "skipped" (before 0.12) counted as done; ignored steps simply don't count.
        if "skipped" in w:
            w["ignored"] = sorted(set(w.get("ignored", [])) | set(w.pop("skipped")))
        w.setdefault("ignored", [])
        w.setdefault("ever_ok", [])
        w.setdefault("nonok_since", {})
        return w

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
        ignored = set(self.wstate["ignored"])
        hs_running = await asyncio.to_thread(netcheck.tcp_listening, int(o.listen_port))
        steps: dict[str, dict] = {}

        # 1. Certificate (from a separate app via /ssl) ------------------------------
        inventory = await asyncio.to_thread(certs.inventory)
        providers = await self._cached("certapps", 60, refresh, supervisor.certificate_apps)
        providers = providers if isinstance(providers, list) else []
        cert_problem = None
        renewal = None
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
            renewal = certs.renewal(chosen) if chosen else None
            if renewal:
                renewal["file"] = chosen["file"]
                renewal["renewed"] = chosen.get("mtime")
            rstate = (renewal or {}).get("state")
            if not o.configured:
                status = "todo"
            elif cert_problem:
                status, issues = "fail", ["cert_problem"]
            elif rstate in ("critical", "expired"):
                status, issues = "fail", ["cert_renewal_critical"]
            elif rstate == "overdue":
                status, issues = "warn", ["cert_renewal_overdue"]
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
                "renewal": renewal,
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
        # The file in /ssl was renewed but Headscale still serves the old one?
        cert_step = steps["certificate"]
        served = (tls or self.app.manager.tls or {}).get("expires")
        on_disk = (cert_step["data"].get("renewal") or {}).get("expires")
        if served and on_disk and on_disk - served > certs.DAY and cert_step["status"] == "ok":
            cert_step["status"], cert_step["issues"] = "warn", ["cert_not_loaded"]
            cert_step["data"]["served_expires"] = served

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
        out = [{"id": sid, "optional": sid in OPTIONAL_STEPS, **steps[sid]} for sid in STEP_ORDER]
        summary = self._summarise(out, ignored)
        return {
            **summary,
            "setup_mode": setup,
            "headscale_running": hs_running,
            "supervisor": supervisor.available(),
            "steps": out,
        }

    # ------------------------------------------------------------ progress
    def _summarise(self, out: list[dict], ignored: set[str], now: float | None = None) -> dict:
        """Progress bar, broken steps and the overview card.

        - Ignored steps don't count: the bar is 100 % when every other step is done.
        - A step that worked before and has been failing for BROKEN_GRACE is broken
          (a red segment). Within the grace period it still counts as done.
        - The overview card hides itself after AUTO_HIDE_AFTER at 100 %, or when the
          user hides it; it comes back as soon as something new breaks.
        """
        now = time.time() if now is None else now
        w = self.wstate
        ever_ok = set(w["ever_ok"])
        since = w["nonok_since"]
        dirty = False
        segments, broken = [], []
        for step in out:
            sid, raw = step["id"], step["status"]
            if raw == "ok":
                if sid not in ever_ok:
                    ever_ok.add(sid)
                    dirty = True
                if since.pop(sid, None) is not None:
                    dirty = True
            elif sid in ever_ok and sid not in since:
                since[sid] = int(now)
                dirty = True
            is_broken = sid in ever_ok and raw != "ok" and now - since.get(sid, now) >= BROKEN_GRACE
            if sid in ignored:
                step["ignored"] = True
                continue
            if is_broken:
                step["broken"] = True
                step["broken_since"] = since[sid]
                broken.append(sid)
                state = "broken"
            elif raw == "ok" or sid in ever_ok:
                state = "ok"  # ok, or recovering within the grace period
            elif raw == "fail":
                state = "fail"
            elif raw == "warn":
                state = "warn"
            else:
                state = "todo"
            segments.append({"id": sid, "state": state})
        done = sum(1 for seg in segments if seg["state"] == "ok")
        total = len(segments)
        progress = 100 if not total else (100 * done // total if done < total else 100)
        complete = progress == 100

        if complete and not w.get("complete_since"):
            w["complete_since"] = int(now)
            dirty = True
        elif not complete and w.get("complete_since"):
            w["complete_since"] = None
            dirty = True
        hidden = w.get("overview_hidden")
        if hidden and set(broken) - set(hidden.get("broken", [])):
            w["overview_hidden"] = hidden = None  # something new broke: show the card again
            dirty = True
        auto_hidden = bool(complete and w.get("complete_since") and now - w["complete_since"] >= AUTO_HIDE_AFTER)
        if dirty:
            w["ever_ok"] = sorted(ever_ok)
            save_state(self.app.manager.state)
        return {
            "progress": progress,
            "done": done,
            "total": total,
            "segments": segments,
            "broken": broken,
            "ignored": sorted(ignored),
            "overview": {
                "visible": not hidden and not auto_hidden,
                "hidden_by_user": bool(hidden),
                "auto_hidden": auto_hidden,
                "complete_since": w.get("complete_since"),
                "auto_hide_after": AUTO_HIDE_AFTER,
            },
        }

    def set_overview_hidden(self, hidden: bool, broken: list[str]) -> None:
        self.wstate["overview_hidden"] = {"at": int(time.time()), "broken": sorted(broken)} if hidden else None
        # "Show again" after an automatic hide: restart the one-hour timer.
        if not hidden and self.wstate.get("complete_since"):
            self.wstate["complete_since"] = int(time.time())
        save_state(self.app.manager.state)

    # ------------------------------------------------------------ monitoring
    async def monitor(self) -> None:
        """Background check: keeps the progress history current and reports a
        certificate that is not renewed on time as a Home Assistant notification."""
        result = await self.evaluate()
        cert = next(s for s in result["steps"] if s["id"] == "certificate")
        renewal = cert["data"].get("renewal") or {}
        problem = next((i for i in cert["issues"] if i.startswith("cert_renewal_") or i == "cert_not_loaded"), None)
        if cert.get("ignored") or self.opts.tls_mode != "ha_certificate":
            problem = None
        key = f"{problem}:{renewal.get('expires')}" if problem else None
        if key == self.wstate.get("cert_notified"):
            return
        if problem:
            lang = await asyncio.to_thread(supervisor.core_language)
            title, message = cert_notification(problem, renewal, cert["data"], lang)
            await asyncio.to_thread(supervisor.notify, CERT_NOTIFICATION, title, message)
            log.warning("Certificate: %s", message.replace("\n", " "))
        elif self.wstate.get("cert_notified"):
            await asyncio.to_thread(supervisor.dismiss, CERT_NOTIFICATION)
            log.info("Certificate renewed on time again: notification removed")
        self.wstate["cert_notified"] = key
        save_state(self.app.manager.state)

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

    def ignore(self, step: str, ignored: bool) -> None:
        if step not in STEP_ORDER:
            raise ValueError(f"Unknown step {step}")
        current = set(self.wstate["ignored"])
        current.add(step) if ignored else current.discard(step)
        self.wstate["ignored"] = sorted(current)
        save_state(self.app.manager.state)

    skip = ignore  # API before 0.12

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


def _date(ts: int | None, lang: str) -> str:
    if not ts:
        return "?"
    d = time.localtime(ts)
    return time.strftime("%d-%m-%Y" if lang.startswith("nl") else "%Y-%m-%d", d)


def cert_notification(problem: str, renewal: dict, data: dict, lang: str) -> tuple[str, str]:
    """Title and text of the Home Assistant notification about the certificate."""
    nl = lang.startswith("nl")
    file = renewal.get("file") or data.get("certfile") or "?"
    expires = _date(renewal.get("expires"), lang)
    due = _date(renewal.get("due"), lang)
    le_app = next((p for p in data.get("providers") or [] if p.get("kind") == "letsencrypt"), None)
    if problem == "cert_not_loaded":
        if nl:
            return "Headscale: oud certificaat in gebruik", (
                f"Het certificaat /ssl/{file} is vernieuwd, maar Headscale gebruikt nog het oude "
                f"(geldig tot {_date(data.get('served_expires'), lang)}). Herstart de Headscale-app."
            )
        return "Headscale: old certificate in use", (
            f"The certificate /ssl/{file} was renewed, but Headscale still serves the old one "
            f"(valid until {_date(data.get('served_expires'), lang)}). Restart the Headscale app."
        )
    critical = problem == "cert_renewal_critical"
    if nl:
        hint = (
            "Start de Let's Encrypt-app en bekijk zijn logboek. Laat een automatisering hem elke week starten."
            if le_app
            else "Controleer de app die het certificaat maakt (Let's Encrypt of Duck DNS) en zijn logboek."
        )
        head = "verloopt binnenkort" if critical else "is niet op tijd vernieuwd"
        return f"Headscale: certificaat {head}", (
            f"/ssl/{file} verloopt op {expires}. Normaal wordt het rond {due} vernieuwd; dat is nog niet gebeurd. "
            f"Na het verlopen kunnen je apparaten Headscale niet meer bereiken.\n\n{hint}"
        )
    hint = (
        "Start the Let's Encrypt app and check its log. Let an automation start it every week."
        if le_app
        else "Check the app that creates the certificate (Let's Encrypt or Duck DNS) and its log."
    )
    head = "expires soon" if critical else "was not renewed on time"
    return f"Headscale: certificate {head}", (
        f"/ssl/{file} expires on {expires}. It is normally renewed around {due}; that has not happened yet. "
        f"Once it expires, your devices can no longer reach Headscale.\n\n{hint}"
    )
