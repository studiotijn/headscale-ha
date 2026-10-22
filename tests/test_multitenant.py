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
    node(1, "pc-thuis", "tijn"),
    node(2, "phone", "tijn"),
    node(3, "ha-router", tags=["tag:homerouter"], routes=["192.168.1.0/24"]),
    node(4, "pc-werk", "dynteq"),
    node(5, "laptop-klant", "srs-jan"),
    node(6, "edge-loc01", tags=["tag:srs-loc01-edge"], routes=["10.81.1.0/24"]),
    node(7, "edge-loc02", tags=["tag:srs-loc02-edge"]),
]


def build(**extra_conn):
    m = tn.default_model("tijn")
    m, _ = tn.apply_change(m, "domain", "update", {**m["domains"][2], "users": "srs-jan"})
    for n in (1, 2):
        m, _ = tn.apply_change(
            m,
            "location",
            "create",
            {
                "domain": "srs",
                "number": n,
                "name": f"Locatie {n}",
                "local_subnet": "172.168.1.0/24",
                "lan_iface": "eth1",
            },
        )
    m, _ = tn.apply_change(
        m, "device", "create", {"id": "lidar1", "location": "loc01", "name": "L1", "ip": "172.168.1.10"}
    )
    m, _ = tn.apply_change(
        m, "device", "create", {"id": "lidar2", "location": "loc02", "name": "L2", "ip": "172.168.1.10"}
    )
    conns = [
        {"name": "thuis-lidar", "src": "node:1", "dst": "dev:lidar1", "ports": "tcp:80, tcp:8010"},
        {"name": "werk-loc01", "src": "node:4", "dst": "loc:loc01", "ports": "tcp:80"},
        {"name": "klant-ssh", "src": "domain:srs", "dst": "edge:loc01", "ports": "tcp:22"},
    ]
    for c in conns:
        m, _ = tn.apply_change(m, "connection", "create", c)
    return m


def ctx(**kw):
    return pg.Context("tijn", NODES, home_routes=["192.168.1.0/24"], **kw)


def test_vpn_ip_keeps_host_part():
    m = build()
    loc = tn.location(m, "loc02")
    assert loc["vpn_subnet"] == "10.81.2.0/24"
    assert str(tn.vpn_ip(loc, "172.168.1.10")) == "10.81.2.10"
    with pytest.raises(tn.ModelError):
        tn.vpn_ip(loc, "172.168.2.10")


def test_overlapping_vpn_subnets_rejected():
    m = build()
    with pytest.raises(tn.ModelError, match="overlaps"):
        new, _ = tn.apply_change(
            m,
            "location",
            "create",
            {
                "domain": "srs",
                "number": 3,
                "name": "x",
                "local_subnet": "172.168.1.0/24",
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
                "domain": "srs",
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
        ("domain:srs", "node:1", "can never start connections"),
        ("node:5", "node:4", "can never start connections"),
        ("node:6", "dev:lidar1", "Edgebox can never be a source"),
        ("dev:lidar1", "node:1", "can never be a source"),
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
    assert doms == {1: "private", 2: "private", 3: "private", 4: "dynteq", 5: "srs", 6: "srs", 7: "srs"}
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
    assert not any(s.startswith(("tag:srs", "loc-", "dev-")) for s in srcs)
    assert "node-6" not in srcs and "node-7" not in srcs
    # No wildcard rules.
    assert all("*" not in g["src"] and "*" not in g["dst"] for g in pol["grants"])
    assert pol["autoApprovers"]["routes"]["10.81.1.0/24"] == ["tag:srs-loc01-edge"]
    assert pol["hosts"]["dev-lidar1"] == "10.81.1.10/32"


def test_policy_tests_cover_isolation():
    m = build()
    tests = pg.generate(m, ctx())["policy"]["tests"]
    by_src: dict[str, set] = {}
    for t in tests:
        by_src.setdefault(t["src"], set()).update(t.get("deny", []))
    assert "node-1:22" in by_src["node-6"]  # Edgebox loc01 -> pc-thuis
    assert "dev-lidar2:22" in by_src["dev-lidar1"]  # site -> other site
    assert "node-4:22" in by_src["node-1"]  # Private -> Dynteq
    assert "node-1:22" in by_src["node-5"]  # client user -> Private
    accepts = {(t["src"], a) for t in tests for a in t.get("accept", [])}
    assert ("node-1", "dev-lidar1:80") in accepts
    assert ("node-5", "node-6:22") in accepts


def test_disabled_connection_and_shares():
    m = build()
    c = next(x for x in m["connections"] if x["name"] == "thuis-lidar")
    m, _ = tn.apply_change(m, "connection", "update", {**c, "enabled": False})
    r = pg.generate(m, ctx(shared_services=[{"slug": "plex", "ip": "192.168.1.20", "ports": [32400]}]))
    names = [g["#name"] for g in r["policy"]["grants"]]
    assert "thuis-lidar" not in names
    share = next(g for g in r["policy"]["grants"] if g["#name"].startswith("Share"))
    assert share["src"] == ["group:dom-private"]  # never autogroup:member in this mode


def test_edge_nftables():
    m = build()
    text = pg.edge_nftables(m, "loc01", ctx())
    assert "dnat ip prefix to ip daddr map { 10.81.1.0/24 : 172.168.1.0/24 }" in text
    assert "policy drop;" in text
    assert "ip saddr 100.64.0.1 ip daddr 172.168.1.10 tcp dport { 80, 8010 } accept" in text
    assert "ip saddr 100.64.0.4 ip daddr 172.168.1.0/24 tcp dport 80 accept" in text
    assert "lidar2" not in text and "10.81.2" not in text
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
    for user in ("tijn", "dynteq", "srs-jan"):
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
    m, _ = tn.apply_change(m, "domain", "update", {**tn.domain(m, "srs"), "users": "srs-jan, srs-piet"})
    m, _ = tn.apply_change(
        m, "group", "create", {"id": "beheer", "name": "Beheerders", "members": ["node:1", "user:dynteq"]}
    )
    m, _ = tn.apply_change(
        m, "group", "create", {"id": "lidars", "name": "LiDARs", "members": ["dev:lidar1", "dev:lidar2"]}
    )
    m, _ = tn.apply_change(m, "profile", "create", {"name": "LiDAR web", "ports": "tcp:80, tcp:8010"})
    m, _ = tn.apply_change(
        m,
        "connection",
        "create",
        {
            "id": "g2g",
            "name": "Beheer naar LiDARs",
            "src": ["group:beheer"],
            "dst": ["group:lidars"],
            "ports": ["profile:lidar-web", "profile:ssh"],
        },
    )
    m, _ = tn.apply_change(
        m,
        "connection",
        "create",
        {"id": "u2e", "name": "Piet", "src": "user:srs-piet", "dst": "edge:loc02", "ports": "profile:ssh"},
    )
    tn.validate(m, NODES)
    r = pg.generate(m, ctx())
    g = next(x for x in r["policy"]["grants"] if x["#name"] == "Beheer naar LiDARs")
    assert g["src"] == ["node-1", "dynteq@"]
    assert g["dst"] == ["dev-lidar1", "dev-lidar2"]
    assert g["ip"] == ["tcp:80", "tcp:8010", "tcp:22"]
    piet = next(x for x in r["policy"]["grants"] if x["#name"] == "Piet")
    assert piet["src"] == ["srs-piet@"] and piet["dst"] == ["tag:srs-loc02-edge"]
    nft2 = pg.edge_nftables(m, "loc02", ctx())
    assert "ip saddr { 100.64.0.1, 100.64.0.4 } ip daddr 172.168.1.10 tcp dport { 80, 8010, 22 } accept" in nft2

    m3, _ = tn.apply_change(m, "connection", "update", {**tn_conn(m, "g2g"), "dst": ["dev:lidar2", "loc:loc02"]})
    nft3 = pg.edge_nftables(m3, "loc02", ctx())
    assert "ip daddr 172.168.1.0/24 tcp dport" in nft3 and "172.168.1.10," not in nft3  # host absorbed by subnet
    if shutil.which("nft"):
        for text in (nft2, nft3):
            res = subprocess.run(["nft", "-c", "-f", "-"], input=text, text=True, capture_output=True)
            assert res.returncode == 0, res.stderr

    # Editing a profile changes every connection that uses it.
    m, _ = tn.apply_change(m, "profile", "update", {"id": "lidar-web", "name": "LiDAR web", "ports": "tcp:8010"})
    g = next(x for x in pg.generate(m, ctx())["policy"]["grants"] if x["#name"] == "Beheer naar LiDARs")
    assert g["ip"] == ["tcp:8010", "tcp:22"]

    # In use: cannot delete; a group with a site device can never be a source.
    with pytest.raises(tn.ModelError, match="used by"):
        tn.apply_change(m, "group", "delete", {"id": "beheer"})
    with pytest.raises(tn.ModelError, match="used by"):
        tn.apply_change(m, "profile", "delete", {"id": "ssh"})
    bad, _ = tn.apply_change(m, "connection", "update", {**tn_conn(m, "g2g"), "src": ["group:lidars"]})
    with pytest.raises(tn.ModelError, match="never start"):
        tn.validate(bad, NODES)
    # A group mixing a client user with Private, towards Private: refused.
    m2, _ = tn.apply_change(m, "group", "create", {"id": "mix", "name": "Mix", "members": ["user:srs-jan", "node:1"]})
    bad, _ = tn.apply_change(m2, "connection", "create", {"src": "group:mix", "dst": "node:2", "ports": "*"})
    with pytest.raises(tn.ModelError, match="client domain"):
        tn.validate(bad, NODES)


def tn_conn(m, cid):
    return next(c for c in m["connections"] if c["id"] == cid)


def test_edit_in_place_and_cascade():
    m = build()
    c = next(x for x in m["connections"] if x["name"] == "thuis-lidar")
    m, summary = tn.apply_change(
        m, "connection", "update", {**c, "dst": ["dev:lidar1", "dev:lidar2"], "ports": "tcp:80"}
    )
    c2 = tn_conn(m, c["id"])
    assert c2["dst"] == ["dev:lidar1", "dev:lidar2"] and c2["ports"] == ["tcp:80"] and "updated" in summary
    m, _ = tn.apply_change(m, "location", "update", {**tn.location(m, "loc02"), "name": "Hengelo"})
    assert tn.location(m, "loc02")["name"] == "Hengelo" and tn.location(m, "loc02")["vpn_subnet"] == "10.81.2.0/24"
    m, _ = tn.apply_change(m, "device", "update", {**tn.device(m, "lidar2"), "ip": "172.168.1.11"})
    assert pg.generate(m, ctx())["policy"]["hosts"]["dev-lidar2"] == "10.81.2.11/32"
    # Deleting a location removes its devices from connections, but keeps the rest of the connection.
    m, _ = tn.apply_change(m, "location", "delete", {"id": "loc02"})
    assert tn_conn(m, c["id"])["dst"] == ["dev:lidar1"]
    # Removing a user from a domain removes it from connections.
    m, _ = tn.apply_change(
        m, "connection", "create", {"id": "u", "src": "user:srs-jan", "dst": "edge:loc01", "ports": "tcp:22"}
    )
    m, _ = tn.apply_change(m, "domain", "update", {**tn.domain(m, "srs"), "users": ""})
    assert all(x["id"] != "u" for x in m["connections"])


def test_access_overview():
    m = build()
    by_id = {n["id"]: n for n in NODES}
    a = tn.access(m, "node:1", by_id)
    assert [x["name"] for x in a["outgoing"]] == ["thuis-lidar"] and a["internal"] == ["private"]
    a = tn.access(m, "dev:lidar1", by_id)
    assert sorted(x["name"] for x in a["incoming"]) == ["thuis-lidar", "werk-loc01"]
    a = tn.access(m, "node:5", by_id)  # client user: via domain:srs
    assert [x["name"] for x in a["outgoing"]] == ["klant-ssh"]


def test_old_connections_are_migrated(tmp_path, monkeypatch):
    from hsha import paths

    monkeypatch.setattr(paths, "TENANCY", tmp_path / "t.json")
    m = build()
    for c in m["connections"]:
        c["src"], c["dst"] = c["src"][0], c["dst"][0]
    m.pop("port_profiles")
    tn.save(m)
    loaded = tn.load("tijn")
    assert all(isinstance(c["src"], list) for c in loaded["connections"])
    assert tn.profile(loaded, "ssh")["ports"] == ["tcp:22"]
