"""Unit tests for the multi-tenant model and policy generator (run: pytest tests/)."""

from __future__ import annotations

import json
import os
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
    assert [d["id"] for d in m["domains"]] == ["home"]
    # Users as they are before the app aligns them with the networks (sync_users).
    m["domains"] = [
        {"id": "private", "name": "Private", "kind": "domain", "users": ["admin"], "internal": "full", "home": True},
        {"id": "work", "name": "Work", "kind": "domain", "users": ["work"], "internal": "full", "home": False},
        {"id": "project", "name": "Project", "kind": "cluster", "users": ["anna"], "internal": "none", "home": False},
    ]
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
        ("node:6", "dev:cam1", "gateway can never be a source"),
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
    # Nothing at a site (gateway, site subnet, device behind it) is ever a source.
    assert not any(s.endswith("-edge") or s.startswith(("loc-", "dev-")) for s in srcs)
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
    assert "node-1:22" in by_src["node-6"]  # gateway loc01 -> pc-thuis
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
    if shutil.which("nft") and os.geteuid() == 0:  # nft -c needs root (CI checks it in edge_dataplane.sh)
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
        {"id": "u2e", "name": "Piet", "src": "user:anna", "dst": "edge:loc02", "ports": "profile:ssh"},
    )
    tn.validate(m, NODES)
    r = pg.generate(m, ctx())
    g = next(x for x in r["policy"]["grants"] if x["#name"] == "Beheer naar Cameras")
    assert g["src"] == ["node-1", "work@"]
    assert g["dst"] == ["dev-cam1", "dev-cam2"]
    assert g["ip"] == ["tcp:80", "tcp:8010", "tcp:22"]
    piet = next(x for x in r["policy"]["grants"] if x["#name"] == "Piet")
    assert piet["src"] == ["anna@"] and piet["dst"] == ["tag:project-loc02-edge"]
    nft2 = pg.edge_nftables(m, "loc02", ctx())
    assert "ip saddr { 100.64.0.1, 100.64.0.4 } ip daddr 192.168.1.10 tcp dport { 80, 8010, 22 } accept" in nft2

    m3, _ = tn.apply_change(m, "connection", "update", {**tn_conn(m, "g2g"), "dst": ["dev:cam2", "loc:loc02"]})
    nft3 = pg.edge_nftables(m3, "loc02", ctx())
    assert "ip daddr 192.168.1.0/24 tcp dport" in nft3 and "192.168.1.10," not in nft3  # host absorbed by subnet
    if shutil.which("nft") and os.geteuid() == 0:  # nft -c needs root (CI checks it in edge_dataplane.sh)
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
    # A group mixing a cluster user with Private, towards Private: allowed (explicit connection).
    m2, _ = tn.apply_change(m, "group", "create", {"id": "mix", "name": "Mix", "members": ["user:anna", "node:1"]})
    ok, _ = tn.apply_change(m2, "connection", "create", {"src": "group:mix", "dst": "node:2", "ports": "*"})
    tn.validate(ok, NODES)


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
    # Users are not edited through the model: one per network, kept in line by the app.
    m2, _ = tn.apply_change(m, "domain", "update", {**tn.domain(m, "project"), "users": ""})
    assert tn.domain(m2, "project")["users"] == ["anna"]
    m3, _ = tn.apply_change(m, "domain", "create", {"id": "acme", "name": "ACME", "kind": "cluster", "users": "x"})
    assert tn.domain(m3, "acme")["users"] == ["acme"]


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
    # a cluster user may reach it, but only through an explicit connection
    ok, _ = tn.apply_change(m, "connection", "create", {"src": "user:anna", "dst": "dev:prn", "ports": "*"})
    tn.validate(ok, NODES)
    # not behind an gateway, not a tailnet address, not both location and router
    for data, msg in (
        ({"via": "node:6", "ip": "10.1.1.1"}, "gateway"),
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
    assert tn.load("admin")["domains"][2]["kind"] == "cluster"
    m2, _ = tn.apply_change(m, "domain", "create", {"id": "acme", "name": "ACME", "kind": "client"})
    assert tn.domain(m2, "acme")["kind"] == "cluster"


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
        6: "gateway",
        7: "gateway",
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


def test_domain_and_cluster_kinds(tmp_path, monkeypatch):
    m = build()
    assert [d["kind"] for d in m["domains"]] == ["domain", "domain", "cluster"]
    assert [d["internal"] for d in m["domains"]] == ["full", "full", "none"]
    # The kind decides the internal policy; a separate value is ignored.
    data = {"id": "acme", "name": "ACME", "kind": "cluster", "internal": "full"}
    m2, _ = tn.apply_change(m, "domain", "create", data)
    assert tn.domain(m2, "acme")["internal"] == "none"
    # Old kinds are converted on load.
    from hsha import paths

    monkeypatch.setattr(paths, "TENANCY", tmp_path / "t.json")
    old = json.loads(json.dumps(m))
    for d, k in zip(old["domains"], ("private", "work", "project"), strict=True):
        d["kind"], d["internal"] = k, "none"
    tn.save(old)
    loaded = tn.load("admin")
    assert [(d["kind"], d["internal"]) for d in loaded["domains"]] == [
        ("domain", "full"),
        ("domain", "full"),
        ("cluster", "none"),
    ]


def test_cluster_may_start_connections_and_is_closed_inside():
    m = build(**{})
    # A cluster user and the whole cluster may reach individual devices or a whole domain elsewhere.
    for src, dst in (("node:5", "node:4"), ("domain:project", "node:1"), ("user:anna", "domain:work")):
        ok, _ = tn.apply_change(m, "connection", "create", {"src": src, "dst": dst, "ports": "tcp:22"})
        tn.validate(ok, NODES)
    r = pg.generate(ok, ctx())
    assert any(g["src"] == ["anna@"] and "group:dom-work" in g["dst"] for g in r["policy"]["grants"])
    # Domains: users and servers reach everything inside; clusters get no internal grant.
    internal = {g["#name"]: g for g in r["policy"]["grants"] if g["#name"].endswith(": internal")}
    assert set(internal) == {"Private: internal", "Work: internal"}
    assert "tag:work-server" in internal["Work: internal"]["src"]


def test_rename_user_refs():
    m = build()
    m, _ = tn.apply_change(m, "group", "create", {"id": "g", "name": "G", "members": ["user:anna", "user:project"]})
    m, _ = tn.apply_change(m, "connection", "create", {"id": "x", "src": "user:anna", "dst": "node:1", "ports": "*"})
    assert tn.rename_user_refs(m, "anna", "project")
    assert tn_conn(m, "x")["src"] == ["user:project"]
    assert tn.group(m, "g")["members"] == ["user:project"]  # deduplicated
    assert not tn.rename_user_refs(m, "anna", "project")


def test_db_users(tmp_path):
    import sqlite3

    from hsha import hs

    db = tmp_path / "db.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, display_name TEXT, deleted_at TEXT);"
        "CREATE TABLE nodes (id INTEGER PRIMARY KEY, user_id INTEGER, tags TEXT, deleted_at TEXT);"
        "INSERT INTO users VALUES (1, 'project', NULL, NULL), (2, 'piet', NULL, NULL);"
        "INSERT INTO nodes VALUES (10, 1, '[]', NULL), (11, 2, '[]', NULL), (12, 2, '[]', NULL);"
    )
    con.commit()
    con.close()
    r = hs.db_users(str(db), {"project": "SRS/SHP"}, {"piet": "project"})
    assert r == {"display": ["project"], "moved": 2}
    con = sqlite3.connect(db)
    assert con.execute("SELECT display_name FROM users WHERE id = 1").fetchone() == ("SRS/SHP",)
    assert con.execute("SELECT COUNT(*) FROM nodes WHERE user_id = 1").fetchone() == (3,)
