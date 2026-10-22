"""Append-only audit log of multi-tenant changes and applied policies."""

from __future__ import annotations

import json
import os
import time

from . import paths
from .store import write_text_atomic

KEEP_POLICIES = 50


def record(action: str, actor: str | None, summary: str, **extra) -> dict:
    entry = {"ts": int(time.time()), "actor": actor or "system", "action": action, "summary": summary, **extra}
    paths.AUDIT.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(paths.AUDIT, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def recent(limit: int = 100) -> list[dict]:
    try:
        lines = paths.AUDIT.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in reversed(lines[-limit:]):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def save_policy(name: str, text: str) -> None:
    """Keep a copy of every applied policy (and the one replaced by the first activation)."""
    paths.POLICY_HISTORY.mkdir(parents=True, exist_ok=True)
    write_text_atomic(paths.POLICY_HISTORY / f"{name}.hujson", text, 0o600)
    files = sorted(
        (p for p in paths.POLICY_HISTORY.glob("*.hujson") if not p.name.startswith("pre-")),
        key=lambda p: p.stat().st_mtime,
    )
    for old in files[:-KEEP_POLICIES]:
        old.unlink(missing_ok=True)
