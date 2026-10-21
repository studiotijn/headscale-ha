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
