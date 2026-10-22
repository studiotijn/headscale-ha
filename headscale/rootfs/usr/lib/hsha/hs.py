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


async def nodes() -> list[dict]:
    return await run("nodes", "list") or []


async def delete_node(node_id: int) -> None:
    await run("nodes", "delete", "--identifier", str(node_id), "--force")


async def expire_node(node_id: int) -> None:
    await run("nodes", "expire", "--identifier", str(node_id), "--force")


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
