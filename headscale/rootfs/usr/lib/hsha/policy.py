"""Initial ACL policy (seeded once; afterwards edit it in Headplane)."""

from __future__ import annotations

import json

ROUTER_TAG = "tag:homerouter"


def initial_policy(admin_user: str, lan_routes: list[str], exit_node: bool) -> str:
    """A safe starting point.

    * admins reach every tailnet device, the home LAN and (optionally) the internet via the exit node
    * other users only reach their own devices
    * the app's subnet router is tagged and its routes are auto-approved
    """
    admin = f"{admin_user}@"
    routes = sorted(set(lan_routes))
    acls = [
        {"action": "accept", "src": ["group:admins"], "dst": ["*:*"]},
        {"action": "accept", "src": ["autogroup:member"], "dst": ["autogroup:self:*"]},
    ]
    if routes:
        acls.append({"action": "accept", "src": ["group:admins"], "dst": [f"{r}:*" for r in routes]})
    if exit_node:
        acls.append({"action": "accept", "src": ["group:admins"], "dst": ["autogroup:internet:*"]})

    policy = {
        "groups": {"group:admins": [admin]},
        "tagOwners": {ROUTER_TAG: ["group:admins"]},
        "autoApprovers": {
            "routes": {r: [ROUTER_TAG] for r in routes},
            "exitNode": [ROUTER_TAG] if exit_node else [],
        },
        "acls": acls,
    }
    header = (
        "// Initial policy created by the Headscale app. Edit it in Headplane (Access Control).\n"
        "// The app never overwrites an existing policy.\n"
    )
    return header + json.dumps(policy, indent=2) + "\n"


SHARE_PREFIX = "hsha-"


def strip_hujson(text: str) -> str:
    """HuJSON (JSON with comments and trailing commas) -> JSON."""
    out = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
        else:
            out.append(c)
            i += 1
    cleaned = "".join(out)
    # Trailing commas before } or ] (outside strings: strings no longer contain comments here).
    result, in_str, i = [], False, 0
    while i < len(cleaned):
        c = cleaned[i]
        if in_str:
            result.append(c)
            if c == "\\" and i + 1 < len(cleaned):
                result.append(cleaned[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            result.append(c)
        elif c == ",":
            j = i + 1
            while j < len(cleaned) and cleaned[j] in " \t\r\n":
                j += 1
            if j < len(cleaned) and cleaned[j] in "}]":
                i += 1
                continue
            result.append(c)
        else:
            result.append(c)
        i += 1
    return "".join(result)


def apply_shares(policy: dict, shared: list[dict]) -> dict:
    """Make exactly the shared services reachable for every tailnet user.

    Managed entries use host aliases starting with ``hsha-``; everything else in the
    policy is left alone.
    """
    hosts = {k: v for k, v in (policy.get("hosts") or {}).items() if not k.startswith(SHARE_PREFIX)}
    acls = [
        a
        for a in (policy.get("acls") or [])
        if not (a.get("dst") and all(str(d).startswith(SHARE_PREFIX) for d in a["dst"]))
    ]
    for svc in shared:
        alias = f"{SHARE_PREFIX}{svc['slug']}"
        hosts[alias] = f"{svc['ip']}/32"
        ports = ",".join(str(p) for p in svc.get("ports") or []) or "*"
        acls.append({"action": "accept", "src": ["autogroup:member"], "dst": [f"{alias}:{ports}"]})
    policy = dict(policy)
    if hosts:
        policy["hosts"] = hosts
    else:
        policy.pop("hosts", None)
    policy["acls"] = acls
    return policy


def dump(policy: dict) -> str:
    return (
        "// Managed by the Headscale app and Headplane. Entries named hsha-* are shares made in\n"
        "// the app's Home network tab; edit those there.\n" + json.dumps(policy, indent=2) + "\n"
    )
