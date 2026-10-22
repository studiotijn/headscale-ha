"""Unit tests for the multi-tenant model and policy generator (run: pytest tests/)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "headscale/rootfs/usr/lib"))

from hsha import policygen as pg
from hsha import tenancy as tn


def node(nid, name, user=None, tags=None, routes=None):
    return {
        "id": nid,
        "name": name,
        "given_name": name,
        "user": {"name": user or "tagged-devices"},
        "tags": tags or [],
        "ip_addresses": [f"100.64.0.{nid}", f"fd7a:115c:a1e0::{nid}"],
        "approved_routes": routes or [],
        "available_routes": routes or [],
    }


NODES = [
    node(1, "pc-thuis", "admin"),
    node(2, "phone", "admin"),
    node(3, "ha-router", tags=["tag:homerouter"], routes=["192.168.1.0/24"]),
    node(4, "pc-werk", "work"),
    node(5, "laptop-klant", "anna"),
    node(6, "edge-loc01", tags=["tag:project-loc01-edge"], routes=["10.81.1.0/24"]),
    node(7, "edge-loc02", tags=["tag:project-loc02-edge"]),
]


def build(**extra_conn):
    m = tn.default_model("admin")
    assert [d["name"] for d in m["domains"]] == ["Private", "Work", "Project"]
    m, _ = tn.apply_change(m, "domain", "update", {**m["domains"][1], "users": "work"})
    m, _ = tn.apply_change(m, "domain", "update", {**m["domains"][2], "users": "anna"})
    for n in (1, 2):
        m, _ = tn.apply_change(
            m,
            "location",
            "create",
            {
                "domain": "project",
                "number": n,
                "name": f"Locatie {n}",
                "local_subnet": "192.168.1.0/24",
                "lan_iface": "eth1",
            },
        )
    m, _ = tn.apply_change(
        m, "device", "create", {"id": "cam1", "location": "loc01", "name": "L1", "ip": "192.168.1.10"}
    )
    m, _ = tn.apply_change(
        m, "device", "create", {"id": "cam2", "location": "loc02", "name": "L2", "ip": "192.168.1.10"}
    )
    conns = [
        {"name": "thuis-cam", "src": "node:1", "dst": "dev:cam1", "ports": "tcp:80, tcp:8010"},
        {"name": "werk-loc01", "src": "node:4", "dst": "loc:loc01", "ports": "tcp:80"},
        {"name": "klant-ssh", "src": "domain:project", "dst": "edge:loc01", "ports": "tcp:22"},
    ]
    for c in conns:
        m, _ = tn.apply_change(m, "connection", "create", c)
    return m


def ctx(**kw):
    return pg.Context("admin", NODES, home_routes=["192.168.1.0/24"], **kw)


def test_vpn_ip_keeps_host_part():
    m = build()
    loc = tn.location(m, "loc02")
    assert loc["vpn_subnet"] == "10.81.2.0/24"
    assert str(tn.vpn_ip(loc, "192.168.1.10")) == "10.81.2.10"
    with pytest.raises(tn.ModelError):
        tn.vpn_ip(loc, "192.168.2.10")


def test_overlapping_vpn_subnets_rejected():
    m = build()
    with pytest.raises(tn.ModelError, match="overlaps"):
        new, _ = tn.apply_change(
            m,
            "location",
            "create",
            {
                "domain": "project",
                "number": 3,
                "name": "x",
                "local_subnet": "192.168.1.0/24",
                "vpn_subnet": "10.81.1.0/24",
                "lan_iface": "eth1",
            },
        )
        tn.validate(new, NODES)
    with pytest.raises(tn.ModelError, match="home network"):
        new, _ = tn.apply_change(
            m,
            "location",
            "create",
            {
                "domain": "project",
                "number": 4,
                "name": "y",
                "local_subnet": "192.168.1.0/24",
                "vpn_subnet": "192.168.1.0/24",
                "lan_iface": "eth1",
            },
        )
        tn.validate(new, NODES, ["192.168.1.0/24"])


@pytest.mark.parametrize(
    ("src", "dst", "message"),
    [
        ("domain:project", "node:1", "can never start connections"),
        ("node:5", "node:4", "can never start connections"),
        ("node:6", "dev:cam1", "Edgebox can never be a source"),
        ("dev:cam1", "node:1", "can never be a source"),
    ],
)
def test_forbidden_connections(src, dst, message):
    m = build()
    new, _ = tn.apply_change(m, "connection", "create", {"src": src, "dst": dst, "ports": "*"})
    with pytest.raises(tn.ModelError, match=message):
        tn.validate(new, NODES)


def test_ports_parsing():
    assert tn.parse_ports("tcp:22, udp:53 8000") == ["tcp:22", "udp:53", "8000"]
    assert tn.parse_ports(["ICMP", "*"]) == ["icmp:*", "*"]
    for bad in ("tcp:0", "tcp:70000", "ftp:21", "tcp:10-5", ""):
        with pytest.raises(tn.ModelError):
            tn.parse_ports(bad)


def test_node_domains():
    m = build()
    doms = {n["id"]: tn.node_domain(m, n) for n in NODES}
    assert doms == {1: "private", 2: "private", 3: "private", 4: "work", 5: "project", 6: "project", 7: "project"}
    assert tn.node_location(m, NODES[5]) == "loc01"
    assert tn.allowed_routes(m, NODES[5], []) == ["10.81.1.0/24"]
    assert tn.allowed_routes(m, NODES[2], ["192.168.1.0/24"]) == ["192.168.1.0/24"]


def test_policy_is_deterministic_and_closed():
    m = build()
    a, b = pg.generate(m, ctx()), pg.generate(m, ctx())
    assert a["sha256"] == b["sha256"] and a["text"] == b["text"]
    pol = a["policy"]
    srcs = {s for g in pol["grants"] for s in g["src"]}
    # Nothing at a client site is ever a source.
    assert not any(s.startswith(("tag:project", "loc-", "dev-")) for s in srcs)
    assert "node-6" not in srcs and "node-7" not in srcs
    # No wildcard rules.
    assert all("*" not in g["src"] and "*" not in g["dst"] for g in pol["grants"])
    assert pol["autoApprovers"]["routes"]["10.81.1.0/24"] == ["tag:project-loc01-edge"]
    assert pol["hosts"]["dev-cam1"] == "10.81.1.10/32"


def test_policy_tests_cover_isolation():
    m = build()
    tests = pg.generate(m, ctx())["policy"]["tests"]
    by_src: dict[str, set] = {}
    for t in tests:
        by_src.setdefault(t["src"], set()).update(t.get("deny", []))
    assert "node-1:22" in by_src["node-6"]  # Edgebox loc01 -> pc-thuis
    assert "dev-cam2:22" in by_src["dev-cam1"]  # site -> other site
    assert "node-4:22" in by_src["node-1"]  # Private -> Work
    assert "node-1:22" in by_src["node-5"]  # client user -> Private
    accepts = {(t["src"], a) for t in tests for a in t.get("accept", [])}
    assert ("node-1", "dev-cam1:80") in accepts
    assert ("node-5", "node-6:22") in accepts


def test_disabled_connection_and_shares():
    m = build()
    c = next(x for x in m["connections"] if x["name"] == "thuis-cam")
    m, _ = tn.apply_change(m, "connection", "update", {**c, "enabled": False})
    r = pg.generate(m, ctx(shared_services=[{"slug": "plex", "ip": "192.168.1.20", "ports": [32400]}]))
    names = [g["#name"] for g in r["policy"]["grants"]]
    assert "thuis-cam" not in names
    share = next(g for g in r["policy"]["grants"] if g["#name"].startswith("Share"))
    assert share["src"] == ["group:dom-private"]  # never autogroup:member in this mode


def test_edge_nftables():
    m = build()
    text = pg.edge_nftables(m, "loc01", ctx())
    assert "dnat ip prefix to ip daddr map { 10.81.1.0/24 : 192.168.1.0/24 }" in text
    assert "policy drop;" in text
    assert "ip saddr 100.64.0.1 ip daddr 192.168.1.10 tcp dport { 80, 8010 } accept" in text
    assert "ip saddr 100.64.0.4 ip daddr 192.168.1.0/24 tcp dport 80 accept" in text
    assert "cam2" not in text and "10.81.2" not in text
    if shutil.which("nft"):
        res = subprocess.run(["nft", "-c", "-f", "-"], input=text, text=True, capture_output=True)
        assert res.returncode == 0, res.stderr


HEADSCALE = shutil.which("headscale")


@pytest.mark.skipif(not HEADSCALE, reason="headscale binary not installed")
def test_generated_policy_accepted_by_headscale(tmp_path):
    """Headscale 0.29 accepts the generated policy (grants, hosts, autoApprovers)."""
    m = build()
    r = pg.generate(m, ctx())
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        json.dumps(
            {
                "server_url": "http://127.0.0.1:1",
                "listen_addr": "127.0.0.1:0",
                "noise": {"private_key_path": str(tmp_path / "noise.key")},
                "prefixes": {"v4": "100.64.0.0/10", "v6": "fd7a:115c:a1e0::/48"},
                "database": {"type": "sqlite", "sqlite": {"path": str(tmp_path / "db.sqlite")}},
                "derp": {"server": {"enabled": False}, "urls": [], "paths": []},
                "dns": {"magic_dns": False, "override_local_dns": False},
                "policy": {"mode": "database"},
            }
        )
    )
    pol = tmp_path / "p.hujson"
    pol.write_text(json.dumps({k: v for k, v in r["policy"].items() if k != "tests"}))
    for user in ("admin", "work", "anna"):
        subprocess.run([HEADSCALE, "-c", str(cfg), "--force", "users", "create", user], capture_output=True)
    res = subprocess.run(
        [
            HEADSCALE,
            "-c",
            str(cfg),
            "--force",
            "policy",
            "check",
            "-f",
            str(pol),
            "--bypass-grpc-and-access-database-directly",
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr


def test_groups_users_and_profiles():
    m = build()
    m, _ = tn.apply_change(m, "domain", "update", {**tn.domain(m, "project"), "users": "anna, piet"})
    m, _ = tn.apply_change(
        m, "group", "create", {"id": "beheer", "name": "Beheerders", "members": ["node:1", "user:work"]}
    )
    m, _ = tn.apply_change(m, "group", "create", {"id": "cams", "name": "Cameras", "members": ["dev:cam1", "dev:cam2"]})
    m, _ = tn.apply_change(m, "profile", "create", {"name": "Camera web", "ports": "tcp:80, tcp:8010"})
    m, _ = tn.apply_change(
        m,
        "connection",
        "create",
        {
            "id": "g2g",
            "name": "Beheer naar Cameras",
            "src": ["group:beheer"],
            "dst": ["group:cams"],
            "ports": ["profile:camera-web", "profile:ssh"],
        },
    )
    m, _ = tn.apply_change(
        m,
        "connection",
        "create",
        {"id": "u2e", "name": "Piet", "src": "user:piet", "dst": "edge:loc02", "ports": "profile:ssh"},
    )
    tn.validate(m, NODES)
    r = pg.generate(m, ctx())
    g = next(x for x in r["policy"]["grants"] if x["#name"] == "Beheer naar Cameras")
    assert g["src"] == ["node-1", "work@"]
    assert g["dst"] == ["dev-cam1", "dev-cam2"]
    assert g["ip"] == ["tcp:80", "tcp:8010", "tcp:22"]
    piet = next(x for x in r["policy"]["grants"] if x["#name"] == "Piet")
    assert piet["src"] == ["piet@"] and piet["dst"] == ["tag:project-loc02-edge"]
    nft2 = pg.edge_nftables(m, "loc02", ctx())
    assert "ip saddr { 100.64.0.1, 100.64.0.4 } ip daddr 192.168.1.10 tcp dport { 80, 8010, 22 } accept" in nft2

    m3, _ = tn.apply_change(m, "connection", "update", {**tn_conn(m, "g2g"), "dst": ["dev:cam2", "loc:loc02"]})
    nft3 = pg.edge_nftables(m3, "loc02", ctx())
    assert "ip daddr 192.168.1.0/24 tcp dport" in nft3 and "192.168.1.10," not in nft3  # host absorbed by subnet
    if shutil.which("nft"):
        for text in (nft2, nft3):
            res = subprocess.run(["nft", "-c", "-f", "-"], input=text, text=True, capture_output=True)
            assert res.returncode == 0, res.stderr

    # Editing a profile changes every connection that uses it.
    m, _ = tn.apply_change(m, "profile", "update", {"id": "camera-web", "name": "Camera web", "ports": "tcp:8010"})
    g = next(x for x in pg.generate(m, ctx())["policy"]["grants"] if x["#name"] == "Beheer naar Cameras")
    assert g["ip"] == ["tcp:8010", "tcp:22"]

    # In use: cannot delete; a group with a site device can never be a source.
    with pytest.raises(tn.ModelError, match="used by"):
        tn.apply_change(m, "group", "delete", {"id": "beheer"})
    with pytest.raises(tn.ModelError, match="used by"):
        tn.apply_change(m, "profile", "delete", {"id": "ssh"})
    bad, _ = tn.apply_change(m, "connection", "update", {**tn_conn(m, "g2g"), "src": ["group:cams"]})
    with pytest.raises(tn.ModelError, match="never start"):
        tn.validate(bad, NODES)
    # A group mixing a client user with Private, towards Private: refused.
    m2, _ = tn.apply_change(m, "group", "create", {"id": "mix", "name": "Mix", "members": ["user:anna", "node:1"]})
    bad, _ = tn.apply_change(m2, "connection", "create", {"src": "group:mix", "dst": "node:2", "ports": "*"})
    with pytest.raises(tn.ModelError, match="project domain"):
        tn.validate(bad, NODES)


def tn_conn(m, cid):
    return next(c for c in m["connections"] if c["id"] == cid)


def test_edit_in_place_and_cascade():
    m = build()
    c = next(x for x in m["connections"] if x["name"] == "thuis-cam")
    m, summary = tn.apply_change(m, "connection", "update", {**c, "dst": ["dev:cam1", "dev:cam2"], "ports": "tcp:80"})
    c2 = tn_conn(m, c["id"])
    assert c2["dst"] == ["dev:cam1", "dev:cam2"] and c2["ports"] == ["tcp:80"] and "updated" in summary
    m, _ = tn.apply_change(m, "location", "update", {**tn.location(m, "loc02"), "name": "Hengelo"})
    assert tn.location(m, "loc02")["name"] == "Hengelo" and tn.location(m, "loc02")["vpn_subnet"] == "10.81.2.0/24"
    m, _ = tn.apply_change(m, "device", "update", {**tn.device(m, "cam2"), "ip": "192.168.1.11"})
    assert pg.generate(m, ctx())["policy"]["hosts"]["dev-cam2"] == "10.81.2.11/32"
    # Deleting a location removes its devices from connections, but keeps the rest of the connection.
    m, _ = tn.apply_change(m, "location", "delete", {"id": "loc02"})
    assert tn_conn(m, c["id"])["dst"] == ["dev:cam1"]
    # Removing a user from a domain removes it from connections.
    m, _ = tn.apply_change(
        m, "connection", "create", {"id": "u", "src": "user:anna", "dst": "edge:loc01", "ports": "tcp:22"}
    )
    m, _ = tn.apply_change(m, "domain", "update", {**tn.domain(m, "project"), "users": ""})
    assert all(x["id"] != "u" for x in m["connections"])


def test_access_overview():
    m = build()
    by_id = {n["id"]: n for n in NODES}
    a = tn.access(m, "node:1", by_id)
    assert [x["name"] for x in a["outgoing"]] == ["thuis-cam"] and a["internal"] == ["private"]
    a = tn.access(m, "dev:cam1", by_id)
    assert sorted(x["name"] for x in a["incoming"]) == ["thuis-cam", "werk-loc01"]
    a = tn.access(m, "node:5", by_id)  # client user: via domain:project
    assert [x["name"] for x in a["outgoing"]] == ["klant-ssh"]


def test_old_connections_are_migrated(tmp_path, monkeypatch):
    from hsha import paths

    monkeypatch.setattr(paths, "TENANCY", tmp_path / "t.json")
    m = build()
    for c in m["connections"]:
        c["src"], c["dst"] = c["src"][0], c["dst"][0]
    m.pop("port_profiles")
    tn.save(m)
    loaded = tn.load("admin")
    assert all(isinstance(c["src"], list) for c in loaded["connections"])
    assert tn.profile(loaded, "ssh")["ports"] == ["tcp:22"]


def test_device_behind_a_router_gets_only_its_route():
    m = build()
    m, _ = tn.apply_change(
        m, "device", "create", {"id": "prn", "via": "node:4", "name": "Printer werk", "ip": "10.20.0.5"}
    )
    tn.validate(m, NODES)
    werk = NODES[3]
    assert tn.allowed_routes(m, werk, []) == []  # not used by any connection yet: no route
    m, _ = tn.apply_change(
        m, "connection", "create", {"id": "p", "src": "node:1", "dst": "dev:prn", "ports": "tcp:631"}
    )
    assert tn.allowed_routes(m, werk, []) == ["10.20.0.5/32"]
    assert tn.ref_domains(m, "dev:prn", {n["id"]: n for n in NODES}) == {"work"}
    r = pg.generate(m, ctx())
    assert r["policy"]["hosts"]["dev-prn"] == "10.20.0.5/32"
    g = next(x for x in r["policy"]["grants"] if x["src"] == ["node-1"] and x["dst"] == ["dev-prn"])
    assert g["ip"] == ["tcp:631"]
    # switching the connection off withdraws the route again
    m, _ = tn.apply_change(m, "connection", "update", {**tn_conn(m, "p"), "enabled": False})
    assert tn.allowed_routes(m, werk, []) == []
    # a client user can never reach it (other domain)
    bad, _ = tn.apply_change(m, "connection", "create", {"src": "user:anna", "dst": "dev:prn", "ports": "*"})
    with pytest.raises(tn.ModelError, match="project domain"):
        tn.validate(bad, NODES)
    # not behind an Edgebox, not a tailnet address, not both location and router
    for data, msg in (
        ({"via": "node:6", "ip": "10.1.1.1"}, "Edgebox"),
        ({"via": "node:4", "ip": "100.64.0.9"}, "tailnet address"),
        ({"via": "node:4", "ip": "10.81.1.50"}, "VPN subnet"),
    ):
        bad, _ = tn.apply_change(m, "device", "create", {"name": "x", **data})
        with pytest.raises(tn.ModelError, match=msg):
            tn.validate(bad, NODES)


def test_device_routes_are_approved_and_withdrawn(tmp_path, monkeypatch):
    import asyncio
    import types

    from hsha import hs, multitenant, paths

    monkeypatch.setattr(paths, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(paths, "AUDIT", tmp_path / "audit.jsonl")
    monkeypatch.setattr(paths, "TENANCY", tmp_path / "t.json")
    werk = {**NODES[3], "approved_routes": ["192.168.50.0/24"]}  # a route the user approved himself
    calls = []

    async def fake_approve(node_id, routes):
        calls.append((node_id, routes))
        werk["approved_routes"] = routes

    monkeypatch.setattr(hs, "approve_routes", fake_approve)
    opts = types.SimpleNamespace(admin_user="admin", subnet_router=False, exit_node=False)
    manager = types.SimpleNamespace(opts=opts, state={}, desired_routes=lambda: [])
    mt = multitenant.MultiTenant(manager)
    m = build()
    m, _ = tn.apply_change(m, "device", "create", {"id": "prn", "via": "node:4", "name": "P", "ip": "10.20.0.5"})
    m, _ = tn.apply_change(
        m, "connection", "create", {"id": "p", "src": "node:1", "dst": "dev:prn", "ports": "tcp:631"}
    )
    mt.model = m
    asyncio.run(mt._sync_device_routes([werk]))
    assert calls[-1] == (4, ["10.20.0.5/32", "192.168.50.0/24"])
    mt.model, _ = tn.apply_change(m, "connection", "delete", {"id": "p"})
    asyncio.run(mt._sync_device_routes([werk]))
    assert calls[-1] == (4, ["192.168.50.0/24"])  # only our /32 is withdrawn
    assert manager.state["mt_routes"] == {}


def test_legacy_client_kind_is_migrated(tmp_path, monkeypatch):
    from hsha import paths

    monkeypatch.setattr(paths, "TENANCY", tmp_path / "t.json")
    m = build()
    m["domains"][2]["kind"] = "client"
    tn.save(m)
    assert tn.load("admin")["domains"][2]["kind"] == "project"
    m2, _ = tn.apply_change(m, "domain", "create", {"id": "acme", "name": "ACME", "kind": "client"})
    assert tn.domain(m2, "acme")["kind"] == "project"


def test_device_types():
    m = build()
    by_id = {n["id"]: n for n in NODES}
    roles = {n["id"]: tn.node_role(m, n) for n in NODES}
    assert roles == {
        1: "workstation",
        2: "mobile",
        3: "router",
        4: "workstation",
        5: "workstation",
        6: "edgebox",
        7: "edgebox",
    }
    srv = {**NODES[3], "id": 8, "name": "nas", "tags": ["tag:work-server"], "user": {"name": "tagged-devices"}}
    assert tn.node_role(m, srv) == "server" and tn.node_domain(m, srv) == "work"
    m, _ = tn.apply_change(m, "noderole", "update", {"id": 4, "role": "server"})
    assert tn.node_role(m, NODES[3]) == "server"
    m, _ = tn.apply_change(m, "noderole", "update", {"id": 4, "role": "auto"})
    assert tn.node_role(m, NODES[3]) == "workstation"
    # Connections to a workstation: RDP is normal, a web port gets a warning; phones always do.
    ok, _ = tn.apply_change(m, "connection", "create", {"src": "node:1", "dst": "node:4", "ports": "profile:rdp"})
    assert not [w for w in tn.validate(ok, NODES) if "workstation" in w]
    odd, _ = tn.apply_change(m, "connection", "create", {"src": "node:1", "dst": "node:4", "ports": "tcp:8080"})
    assert [w for w in tn.validate(odd, NODES) if "workstation" in w]
    phone, _ = tn.apply_change(m, "connection", "create", {"src": "node:4", "dst": "node:2", "ports": "profile:ssh"})
    assert [w for w in tn.validate(phone, NODES) if "phone" in w]
    assert by_id
