"""Multi-tenant controller: model changes, preview/apply of the generated policy, drift and route checks.

Only active with the app option ``multi_tenant``. Changes to the model are first
*pending*; the generated policy is applied when the user presses Apply (or
Activate the first time). After that, changes that come only from the nodes
(an IP or a new device of a domain user) are applied automatically, because the
model the user approved did not change.
"""

from __future__ import annotations

import asyncio
import logging
import time

from . import audit, hs, policygen, tenancy
from .store import save_state
from .tenancy import ModelError

log = logging.getLogger("hsha.multitenant")


class MultiTenant:
    def __init__(self, manager):
        self.manager = manager
        self.opts = manager.opts
        self.model = tenancy.load(self.opts.admin_user)
        self.drift = False
        self.route_warnings: list[str] = []
        self.last_error: str | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------ context
    def _home_routes(self) -> list[str]:
        return self.manager.desired_routes() if self.opts.subnet_router else []

    def _remote_printers(self) -> list[dict]:
        return [p for p in self.manager.state.get("printers", []) if p.get("via_node")]

    def _shared(self) -> list[dict]:
        return [s for s in self.manager.state.get("services", []) if s.get("shared")]

    async def context(self, nodes: list[dict] | None = None) -> policygen.Context:
        if nodes is None:
            nodes = await hs.nodes()
        return policygen.Context(
            self.opts.admin_user,
            nodes,
            home_routes=self._home_routes(),
            exit_node=bool(self.opts.exit_node),
            shared_services=self._shared(),
            remote_printers=self._remote_printers(),
        )

    # ------------------------------------------------------------ model
    async def change(self, kind: str, action: str, data: dict, actor: str | None) -> dict:
        async with self._lock:
            nodes = await hs.nodes()
            new, summary = tenancy.apply_change(self.model, kind, action, data)
            tenancy.validate(new, nodes, self._home_routes())
            self.model = new
            tenancy.save(self.model)
            audit.record("model", actor, summary, revision=self.model["revision"], data=data)
            return self.model

    async def dry_run(self, kind: str, action: str, data: dict) -> dict:
        """Validate a change without saving it (live feedback in the editors)."""
        nodes = await hs.nodes()
        try:
            new, summary = tenancy.apply_change(self.model, kind, action, data)
            warnings = tenancy.validate(new, nodes, self._home_routes())
        except (ModelError, ValueError) as exc:
            return {"ok": False, "error": str(exc), "warnings": []}
        return {"ok": True, "summary": summary, "warnings": warnings}

    async def access(self, ref: str) -> dict:
        nodes = await hs.nodes()
        return tenancy.access(self.model, ref, {int(n["id"]): n for n in nodes})

    async def preview(self) -> dict:
        ctx = await self.context()
        gen = policygen.generate(self.model, ctx)
        check = await hs.policy_check(gen["text"])
        live = await hs.get_policy()
        return {
            "text": gen["text"],
            "sha256": gen["sha256"],
            "tests": gen["tests"],
            "warnings": gen["warnings"],
            "check": check,
            "live": live,
            "matrix": policygen.matrix(self.model, ctx),
        }

    async def apply(self, actor: str | None, reason: str = "apply") -> dict:
        async with self._lock:
            return await self._apply(actor, reason)

    async def _apply(self, actor: str | None, reason: str) -> dict:
        for user in tenancy.all_users(self.model):
            await hs.ensure_user(user)
        ctx = await self.context()
        gen = policygen.generate(self.model, ctx)
        if not self.model.get("activated"):
            # Keep the hand-made policy that the first activation replaces.
            before = await hs.get_policy()
            if before:
                audit.save_policy(f"pre-multitenant-{int(time.time())}", before)
        await hs.set_policy(gen["text"])  # Headscale runs the tests and refuses a failing policy
        self.model["activated"] = True
        self.model["applied"] = {
            "sha256": gen["sha256"],
            "revision": self.model["revision"],
            "at": int(time.time()),
            "by": actor or "system",
            "tests": gen["tests"],
        }
        tenancy.save(self.model)
        audit.save_policy(f"{int(time.time())}-r{self.model['revision']}-{gen['sha256'][:12]}", gen["text"])
        audit.record(
            reason,
            actor,
            f"policy applied ({gen['tests']} tests)",
            sha256=gen["sha256"],
            revision=self.model["revision"],
        )
        self.drift = False
        self.last_error = None
        log.info("Multi-tenant policy applied (revision %s, %s tests)", self.model["revision"], gen["tests"])
        return self.model["applied"]

    # ------------------------------------------------------------ loop
    async def reconcile(self) -> None:
        """Called from the manager loop: follow node changes, detect drift and odd routes."""
        if not self.model.get("activated"):
            return
        nodes = await hs.nodes()
        await self._check_routes(nodes)
        applied = self.model.get("applied") or {}
        async with self._lock:
            ctx = await self.context(nodes)
            try:
                gen = policygen.generate(self.model, ctx)
            except ModelError as exc:
                self.last_error = str(exc)
                return
            if applied.get("revision") == self.model["revision"] and gen["sha256"] != applied.get("sha256"):
                try:
                    await self._apply(None, "auto-apply")
                    log.info("Policy re-applied after a device change")
                except hs.HeadscaleError as exc:
                    self.last_error = str(exc)
                    log.warning("Automatic re-apply refused: %s", exc)
                    return
            applied = self.model.get("applied") or {}  # may just have been re-applied
            live = await hs.get_policy() or ""
            self.drift = policygen.HEADER.splitlines()[0] not in live or (applied.get("sha256", "")[:16] not in live)

    async def _sync_device_routes(self, nodes: list[dict]) -> None:
        """Approve exactly <ip>/32 for devices behind a router that a connection uses; withdraw the rest.

        Opening a port to such a device is what makes its route appear; nothing else of the
        network behind that router becomes reachable.
        """
        managed: dict[str, list[str]] = self.manager.state.setdefault("mt_routes", {})
        changed = False
        for n in nodes:
            nid = str(n["id"])
            if tenancy.node_location(self.model, n):
                continue  # Edgeboxes: their location subnet, handled below
            wanted = set(tenancy.device_routes(self.model, int(n["id"])))
            before = set(managed.get(nid, []))
            approved = set(n.get("approved_routes") or [])
            target = (approved - (before - wanted)) | wanted
            if target != approved:
                await hs.approve_routes(int(n["id"]), sorted(target))
                name = n.get("given_name") or n.get("name")
                added, removed = sorted(target - approved), sorted(approved - target)
                audit.record(
                    "routes",
                    None,
                    f"{name}: "
                    + "; ".join(
                        x
                        for x in (
                            f"approved {', '.join(added)}" if added else "",
                            f"withdrew {', '.join(removed)}" if removed else "",
                        )
                        if x
                    ),
                )
                log.info("Routes on %s: +%s -%s", name, added, removed)
                n["approved_routes"] = sorted(target)
            if sorted(wanted) != managed.get(nid, []):
                if wanted:
                    managed[nid] = sorted(wanted)
                else:
                    managed.pop(nid, None)
                changed = True
        if changed:
            save_state(self.manager.state)

    async def _check_routes(self, nodes: list[dict]) -> None:
        await self._sync_device_routes(nodes)
        warnings = []
        remote = self.manager.state.get("remote_routes", {})
        for n in nodes:
            allowed = set(tenancy.allowed_routes(self.model, n, self._home_routes()))
            allowed |= set(remote.get(str(n["id"]), []))
            name = n.get("given_name") or n.get("name")
            approved = set(n.get("approved_routes") or []) - {"0.0.0.0/0", "::/0"}
            if tenancy.node_location(self.model, n) and approved - allowed:
                # Edgeboxes are fully managed: withdraw anything outside their own location.
                keep = sorted(approved & allowed)
                await hs.approve_routes(int(n["id"]), keep)
                audit.record("route-revoked", None, f"{name}: withdrew {', '.join(sorted(approved - allowed))}")
                log.warning("Withdrew routes outside the model from Edgebox %s: %s", name, sorted(approved - allowed))
                approved = set(keep)
            for r in sorted(approved - allowed):
                warnings.append(f"{name}: route {r} is approved but not part of the model")
            for r in sorted(set(n.get("available_routes") or []) - approved - allowed - {"0.0.0.0/0", "::/0"}):
                warnings.append(f"{name}: offers route {r} that the model does not allow (not approved)")
        if warnings != self.route_warnings:
            for w in set(warnings) - set(self.route_warnings):
                log.warning("Route check: %s", w)
        self.route_warnings = warnings

    def allowed_routes_for(self, node: dict) -> list[str]:
        remote = self.manager.state.get("remote_routes", {})
        own = tenancy.allowed_routes(self.model, node, self._home_routes())
        return sorted(set(own) | set(remote.get(str(node["id"]), [])))

    # ------------------------------------------------------------ keys
    def user_for(self, domain_id: str | None, user: str | None) -> str:
        dom = tenancy.domain(self.model, domain_id or "") or tenancy.home_domain(self.model)
        if dom is None or not dom.get("users"):
            raise ModelError("This domain has no users; add one first")
        if user:
            if user not in dom["users"]:
                raise ModelError(f"User {user} is not part of domain {dom['name']}")
            return user
        return dom["users"][0]

    async def edge_key(self, loc_id: str, actor: str | None) -> dict:
        loc = tenancy.location(self.model, loc_id)
        if loc is None:
            raise ModelError("Unknown location")
        tag = tenancy.edge_tag(loc)
        if not self.model.get("activated") or f'"{tag}"' not in (await hs.get_policy() or ""):
            raise ModelError("Apply the policy first, so the Edgebox tag exists")
        key = await hs.create_preauthkey(tags=[tag], expiration="1h")
        audit.record("edge-key", actor, f"one-time key for {loc['name']} ({tag})")
        return {"tag": tag, "command": policygen.edge_up_command(loc, self.opts.server_url_clean, key)}

    async def tag_server(self, node_id: int, actor: str | None) -> dict:
        """Turn a device into a server of its network: tagged, no longer tied to a person, no expiry."""
        nodes = {int(n["id"]): n for n in await hs.nodes()}
        node = nodes.get(int(node_id))
        if node is None:
            raise ModelError("Unknown device")
        dom = tenancy.node_domain(self.model, node)
        if dom is None:
            raise ModelError("This device is not part of a network yet")
        if tenancy.node_location(self.model, node) or "tag:homerouter" in tenancy.node_tags(node):
            raise ModelError("Routers and Edgeboxes keep their own tag")
        tag = tenancy.server_tag(dom)
        if not self.model.get("activated") or f'"{tag}"' not in (await hs.get_policy() or ""):
            raise ModelError("Apply the policy first, so the server tag exists")
        await hs.set_tags(int(node_id), [tag])
        name = node.get("given_name") or node.get("name")
        audit.record("server-tag", actor, f"{name} is now a server ({tag})")
        return {"tag": tag}

    async def move_node(self, node_id: int, domain_id: str, user: str | None, actor: str | None) -> dict:
        """Move a device to another network: a new owner (user) or, for servers, the other server tag."""
        nodes = {int(n["id"]): n for n in await hs.nodes()}
        node = nodes.get(int(node_id))
        if node is None:
            raise ModelError("Unknown device")
        if tenancy.node_location(self.model, node) or "tag:homerouter" in tenancy.node_tags(node):
            raise ModelError("Routers and Edgeboxes stay in their own network")
        target = tenancy.domain(self.model, domain_id)
        if target is None:
            raise ModelError("Unknown network")
        name = node.get("given_name") or node.get("name")
        before = tenancy.node_domain(self.model, node)
        before_name = (tenancy.domain(self.model, before or "") or {}).get("name") or "-"
        tags = tenancy.node_tags(node)
        if tags:
            if not any(tag.endswith("-server") for tag in tags):
                raise ModelError("This device has a tag of its own; change it in Headplane")
            tag = tenancy.server_tag(target["id"])
            if not self.model.get("activated") or f'"{tag}"' not in (await hs.get_policy() or ""):
                raise ModelError("Apply the policy first, so the server tag of that network exists")
            await hs.set_tags(int(node_id), [tag])
            audit.record("move", actor, f"{name}: {before_name} → {target['name']} ({tag})")
            return {"node": name, "domain": target["id"], "tag": tag}
        owner = self.user_for(target["id"], user)
        try:
            result = await hs.move_node(int(node_id), owner)
        except hs.HeadscaleError as exc:
            raise ModelError(str(exc)) from exc
        audit.record("move", actor, f"{name}: {before_name} → {target['name']} (user {owner})")
        return {"node": name, "domain": target["id"], "user": owner, "changed": result.get("changed", True)}

    async def server_key(self, domain_id: str, hours: int, reusable: bool, actor: str | None) -> str:
        dom = tenancy.domain(self.model, domain_id)
        if dom is None:
            raise ModelError("Unknown network")
        tag = tenancy.server_tag(dom["id"])
        if not self.model.get("activated") or f'"{tag}"' not in (await hs.get_policy() or ""):
            raise ModelError("Apply the policy first, so the server tag exists")
        key = await hs.create_preauthkey(tags=[tag], reusable=reusable, expiration=f"{hours}h")
        audit.record("server-key", actor, f"key for a server in {dom['name']} ({tag})")
        return key

    async def edge_nftables(self, loc_id: str) -> str:
        ctx = await self.context()
        sha = (self.model.get("applied") or {}).get("sha256")
        return policygen.edge_nftables(self.model, loc_id, ctx, sha)

    # ------------------------------------------------------------ views
    def status(self) -> dict:
        applied = self.model.get("applied") or {}
        return {
            "activated": bool(self.model.get("activated")),
            "revision": self.model["revision"],
            "applied": applied or None,
            "pending": applied.get("revision") != self.model["revision"],
            "drift": self.drift,
            "route_warnings": self.route_warnings,
            "error": self.last_error,
        }
