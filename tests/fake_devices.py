"""Fake home devices for testing the Home network assistants (needs root for ports < 1024).

Usage: python tests/fake_devices.py [--base 127.0.0]
  .20 Plex       HTTP 32400 (/identity)
  .21 Prusa      HTTP 80 (PrusaLink page) + TCP 554 (RTSP)
  .22 UniFi OS   HTTPS-ish TCP 443 + TCP 7441 + TCP 7447
"""

from __future__ import annotations

import argparse
import asyncio

from aiohttp import web


async def tcp_listener(ip: str, port: int) -> None:
    async def handle(reader, writer):
        writer.close()

    await asyncio.start_server(handle, ip, port)


async def http_app(ip: str, port: int, routes: dict[str, tuple[str, str, dict]]) -> None:
    app = web.Application()
    for path, (body, ctype, headers) in routes.items():

        async def handler(_request, body=body, ctype=ctype, headers=headers):
            return web.Response(text=body, content_type=ctype, headers=headers)

        app.router.add_get(path, handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, ip, port).start()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="127.0.0")
    b = ap.parse_args().base
    plex, prusa, unifi = f"{b}.20", f"{b}.21", f"{b}.22"
    await http_app(
        plex,
        32400,
        {
            "/identity": (
                '<?xml version="1.0"?><MediaContainer size="0" claimed="1" '
                'machineIdentifier="abc123" version="1.41.9.1234"></MediaContainer>',
                "text/xml",
                {},
            ),
        },
    )
    await http_app(
        prusa,
        80,
        {"/": ("<html><title>PrusaLink</title><body>Prusa MK4</body></html>", "text/html", {"Server": "PrusaLink"})},
    )
    await tcp_listener(prusa, 554)
    await http_app(unifi, 443, {"/": ("<html><title>UniFi OS</title></html>", "text/html", {})})
    for port in (7441, 7447):
        await tcp_listener(unifi, port)
    print(f"fake devices: plex {plex}, prusa {prusa}, unifi {unifi}", flush=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
