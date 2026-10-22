"""Small DNS server that publishes the added printers via unicast DNS-SD ("wide-area Bonjour").

iPhones, iPads and Macs find AirPrint printers through mDNS on the local network
only. They also browse the DNS search domains for DNS-SD records, and that works
across a VPN. Headscale gives the devices `printer_domain` as search domain and
sends queries for it (split DNS) to the subnet router of this app; Tailscale's
userspace networking delivers them to 127.0.0.1:53 on the Home Assistant host.

Two modes, chosen automatically:
* adguard: something (AdGuard Home) already serves 127.0.0.1:53. This server
  listens on 127.0.0.1:PORT and AdGuard forwards the printer domain to it with
  the upstream rule `[/printers.home.arpa/]127.0.0.1:PORT`.
* direct: port 53 is free. This server listens on 127.0.0.1:53 itself, answers
  the printer domain and forwards everything else to the host's resolver.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import socket
import sys

from dnslib import PTR, QTYPE, RCODE, RR, SOA, SRV, TXT, A, DNSHeader, DNSLabel, DNSRecord

from . import paths
from .options import load
from .store import load_state, read_json, write_json

log = logging.getLogger("hsha.dnssd")

ALT_PORT = int(os.environ.get("HSHA_DNSSD_PORT", "15353"))
TTL = 60
URF_DEFAULT = "CP1,IS1,MT1-2-3-4-5-6-8-10-11-12-13,RS300,SRGB24,V1.4,W8,DM1"


def _label(text: str) -> str:
    """DNS-SD instance names may contain spaces and UTF-8, but no dots; max 63 bytes."""
    text = text.replace(".", " ").strip() or "Printer"
    raw = text.encode()[:63]
    return raw.decode("utf-8", "ignore")


def default_txt(p: dict) -> dict:
    model = p.get("model") or p.get("name") or "Printer"
    return {
        "txtvers": "1",
        "qtotal": "1",
        "rp": p.get("resource") or "ipp/print",
        "ty": model,
        "product": f"({model})",
        "pdl": "application/pdf,image/urf,image/jpeg",
        "URF": URF_DEFAULT,
        "Color": "T",
        "Duplex": "T",
        "kind": "document",
    }


def key(name) -> tuple[bytes, ...]:
    """Case-insensitive lookup key for a DNS name (str or DNSLabel)."""
    label = name if isinstance(name, DNSLabel) else DNSLabel(str(name))
    return tuple(part.lower() for part in label.label)


class Zone:
    """All records for the printer domain, built from the app state."""

    def __init__(self, domain: str):
        self.domain = domain.strip(".").lower()
        self.records: dict[tuple[tuple[bytes, ...], int], list[RR]] = {}

    def _add(self, name: str, rtype: int, rdata) -> None:
        self.records.setdefault((key(name), rtype), []).append(RR(name, rtype, rdata=rdata, ttl=TTL))

    def build(self, printers: list[dict]) -> Zone:
        d = self.domain
        self.records.clear()
        for browse in ("b", "db", "lb"):
            self._add(f"{browse}._dns-sd._udp.{d}", QTYPE.PTR, PTR(f"{d}."))
        for p in printers:
            if p.get("protocol") not in ("ipp", "ipps"):
                continue  # AirPrint needs IPP
            service = "_ipps._tcp" if p["protocol"] == "ipps" else "_ipp._tcp"
            instance = f"{_label(p['name'])}.{service}.{d}"
            host = f"{p['slug']}.{d}"
            self._add(f"{service}.{d}", QTYPE.PTR, PTR(f"{instance}."))
            self._add(f"_universal._sub.{service}.{d}", QTYPE.PTR, PTR(f"{instance}."))
            self._add(f"_print._sub.{service}.{d}", QTYPE.PTR, PTR(f"{instance}."))
            self._add(instance, QTYPE.SRV, SRV(priority=0, weight=0, port=int(p["port"]), target=f"{host}."))
            txt = {**default_txt(p), **(p.get("txt") or {})}
            self._add(instance, QTYPE.TXT, TXT([f"{k}={v}".encode()[:255] for k, v in txt.items()]))
            self._add(host, QTYPE.A, A(p["ip"]))
        self._add(d, QTYPE.SOA, SOA(f"ns.{d}.", f"hostmaster.{d}.", (1, 3600, 600, 86400, TTL)))
        return self

    def inside(self, name) -> bool:
        k, d = key(name), key(self.domain)
        return k[len(k) - len(d) :] == d

    def answer(self, request: DNSRecord) -> DNSRecord:
        reply = request.reply()
        q = request.q
        qkey = key(q.qname)
        if q.qtype == QTYPE.ANY:
            hits = [rr for (name, _), rrs in self.records.items() if name == qkey for rr in rrs]
        else:
            hits = list(self.records.get((qkey, q.qtype), []))
        for rr in hits:
            reply.add_answer(rr)
        # Helpful extras: SRV/TXT/A for PTR answers, A for SRV answers.
        for rr in hits:
            if rr.rtype == QTYPE.PTR:
                target = key(rr.rdata.label)
                for extra in self.records.get((target, QTYPE.SRV), []) + self.records.get((target, QTYPE.TXT), []):
                    reply.add_ar(extra)
                    if extra.rtype == QTYPE.SRV:
                        for a in self.records.get((key(extra.rdata.target), QTYPE.A), []):
                            reply.add_ar(a)
            elif rr.rtype == QTYPE.SRV:
                for a in self.records.get((key(rr.rdata.target), QTYPE.A), []):
                    reply.add_ar(a)
        if not hits:
            if not any(name == qkey for (name, _) in self.records):
                reply.header.rcode = RCODE.NXDOMAIN
            reply.add_auth(self.records[(key(self.domain), QTYPE.SOA)][0])
        reply.header.aa = 1
        return reply


def system_resolver() -> str:
    try:
        with open("/etc/resolv.conf", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "nameserver" and not parts[1].startswith("127."):
                    return parts[1]
    except OSError:
        pass
    return "1.1.1.1"


class Server:
    def __init__(self, domain: str, forward_to: str | None):
        self.domain = domain
        self.forward_to = forward_to
        self.zone = Zone(domain)
        self._mtime = None

    def refresh(self) -> None:
        try:
            mtime = paths.STATE.stat().st_mtime
        except OSError:
            mtime = 0
        if mtime != self._mtime:
            self._mtime = mtime
            self.zone.build(load_state().get("printers", []))

    async def handle(self, data: bytes) -> bytes | None:
        try:
            request = DNSRecord.parse(data)
        except Exception:
            return None
        self.refresh()
        if self.zone.inside(request.q.qname):
            return self.zone.answer(request).pack()
        if self.forward_to:
            return await self.forward(data)
        reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, ra=1, rcode=RCODE.REFUSED), q=request.q)
        return reply.pack()

    async def forward(self, data: bytes) -> bytes | None:
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        try:
            await loop.sock_sendto(sock, data, (self.forward_to, 53))
            resp, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), 4)
            return resp
        except (OSError, TimeoutError):
            return None
        finally:
            sock.close()


class _Udp(asyncio.DatagramProtocol):
    def __init__(self, server: Server):
        self.server = server
        self.tasks: set[asyncio.Task] = set()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        async def reply():
            try:
                resp = await self.server.handle(data)
            except Exception:
                log.exception("DNS query failed")
                return
            if resp:
                if len(resp) > 1232:
                    with contextlib.suppress(Exception):
                        rec = DNSRecord.parse(resp)
                        rec.header.tc = 1
                        rec.rr, rec.auth, rec.ar = [], [], []
                        resp = rec.pack()
                self.transport.sendto(resp, addr)

        task = asyncio.ensure_future(reply())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


async def _tcp(server: Server, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    with contextlib.suppress(Exception):
        while True:
            head = await asyncio.wait_for(reader.readexactly(2), 10)
            data = await reader.readexactly(int.from_bytes(head, "big"))
            resp = await server.handle(data)
            if not resp:
                break
            writer.write(len(resp).to_bytes(2, "big") + resp)
            await writer.drain()
    writer.close()


def port_free(port: int) -> bool:
    for kind in (socket.SOCK_DGRAM, socket.SOCK_STREAM):
        s = socket.socket(socket.AF_INET, kind)
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            return False
        finally:
            s.close()
    return True


async def serve() -> None:
    opts = load()
    domain = opts.printer_domain
    if port_free(53):
        mode, port, forward_to = "direct", 53, system_resolver()
    else:
        mode, port, forward_to = "adguard", ALT_PORT, None
    server = Server(domain, forward_to)
    server.refresh()
    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(lambda: _Udp(server), local_addr=("127.0.0.1", port))
    await asyncio.start_server(lambda r, w: _tcp(server, r, w), "127.0.0.1", port)
    runtime = read_json(paths.RUNTIME, {})
    runtime["printer_dns"] = {"mode": mode, "port": port, "domain": domain, "forward_to": forward_to}
    write_json(paths.RUNTIME, runtime, 0o644)
    log.info("Printer DNS for %s on 127.0.0.1:%d (%s mode)", domain, port, mode)
    if mode == "adguard":
        log.info("Add this upstream rule in AdGuard Home: [/%s/]127.0.0.1:%d", domain, port)
    await asyncio.Event().wait()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[hsha] %(message)s")
    asyncio.run(serve())
    return 0


if __name__ == "__main__":
    sys.exit(main())


def lookup(name: str, qtype: str, server: str = "127.0.0.1", port: int = 53, timeout: float = 3) -> dict:
    """Query a DNS server; used by the setup wizard to test the AirPrint chain."""
    q = DNSRecord.question(name, qtype)
    try:
        raw = q.send(server, port, timeout=timeout)
    except Exception as exc:
        return {"ok": False, "error": str(exc) or "timeout"}
    reply = DNSRecord.parse(raw)
    answers = [str(rr.rdata) for rr in reply.rr]
    return {"ok": bool(answers), "rcode": RCODE.get(reply.header.rcode), "answers": answers}
