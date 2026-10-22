"""Take over the data of a previous installation of this app from another repository.

Home Assistant derives an app's slug from its repository URL. Adding the same repository
under another URL (e.g. without an access token) gives a new slug and an empty /data.
On the first start, this module finds the other Headscale installation, makes a temporary
partial backup of it through the Supervisor, copies its /data and options and removes the
backup again. Headscale keeps its keys and database, so no device has to sign in again.
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

from . import paths, supervisor

log = logging.getLogger("hsha.migrate")
MARKER = paths.DATA / "hsha" / "migrated.json"


def _fresh() -> bool:
    """No Headscale database and no app state yet: a new installation."""
    return not (paths.HS_DIR / "db.sqlite").exists() and not paths.STATE.exists() and not MARKER.exists()


def _previous(own_slug: str) -> dict | None:
    data = supervisor._get("/addons") or {}
    for app in data.get("addons", []):
        slug = str(app.get("slug", ""))
        if slug != own_slug and slug.endswith("_headscale") and app.get("installed", True):
            return app
    return None


def _download(backup: str) -> bytes:
    req = urllib.request.Request(
        f"{supervisor.SUPERVISOR}/backups/{backup}/download",
        headers={"Authorization": f"Bearer {os.environ['SUPERVISOR_TOKEN']}"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return resp.read()


def _extract(outer: bytes, slug: str, target: Path) -> dict:
    """Unpack data/ of the app from a Supervisor backup into target; return its addon.json."""
    with tarfile.open(fileobj=io.BytesIO(outer)) as tar:
        member = next(m for m in tar.getmembers() if Path(m.name).name in (f"{slug}.tar.gz", f"{slug}.tar"))
        inner = tar.extractfile(member).read()
    meta: dict = {}
    with tarfile.open(fileobj=io.BytesIO(inner)) as tar:
        for m in tar.getmembers():
            name = m.name.lstrip("./")
            if name == "addon.json":
                meta = json.loads(tar.extractfile(m).read())
                continue
            if not name.startswith("data/") or name == "data/":
                continue
            rel = Path(name[len("data/") :])
            if rel.is_absolute() or ".." in rel.parts:
                continue
            dest = target / rel
            if m.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(m) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
                os.chmod(dest, m.mode & 0o777)
            elif m.issym():
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    os.symlink(m.linkname, dest)
    return meta


def migrate() -> bool:
    if not supervisor.available() or not _fresh():
        return False
    own = supervisor.self_info().get("slug")
    prev = _previous(own) if own else None
    if not prev:
        return False
    slug = prev["slug"]
    if prev.get("state") == "started":
        raise RuntimeError(f"previous installation {slug} is still running: stop it, then start this app again")
    log.info("Taking over the data of the previous installation %s", slug)
    backup = supervisor._post(
        "/backups/new/partial",
        {"name": f"Headscale migration {time.strftime('%Y-%m-%d %H:%M')}", "addons": [slug], "homeassistant": False},
        timeout=600,
    ).get("slug")
    try:
        with tempfile.TemporaryDirectory(dir=paths.DATA) as tmp:
            meta = _extract(_download(backup), slug, Path(tmp))
            for item in Path(tmp).iterdir():
                if item.name == "options.json":
                    continue  # written by the Supervisor from this app's own options
                dest = paths.DATA / item.name
                if dest.is_dir():
                    shutil.rmtree(dest)
                elif dest.exists():
                    dest.unlink()
                shutil.move(str(item), dest)
    finally:
        try:
            _delete_backup(backup)
        except Exception as exc:
            log.warning("Could not remove the temporary backup %s: %s", backup, exc)
    options = (meta.get("user") or {}).get("options") or meta.get("options")
    if isinstance(options, dict) and options:
        supervisor.save_options(options)
        # This start already uses them; the Supervisor writes them again on the next start.
        from .store import write_json

        write_json(paths.OPTIONS, options, 0o600)
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text(json.dumps({"from": slug, "time": int(time.time())}))
    log.info("Migration from %s done; you can uninstall that app now", slug)
    return True


def _delete_backup(backup: str) -> None:
    req = urllib.request.Request(
        f"{supervisor.SUPERVISOR}/backups/{backup}",
        method="DELETE",
        headers={"Authorization": f"Bearer {os.environ['SUPERVISOR_TOKEN']}"},
    )
    with urllib.request.urlopen(req, timeout=60):
        pass


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[hsha] %(levelname)s %(message)s")
    try:
        migrate()
    except Exception as exc:
        # Don't start with an empty database next to the old one: that would make every
        # device sign in again. Stop here; the next start tries again.
        log.error("Taking over the previous installation failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
