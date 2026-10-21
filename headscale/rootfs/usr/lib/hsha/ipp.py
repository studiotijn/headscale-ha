"""Minimal IPP client: Get-Printer-Attributes, enough to check a printer is reachable and idle."""

from __future__ import annotations

import struct

import aiohttp

TAG_OPERATION = 0x01
TAG_END = 0x03
TAG_INTEGER = 0x21
TAG_BOOLEAN = 0x22
TAG_ENUM = 0x23
TAG_URI = 0x45
TAG_KEYWORD = 0x44
TAG_CHARSET = 0x47
TAG_LANGUAGE = 0x48

PRINTER_STATES = {3: "idle", 4: "processing", 5: "stopped"}

REQUESTED = [
    "printer-name",
    "printer-make-and-model",
    "printer-state",
    "printer-state-message",
    "printer-state-reasons",
    "printer-info",
    "printer-location",
]


def _attr(tag: int, name: str, value: bytes) -> bytes:
    nb = name.encode()
    return struct.pack(">BH", tag, len(nb)) + nb + struct.pack(">H", len(value)) + value


def encode_get_printer_attributes(printer_uri: str, request_id: int = 1) -> bytes:
    body = struct.pack(">BBHI", 2, 0, 0x000B, request_id)
    body += bytes([TAG_OPERATION])
    body += _attr(TAG_CHARSET, "attributes-charset", b"utf-8")
    body += _attr(TAG_LANGUAGE, "attributes-natural-language", b"en")
    body += _attr(TAG_URI, "printer-uri", printer_uri.encode())
    body += _attr(TAG_KEYWORD, "requested-attributes", REQUESTED[0].encode())
    for extra in REQUESTED[1:]:
        body += _attr(TAG_KEYWORD, "", extra.encode())
    body += bytes([TAG_END])
    return body


def decode_response(data: bytes) -> tuple[int, dict[str, list]]:
    if len(data) < 8:
        raise ValueError("IPP response too short")
    status = struct.unpack(">H", data[2:4])[0]
    attrs: dict[str, list] = {}
    pos = 8
    last_name = None
    while pos < len(data):
        tag = data[pos]
        pos += 1
        if tag == TAG_END:
            break
        if tag <= 0x0F:  # delimiter: next attribute group
            continue
        (name_len,) = struct.unpack(">H", data[pos : pos + 2])
        pos += 2
        name = data[pos : pos + name_len].decode("utf-8", "replace")
        pos += name_len
        (value_len,) = struct.unpack(">H", data[pos : pos + 2])
        pos += 2
        raw = data[pos : pos + value_len]
        pos += value_len
        if name:
            last_name = name
        if last_name is None:
            continue
        if tag in (TAG_INTEGER, TAG_ENUM) and value_len == 4:
            value = struct.unpack(">i", raw)[0]
        elif tag == TAG_BOOLEAN and value_len == 1:
            value = bool(raw[0])
        elif 0x40 <= tag <= 0x4A or 0x30 <= tag <= 0x37:
            value = raw.decode("utf-8", "replace")
        else:
            value = raw.hex()
        attrs.setdefault(last_name, []).append(value)
    return status, attrs


async def get_printer_attributes(
    host: str, port: int = 631, resource: str = "ipp/print", tls: bool = False, timeout: float = 8
) -> dict:
    resource = resource.lstrip("/")
    scheme_ipp = "ipps" if tls else "ipp"
    printer_uri = f"{scheme_ipp}://{host}:{port}/{resource}"
    http_url = f"{'https' if tls else 'http'}://{host}:{port}/{resource}"
    payload = encode_get_printer_attributes(printer_uri)
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with (
        aiohttp.ClientSession(timeout=client_timeout) as session,
        session.post(http_url, data=payload, headers={"Content-Type": "application/ipp"}, ssl=False) as resp,
    ):
        if resp.status != 200:
            raise ValueError(f"HTTP {resp.status} from {http_url}")
        status, attrs = decode_response(await resp.read())
    if status >= 0x0400:
        raise ValueError(f"IPP status 0x{status:04x}")

    def first(key: str):
        values = attrs.get(key)
        return values[0] if values else None

    state = first("printer-state")
    return {
        "uri": printer_uri,
        "name": first("printer-name"),
        "model": first("printer-make-and-model"),
        "state": PRINTER_STATES.get(state, state),
        "message": first("printer-state-message"),
        "reasons": [r for r in attrs.get("printer-state-reasons", []) if r != "none"],
        "location": first("printer-location"),
    }
