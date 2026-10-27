"""Pass Headscale's log through and note browser sign-ins that wait for approval.

Headscale keeps pending registrations only in memory and has no command to list
them, but it logs every new one ("starting node registration using auth id: …").
The Headscale run script pipes the server log through this module. Every line is
written to stdout unchanged (the app log); a registration line also appends
``{"id": …, "ts": …}`` to ``paths.PENDING``, which the panel shows.

This must never stop reading: if it exits, Headscale's next log write fails.
"""

from __future__ import annotations

import contextlib
import json
import re
import sys
import time

from . import paths

ANSI = re.compile(rb"\x1b\[[0-9;]*m")
REGISTRATION = re.compile(rb"starting node registration using auth id: ([A-Za-z0-9_-]{6,128})")
MAX_LINES = 500  # the file lives in /run; keep it small


def auth_id(line: bytes) -> str | None:
    match = REGISTRATION.search(ANSI.sub(b"", line))
    return match.group(1).decode() if match else None


def record(auth: str, now: float | None = None) -> None:
    path = paths.PENDING
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines = [*lines[-(MAX_LINES - 1) :], json.dumps({"id": auth, "ts": int(now or time.time())})]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    out = sys.stdout.buffer
    for line in sys.stdin.buffer:
        with contextlib.suppress(OSError):
            out.write(line)
            out.flush()
        try:
            found = auth_id(line)
            if found:
                record(found)
        except Exception as exc:  # keep passing the log through
            with contextlib.suppress(OSError):
                out.write(f"[hsha] could not note a pending sign-in: {exc}\n".encode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
