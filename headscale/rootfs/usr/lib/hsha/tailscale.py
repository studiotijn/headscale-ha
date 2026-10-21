"""Async wrapper around the local `tailscale` CLI (subnet router / exit node)."""

from __future__ import annotations

import asyncio
import json
import os
import shutil

from . import paths

TAILSCALE_BIN = os.environ.get("HSHA_TAILSCALE_BIN", shutil.which("tailscale") or "/usr/bin/tailscale")
HOSTNAME = os.environ.get("HSHA_ROUTER_HOSTNAME", "home-assistant")


class TailscaleError(RuntimeError):
    pass


async def run(*args: str, timeout: float = 60) -> str:
    proc = await asyncio.create_subprocess_exec(
        TAILSCALE_BIN,
        f"--socket={paths.TS_SOCKET}",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError as exc:
        proc.kill()
        raise TailscaleError(f"tailscale {args[0]}: timed out") from exc
    if proc.returncode != 0:
        raise TailscaleError(f"tailscale {args[0]}: {(err or out).decode().strip()}")
    return out.decode()


def available() -> bool:
    return paths.TS_SOCKET.exists()


async def status() -> dict:
    return json.loads(await run("status", "--json", timeout=15))


def _route_flags(routes: list[str], exit_node: bool) -> list[str]:
    return [f"--advertise-routes={','.join(routes)}", f"--advertise-exit-node={'true' if exit_node else 'false'}"]


async def up(login_server: str, authkey: str, routes: list[str], exit_node: bool) -> None:
    await run(
        "up",
        f"--login-server={login_server}",
        f"--auth-key={authkey}",
        f"--hostname={HOSTNAME}",
        "--accept-dns=false",
        "--accept-routes=false",
        "--reset",
        *_route_flags(routes, exit_node),
        timeout=90,
    )


async def set_routes(routes: list[str], exit_node: bool) -> None:
    await run("set", *_route_flags(routes, exit_node))
