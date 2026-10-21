"""Setup wizard: evaluates each setup step, runs live checks and applies option changes.

The frontend renders the texts (NL/EN); this module returns step ids, statuses,
problem codes and the data needed to explain them.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import ssl
import time
from urllib.parse import urlsplit

from . import hs, netcheck, paths, supervisor
from .options import DEFAULTS, Options, OptionsError
from .policy import ROUTER_TAG
from .store import read_json, save_state, write_json

log = logging.getLogger("hsha.wizard")

# Options the wizard may change.
EDITABLE = {
    "server_url": str,
    "tls_mode": str,
    "acme_email": str,
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
}
# Answers / confirmations the user can give.
ANSWERS = {
    "router443": {"free", "busy", "unknown"},
    "forwards_done": {True, False},
    "external_ok": {True, False},
    "proxy_ok": {True, False},
    "close8123_done": {True, False},
}
OPTIONAL_STEPS = {"headplane", "printers", "close8123"}
STEP_ORDER = ["address", "ports", "tls", "external", "tailscale", "device", "headplane", "printers", "close8123"]


class Wizard:
    def __init__(self, app):
        self.app = app  # web.App: provides .opts and .manager
        self._cache: dict[str, tuple[float, object]] = {}

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

    @staticmethod
    def ssl_certificates() -> list[dict]:
        """Certificates in /ssl with the hostnames they cover (for tls_mode ha_certificate)."""
        out = []
        if not paths.SSL.is_dir():
            return out
        for f in sorted(paths.SSL.glob("*.pem")) + sorted(paths.SSL.glob("*.crt")):
            try:
                info = ssl._ssl._test_decode_cert(str(f))
            except Exception:
                continue
            names = [v for k, v in info.get("subjectAltName", ()) if k == "DNS"]
            key_guess = None
            for cand in ("privkey.pem", f.name.replace("fullchain", "privkey"), f.name.replace(".crt", ".key")):
                if (paths.SSL / cand).is_file() and cand != f.name:
                    key_guess = cand
                    break
            out.append({"file": f.name, "names": names, "expires": info.get("notAfter"), "keyfile": key_guess})
        return out

    @staticmethod
    def covers(names: list[str], host: str) -> bool:
        for n in names:
            n = n.lower()
            if n == host or (n.startswith("*.") and host.endswith(n[1:]) and host.count(".") == n.count(".")):
                return True
        return False

    # ------------------------------------------------------------ steps
    async def evaluate(self, refresh: bool = False, force_tls: bool = False) -> dict:
        o = self.opts
        runtime = read_json(paths.RUNTIME, {})
        setup = runtime.get("setup_mode")
        answers = self.wstate["answers"]
        skipped = set(self.wstate["skipped"])
        hs_running = await asyncio.to_thread(netcheck.tcp_listening, int(o.listen_port))
        steps: dict[str, dict] = {}

        # 1. Address ----------------------------------------------------------
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
        issues = []
        if local_busy:
            status, issues = "fail", ["local_port_in_use"]
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
                "certificates": self.ssl_certificates(),
            },
        }

        # 3. TLS ---------------------------------------------------------------
        # A check makes Headscale contact Let's Encrypt when it has no certificate yet,
        # so it only runs once the port forwards are confirmed (or on explicit retest).
        tls = None
        issues = []
        if o.tls_mode == "none":
            status = "ok" if answers.get("proxy_ok") else "todo"
        elif not o.configured or (setup and setup.get("reason")):
            status = "todo"
        elif not hs_running:
            status, issues = "fail", ["headscale_down"]
        else:
            tls = await self.app.manager.tls_probe(force=force_tls)
            if tls.get("ok"):
                status = "ok"
            elif tls.get("error") == "not_checked":
                status, issues, tls = "todo", ["waiting_forwards"], None
            else:
                status, issues = "fail", [f"tls_{tls.get('error', 'unknown')}"]
        steps["tls"] = {
            "status": status,
            "issues": issues,
            "data": {
                "tls_mode": o.tls_mode,
                "acme_email": o.acme_email,
                "certfile": o.certfile,
                "keyfile": o.keyfile,
                "check": tls,
                "certificates": steps["ports"]["data"]["certificates"],
                "external_port": o.external_port,
            },
        }

        # 4. Reachable from the internet ------------------------------------------
        proven = bool(tls and tls.get("ok") and tls.get("lets_encrypt") and o.tls_mode == "letsencrypt")
        if proven or answers.get("external_ok") is True:
            status = "ok"
        elif answers.get("external_ok") is False:
            status = "fail"
        else:
            status = "todo"
        steps["external"] = {
            "status": status,
            "issues": [],
            "data": {
                "health_url": f"{o.server_url_clean}/health" if o.configured else "",
                "proven_by_letsencrypt": proven,
                "answer": answers.get("external_ok"),
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
        steps["close8123"] = {
            "status": "ok" if answers.get("close8123_done") else "todo",
            "issues": [],
            "data": {},
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
