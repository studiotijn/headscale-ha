"""Async wrapper around the `headscale` CLI (talks to the server over its unix socket)."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from typing import Any

from . import paths

HEADSCALE_BIN = os.environ.get("HSHA_HEADSCALE_BIN", shutil.which("headscale") or "/usr/bin/headscale")


class HeadscaleError(RuntimeError):
    pass


async def run(*args: str, json_output: bool = True, timeout: float = 30) -> Any:
    cmd = [HEADSCALE_BIN, "-c", str(paths.HS_CONFIG), *args]
    if json_output:
        cmd += ["-o", "json"]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "HEADSCALE_CLI_INSECURE": "0"},
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError as exc:
        proc.kill()
        raise HeadscaleError(f"headscale {' '.join(args)}: timed out") from exc
    text = out.decode().strip()
    if proc.returncode != 0:
        msg = (err.decode().strip() or text or f"exit code {proc.returncode}").splitlines()
        # Policy errors list every failed test on its own line; keep them.
        detail = "\n".join(msg[-15:]) if args and args[0] == "policy" else (msg[-1] if msg else "")
        raise HeadscaleError(f"headscale {' '.join(args)}: {detail}")
    if not json_output:
        return text
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Some commands print a human message even with -o json.
        return text


async def healthy() -> bool:
    try:
        await run("users", "list", timeout=5)
        return True
    except (HeadscaleError, OSError):
        return False


async def wait_healthy(timeout: float = 120) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if await healthy():
            return
        await asyncio.sleep(1)
    raise HeadscaleError("Headscale did not become ready in time")


async def version() -> str:
    out = await run("version", json_output=False)
    first = out.splitlines()[0] if out else ""
    return first.replace("headscale version", "").strip() or first


async def users() -> list[dict]:
    return await run("users", "list") or []


async def ensure_user(name: str) -> dict:
    for user in await users():
        if user.get("name") == name:
            return user
    await run("users", "create", name)
    for user in await users():
        if user.get("name") == name:
            return user
    raise HeadscaleError(f"could not create user {name}")


async def create_user(name: str, display_name: str | None = None) -> None:
    args = ["users", "create", name]
    if display_name:
        args += ["--display-name", display_name]
    await run(*args)


async def rename_user(old: str, new: str) -> None:
    """Live rename; devices keep their keys, IPs and names."""
    await run("users", "rename", "--name", old, "--new-name", new)


async def destroy_user(name: str) -> None:
    await run("users", "destroy", "--name", name, "--force")


async def nodes() -> list[dict]:
    return await run("nodes", "list") or []


async def delete_node(node_id: int) -> None:
    await run("nodes", "delete", "--identifier", str(node_id), "--force")


def dns_label(name: str) -> str:
    """A Headscale node name is a DNS label: lowercase letters, digits and dashes."""
    import re

    label = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower()).strip("-")
    return re.sub(r"-{2,}", "-", label)[:63].strip("-")


async def rename_node(node_id: int, name: str) -> str:
    """Change the name shown in the tailnet (given name / MagicDNS name), not the device's hostname."""
    label = dns_label(name)
    if not label:
        raise ValueError("Use letters, digits and dashes")
    await run("nodes", "rename", "--identifier", str(node_id), label)
    return label


async def expire_node(node_id: int) -> None:
    await run("nodes", "expire", "--identifier", str(node_id), "--force")


async def set_tags(node_id: int, tags: list[str]) -> None:
    await run("nodes", "tag", "--identifier", str(node_id), "--tags", ",".join(tags))


async def approve_routes(node_id: int, routes: list[str]) -> None:
    await run("nodes", "approve-routes", "--identifier", str(node_id), "--routes", ",".join(routes))


async def create_preauthkey(
    *, user_id: int | None = None, tags: list[str] | None = None, reusable: bool = False, expiration: str = "1h"
) -> str:
    args = ["preauthkeys", "create", "--expiration", expiration]
    if user_id is not None:
        args += ["--user", str(user_id)]
    if tags:
        args += ["--tags", ",".join(tags)]
    if reusable:
        args.append("--reusable")
    result = await run(*args)
    if isinstance(result, dict) and result.get("key"):
        return result["key"]
    if isinstance(result, str) and result:
        return result.strip()
    raise HeadscaleError(f"unexpected preauthkey output: {result!r}")


async def register(auth_id: str, user: str) -> None:
    await run("auth", "register", "--auth-id", auth_id, "--user", user, json_output=False)


async def create_apikey(expiration: str = "90d") -> str:
    result = await run("apikeys", "create", "--expiration", expiration, json_output=False)
    return result.strip().splitlines()[-1].strip()


async def get_policy() -> str | None:
    try:
        text = await run("policy", "get", json_output=False)
    except HeadscaleError as exc:
        if "not found" in str(exc).lower() or "no policy" in str(exc).lower():
            return None
        raise
    return text or None


async def policy_check(policy_text: str) -> dict:
    """Validate a policy (including its tests) against the running server without applying it."""
    fd, tmp = tempfile.mkstemp(suffix=".hujson", dir=str(paths.RUN))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(policy_text)
        try:
            out = await run("policy", "check", "--file", tmp, json_output=False)
            return {"ok": True, "message": out or "Policy is valid"}
        except HeadscaleError as exc:
            return {"ok": False, "message": str(exc)}
    finally:
        os.unlink(tmp)


async def set_policy(policy_text: str) -> None:
    fd, tmp = tempfile.mkstemp(suffix=".hujson", dir=str(paths.RUN))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(policy_text)
        await run("policy", "set", "--file", tmp, json_output=False)
    finally:
        os.unlink(tmp)


# ------------------------------------------------------------------ move a device to another user
# Headscale 0.29 has no CLI/API command to change a node's owner. The node keeps its keys and
# tailnet IPs; only nodes.user_id changes. Headscale keeps nodes in memory, so it must be stopped
# while the database is changed and started again afterwards (devices reconnect in seconds).
HS_SERVICE = os.environ.get("HSHA_HS_SERVICE", "/run/service/headscale")
S6_SVC = shutil.which("s6-svc") or "/command/s6-svc"
S6_SVWAIT = shutil.which("s6-svwait") or "/command/s6-svwait"


def db_move_node(db_path: str, node_id: int, user_name: str) -> dict:
    """Change the owner of one (untagged) node in Headscale's SQLite database."""
    import sqlite3

    con = sqlite3.connect(db_path, timeout=10)
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(nodes)")}
        if not {"id", "user_id", "tags"} <= cols:
            raise HeadscaleError("Unexpected Headscale database layout; not changing it")
        row = con.execute(
            "SELECT user_id, tags, given_name FROM nodes WHERE id = ? AND deleted_at IS NULL", (node_id,)
        ).fetchone()
        if row is None:
            raise HeadscaleError(f"Device {node_id} not found")
        old_user, tags, name = row
        if tags and json.loads(tags or "[]"):
            raise HeadscaleError(f"{name} is a tagged device; change its tag instead")
        user = con.execute(
            "SELECT id FROM users WHERE name = ? AND deleted_at IS NULL ORDER BY id LIMIT 1", (user_name,)
        ).fetchone()
        if user is None:
            raise HeadscaleError(f"User {user_name} does not exist")
        if user[0] != old_user:
            with con:
                con.execute("UPDATE nodes SET user_id = ? WHERE id = ?", (user[0], node_id))
        return {"node": name, "from_user_id": old_user, "to_user_id": user[0], "changed": user[0] != old_user}
    finally:
        con.close()


async def _svc(*args: str, timeout: float = 30) -> int:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    try:
        return await asyncio.wait_for(proc.wait(), timeout)
    except TimeoutError:
        proc.kill()
        return -1


async def _stop_headscale() -> None:
    await _svc(S6_SVC, "-d", HS_SERVICE)
    if await _svc(S6_SVWAIT, "-D", "-t", "20000", HS_SERVICE, timeout=25) != 0:
        raise HeadscaleError("Headscale did not stop in time; nothing was changed")


async def _start_headscale() -> None:
    await _svc(S6_SVC, "-u", HS_SERVICE)


async def move_node(node_id: int, user_name: str, stop=None, start=None) -> dict:
    """Give a device another owner (user). Restarts Headscale for a few seconds."""
    node = next((n for n in await nodes() if int(n["id"]) == int(node_id)), None)
    if node is None:
        raise HeadscaleError(f"Device {node_id} not found")
    if node.get("tags"):
        raise HeadscaleError("Tagged devices (servers, routers) belong to their tag, not to a user")
    if (node.get("user") or {}).get("name") == user_name:
        return {"node": node.get("given_name"), "changed": False}
    await ensure_user(user_name)
    db = str(paths.HS_DIR / "db.sqlite")
    stop, start = stop or _stop_headscale, start or _start_headscale
    await stop()
    try:
        backup = f"{db}.before-move"
        await asyncio.to_thread(_backup, db, backup)
        result = await asyncio.to_thread(db_move_node, db, int(node_id), user_name)
    finally:
        await start()
    await wait_healthy(90)
    return result


def _backup(db: str, target: str) -> None:
    import sqlite3

    src, dst = sqlite3.connect(db), sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()


# ------------------------------------------------------------------ user display names / merging
def db_users(db_path: str, display: dict[str, str], merge: dict[str, str]) -> dict:
    """Set users' display names and move the devices of ``merge`` keys to their value user.

    The CLI cannot change a display name or a device's owner, so this edits the database
    (Headscale must be stopped).
    """
    import sqlite3

    con = sqlite3.connect(db_path, timeout=10)
    try:
        ucols = {r[1] for r in con.execute("PRAGMA table_info(users)")}
        ncols = {r[1] for r in con.execute("PRAGMA table_info(nodes)")}
        if not {"id", "name", "display_name"} <= ucols or not {"id", "user_id", "tags"} <= ncols:
            raise HeadscaleError("Unexpected Headscale database layout; not changing it")

        def uid(name: str) -> int:
            row = con.execute(
                "SELECT id FROM users WHERE name = ? AND deleted_at IS NULL ORDER BY id LIMIT 1", (name,)
            ).fetchone()
            if row is None:
                raise HeadscaleError(f"User {name} does not exist")
            return row[0]

        moved = 0
        with con:
            for name, shown in display.items():
                con.execute("UPDATE users SET display_name = ? WHERE id = ?", (shown, uid(name)))
            for old, new in merge.items():
                cur = con.execute(
                    "UPDATE nodes SET user_id = ? WHERE user_id = ? AND deleted_at IS NULL", (uid(new), uid(old))
                )
                moved += cur.rowcount
        return {"display": sorted(display), "moved": moved}
    finally:
        con.close()


async def set_user_details(display: dict[str, str], merge: dict[str, str], stop=None, start=None) -> dict:
    """Apply db_users with Headscale stopped for a few seconds (database backup first)."""
    if not display and not merge:
        return {"display": [], "moved": 0}
    db = str(paths.HS_DIR / "db.sqlite")
    stop, start = stop or _stop_headscale, start or _start_headscale
    await stop()
    try:
        await asyncio.to_thread(_backup, db, f"{db}.before-users")
        return await asyncio.to_thread(db_users, db, display, merge)
    finally:
        await start()
        await wait_healthy(timeout=60)
