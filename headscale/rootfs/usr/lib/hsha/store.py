"""Small JSON helpers with atomic writes."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def write_text_atomic(path: Path, text: str, mode: int = 0o640) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def write_json(path: Path, data: Any, mode: int = 0o640) -> None:
    write_text_atomic(path, json.dumps(data, indent=2, sort_keys=False) + "\n", mode)


def load_state() -> dict:
    from . import paths

    state = read_json(paths.STATE, {})
    state.setdefault("printers", [])
    state.setdefault("services", [])
    return state


def save_state(state: dict) -> None:
    from . import paths

    write_json(paths.STATE, state, 0o600)
