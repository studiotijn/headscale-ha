"""A fake IPP printer for tests: answers Get-Printer-Attributes and announces itself via mDNS.

Usage: python tests/fake_printer.py [--port 18631] [--ip 127.0.0.1] [--no-mdns]
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import struct

from aiohttp import web


def attr(tag: int, name: str, value: bytes) -> bytes:
    nb = name.encode()
    return struct.pack(">BH", tag, len(nb)) + nb + struct.pack(">H", len(value)) + value


def response(request_id: int) -> bytes:
    body = struct.pack(">BBHI", 2, 0, 0x0000, request_id)
    body += b"\x01" + attr(0x47, "attributes-charset", b"utf-8") + attr(0x48, "attributes-natural-language", b"en")
    body += b"\x04"
    body += attr(0x42, "printer-name", b"Fake-Printer")
    body += attr(0x41, "printer-make-and-model", b"Acme LaserJet 9000")
    body += attr(0x23, "printer-state", struct.pack(">i", 3))
    body += attr(0x41, "printer-state-message", b"Ready")
    body += attr(0x44, "printer-state-reasons", b"none")
    body += b"\x03"
    return body


async def handle(request: web.Request) -> web.Response:
    data = await request.read()
    op = struct.unpack(">H", data[2:4])[0]
    req_id = struct.unpack(">I", data[4:8])[0]
    assert op == 0x000B, f"unexpected op {op:#x}"
    request.app["requests"] += 1
    return web.Response(body=response(req_id), content_type="application/ipp")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=18631)
    ap.add_argument("--ip", default="127.0.0.1")
    ap.add_argument("--no-mdns", action="store_true")
    args = ap.parse_args()

    app = web.Application()
    app["requests"] = 0
    app.router.add_post("/ipp/print", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, args.ip, args.port).start()

    azc = None
    if not args.no_mdns:
        from zeroconf import ServiceInfo
        from zeroconf.asyncio import AsyncZeroconf

        azc = AsyncZeroconf()
        info = ServiceInfo(
            "_ipp._tcp.local.",
            "Fake Office Printer._ipp._tcp.local.",
            addresses=[socket.inet_aton(args.ip)],
            port=args.port,
            properties={"rp": "ipp/print", "ty": "Acme LaserJet 9000", "note": "Study"},
            server="fake-printer.local.",
        )
        await azc.async_register_service(info, allow_name_change=True)
    print(f"fake printer on {args.ip}:{args.port}", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        if azc:
            await azc.async_close()


if __name__ == "__main__":
    asyncio.run(main())
