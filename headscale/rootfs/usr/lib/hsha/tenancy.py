"""Multi-tenant model: network domains, client locations, LAN devices and connections.

Only used with the app option ``multi_tenant``. The model is the single source of
truth for the ACL policy in that mode (see policygen.py). It is stored in
/data/hsha/tenancy.json and contains no secrets.

Terms
-----
domain      A network domain (Private, Dynteq, a client such as SRS/SHP). Its user-owned
            devices belong to the Headscale users listed in ``users``; its servers carry
            ``tag:<domain>-server``.
location    A client site with an Edgebox (``tag:<domain>-<location>-edge``). All sites may use
            the same local subnet (e.g. 172.168.1.0/24); the Edgebox maps it 1:1 onto a unique
            VPN subnet (10.81.<n>.0/24), so local host .y is reachable as 10.81.<n>.y.
device      A named host behind a location (local IP; the VPN IP follows from the mapping).
connection  An explicitly allowed flow: source (a node or all users of a domain) to a
            destination (node, LAN device, whole location subnet or the Edgebox itself) on
            given ports. Everything else is denied.
"""

from __future__ import annotations

import copy
import ipaddress
import re
import time
import uuid

from . import paths
from .store import read_json, write_json

SCHEMA = 1
KINDS = ("private", "work", "client")
INTERNAL = ("full", "none")
TAILNET_V4 = ipaddress.ip_network("100.64.0.0/10")

ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,19}$")
USER_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
IFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")
PORT_RE = re.compile(r"^(?:(tcp|udp|sctp):)?(\*|\d{1,5}(?:-\d{1,5})?)$")


class ModelError(ValueError):
    """Invalid model or change; the message is shown to the user."""


# ------------------------------------------------------------------ defaults
def default_model(admin_user: str) -> dict:
    """Starting point when multi-tenant mode is switched on for the first time.

    The existing devices all belong to ``admin_user``, so that user becomes the
    Private domain and nothing has to be re-registered.
    """
    return {
        "schema": SCHEMA,
        "revision": 1,
        "activated": False,
        "domains": [
            {
                "id": "private",
                "name": "Private",
                "kind": "private",
                "users": [admin_user],
                "internal": "full",
                "home": True,
            },
            {"id": "dynteq", "name": "Dynteq", "kind": "work", "users": ["dynteq"], "internal": "full", "home": False},
            {"id": "srs", "name": "SRS/SHP", "kind": "client", "users": [], "internal": "none", "home": False},
        ],
        "locations": [],
        "devices": [],
        "connections": [],
        "manual_grants": [],
        "applied": None,
    }


def load(admin_user: str) -> dict:
    model = read_json(paths.TENANCY, None)
    if not isinstance(model, dict) or model.get("schema") != SCHEMA:
        return default_model(admin_user)
    for key, default in (("locations", []), ("devices", []), ("connections", []), ("manual_grants", [])):
        model.setdefault(key, default)
    return model


def save(model: dict) -> None:
    write_json(paths.TENANCY, model, 0o600)


def new_id(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ------------------------------------------------------------------ lookups
def domain(model: dict, domain_id: str) -> dict | None:
    return next((d for d in model["domains"] if d["id"] == domain_id), None)


def location(model: dict, loc_id: str) -> dict | None:
    return next((loc for loc in model["locations"] if loc["id"] == loc_id), None)


def device(model: dict, dev_id: str) -> dict | None:
    return next((d for d in model["devices"] if d["id"] == dev_id), None)


def home_domain(model: dict) -> dict | None:
    return next((d for d in model["domains"] if d.get("home")), None)


def server_tag(domain_id: str) -> str:
    return f"tag:{domain_id}-server"


def edge_tag(loc: dict) -> str:
    return f"tag:{loc['domain']}-{loc['id']}-edge"


def all_users(model: dict) -> list[str]:
    return sorted({u for d in model["domains"] for u in d.get("users", [])})


# ------------------------------------------------------------------ addresses
def vpn_ip(loc: dict, local_ip: str) -> ipaddress.IPv4Address:
    """1:1 mapping of a local address onto the location's VPN subnet (same host part)."""
    local = ipaddress.ip_network(loc["local_subnet"])
    vpn = ipaddress.ip_network(loc["vpn_subnet"])
    ip = ipaddress.ip_address(local_ip)
    if ip not in local:
        raise ModelError(f"{local_ip} is not in the local subnet {local} of location {loc['name']}")
    return vpn.network_address + (int(ip) - int(local.network_address))


def suggest_vpn_subnet(model: dict, number: int, local_subnet: str, base: str = "10.81") -> str:
    """10.81.<number>.0/24 for a /24 site (the host part stays equal to the local one)."""
    local = ipaddress.ip_network(local_subnet, strict=False)
    if local.prefixlen != 24:
        raise ModelError("Choose the VPN subnet yourself for a local subnet that is not a /24")
    return f"{base}.{int(number)}.0/24"


def parse_ports(ports) -> list[str]:
    """Normalise a port list: '*', 'tcp:22', 'udp:53', 'tcp:8000-8010', '22' (tcp+udp), 'icmp'."""
    if isinstance(ports, str):
        ports = [p for p in re.split(r"[,\s]+", ports) if p]
    out = []
    for raw in ports or []:
        p = str(raw).strip().lower()
        if p in ("icmp", "icmp:*"):
            out.append("icmp:*")
            continue
        m = PORT_RE.match(p)
        if not m:
            raise ModelError(f"Invalid port '{raw}'. Use e.g. tcp:22, udp:53, tcp:8000-8010, 22, icmp or *")
        rng = m.group(2)
        if rng != "*":
            lo, _, hi = rng.partition("-")
            lo_i, hi_i = int(lo), int(hi or lo)
            if not (1 <= lo_i <= hi_i <= 65535):
                raise ModelError(f"Invalid port range '{raw}'")
        out.append(p)
    if not out:
        raise ModelError("A connection needs at least one port (use * for all)")
    return sorted(set(out), key=out.index)


# ------------------------------------------------------------------ node helpers
def node_ipv4(node: dict) -> str | None:
    return next((ip for ip in node.get("ip_addresses") or [] if "." in ip), None)


def node_tags(node: dict) -> list[str]:
    return list(node.get("tags") or node.get("valid_tags") or node.get("forced_tags") or [])


def node_user(node: dict) -> str | None:
    return (node.get("user") or {}).get("name")


def node_domain(model: dict, node: dict) -> str | None:
    """Domain a node belongs to: tags first (servers, Edgeboxes, home router), then its user."""
    tags = node_tags(node)
    if "tag:homerouter" in tags:
        home = home_domain(model)
        return home["id"] if home else None
    for d in sorted(model["domains"], key=lambda x: -len(x["id"])):
        if any(tag.startswith(f"tag:{d['id']}-") for tag in tags):
            return d["id"]
    if tags:
        return None
    user = node_user(node)
    return next((d["id"] for d in model["domains"] if user in d.get("users", [])), None)


def node_location(model: dict, node: dict) -> str | None:
    tags = node_tags(node)
    return next((loc["id"] for loc in model["locations"] if edge_tag(loc) in tags), None)


def edge_node(model: dict, loc: dict, nodes: list[dict]) -> dict | None:
    tag = edge_tag(loc)
    matches = [n for n in nodes if tag in node_tags(n)]
    return sorted(matches, key=lambda n: int(n["id"]))[0] if matches else None


def allowed_routes(model: dict, node: dict, home_routes: list[str]) -> list[str]:
    """Routes a node may have approved in multi-tenant mode (everything else stays unapproved)."""
    tags = node_tags(node)
    out: list[str] = []
    if "tag:homerouter" in tags:
        out += home_routes
    for loc in model["locations"]:
        if edge_tag(loc) in tags:
            out.append(str(ipaddress.ip_network(loc["vpn_subnet"])))
    return sorted(set(out))


# ------------------------------------------------------------------ validation
def _net(value: str, what: str) -> ipaddress.IPv4Network:
    try:
        net = ipaddress.ip_network(str(value).strip(), strict=True)
    except ValueError as exc:
        raise ModelError(f"{what}: '{value}' is not a valid IPv4 network (e.g. 172.168.1.0/24)") from exc
    if net.version != 4:
        raise ModelError(f"{what}: only IPv4 is supported")
    return net


def endpoint_domain(model: dict, ref: str, nodes_by_id: dict[int, dict]) -> str | None:
    kind, _, key = ref.partition(":")
    if kind == "domain":
        return key
    if kind == "node":
        node = nodes_by_id.get(int(key))
        return node_domain(model, node) if node else None
    if kind == "dev":
        dev = device(model, key)
        loc = location(model, dev["location"]) if dev else None
        return loc["domain"] if loc else None
    if kind in ("loc", "edge"):
        loc = location(model, key)
        return loc["domain"] if loc else None
    return None


def validate(model: dict, nodes: list[dict] | None = None, home_routes: list[str] | None = None) -> list[str]:
    """Raise ModelError for anything that would weaken isolation; return non-fatal warnings."""
    warnings: list[str] = []
    nodes = nodes or []
    nodes_by_id = {int(n["id"]): n for n in nodes}

    ids = [d["id"] for d in model["domains"]]
    if len(ids) != len(set(ids)):
        raise ModelError("Domain IDs must be unique")
    owners: dict[str, str] = {}
    homes = 0
    for d in model["domains"]:
        if not ID_RE.match(d["id"]):
            raise ModelError(f"Domain ID '{d['id']}': lowercase letters, digits and '-', max 20 characters")
        if d.get("kind") not in KINDS:
            raise ModelError(f"Domain {d['id']}: kind must be one of {', '.join(KINDS)}")
        if d.get("internal") not in INTERNAL:
            raise ModelError(f"Domain {d['id']}: internal must be full or none")
        homes += bool(d.get("home"))
        if d.get("home") and d.get("kind") == "client":
            raise ModelError("The home network (subnet router of this app) cannot belong to a client domain")
        for u in d.get("users", []):
            if not USER_RE.match(u):
                raise ModelError(f"Invalid user name '{u}'")
            if u in owners:
                raise ModelError(f"User '{u}' is in two domains ({owners[u]} and {d['id']})")
            owners[u] = d["id"]
    if homes > 1:
        raise ModelError("Only one domain can contain the home network")
    # A domain ID that is a prefix of another (srs / srs-x) would make tag ownership ambiguous.
    for a in ids:
        for b in ids:
            if a != b and b.startswith(a + "-"):
                raise ModelError(f"Domain IDs '{a}' and '{b}' overlap; choose IDs that are not prefixes")

    loc_ids = [loc["id"] for loc in model["locations"]]
    if len(loc_ids) != len(set(loc_ids)):
        raise ModelError("Location IDs must be unique")
    vpn_nets: list[tuple[ipaddress.IPv4Network, str]] = []
    reserved = [(ipaddress.ip_network(r, strict=False), "the home network") for r in (home_routes or [])]
    for loc in model["locations"]:
        dom = domain(model, loc["domain"])
        if not ID_RE.match(loc["id"]):
            raise ModelError(f"Location ID '{loc['id']}': lowercase letters, digits and '-', max 20 characters")
        if dom is None:
            raise ModelError(f"Location {loc['id']}: unknown domain {loc['domain']}")
        if dom["kind"] != "client":
            raise ModelError(f"Location {loc['id']}: locations belong to client domains")
        local = _net(loc["local_subnet"], f"Location {loc['name']}: local subnet")
        vpn = _net(loc["vpn_subnet"], f"Location {loc['name']}: VPN subnet")
        if local.prefixlen != vpn.prefixlen:
            raise ModelError(f"Location {loc['name']}: local and VPN subnet need the same size (/{local.prefixlen})")
        if vpn.overlaps(TAILNET_V4):
            raise ModelError(f"Location {loc['name']}: VPN subnet overlaps the tailnet range 100.64.0.0/10")
        if not vpn.is_private:
            warnings.append(f"Location {loc['name']}: VPN subnet {vpn} is not a private (RFC 1918) range")
        for other, name in vpn_nets + reserved:
            if vpn.overlaps(other):
                raise ModelError(f"Location {loc['name']}: VPN subnet {vpn} overlaps {name} ({other})")
        vpn_nets.append((vpn, f"location {loc['name']}"))
        if not IFACE_RE.match(loc.get("lan_iface") or ""):
            raise ModelError(f"Location {loc['name']}: invalid LAN interface name")

    for dev in model["devices"]:
        loc = location(model, dev["location"])
        if loc is None:
            raise ModelError(f"Device {dev['name']}: unknown location")
        vpn_ip(loc, dev["ip"])  # raises when outside the local subnet
    seen = set()
    for dev in model["devices"]:
        key = (dev["location"], dev["ip"])
        if key in seen:
            raise ModelError(f"Two devices with IP {dev['ip']} in the same location")
        seen.add(key)

    for c in model["connections"]:
        check_connection(model, c, nodes_by_id, warnings)
    for g in model.get("manual_grants", []):
        if not isinstance(g, dict) or not g.get("src") or not g.get("dst"):
            raise ModelError("Every manual grant needs src and dst")
    return warnings


def check_connection(model: dict, c: dict, nodes_by_id: dict[int, dict], warnings: list[str]) -> None:
    name = c.get("name") or c.get("id")
    src_kind, _, src_key = str(c.get("src", "")).partition(":")
    dst_kind, _, dst_key = str(c.get("dst", "")).partition(":")
    if src_kind not in ("node", "domain"):
        raise ModelError(f"Connection {name}: the source must be a device or the users of a domain")
    if dst_kind not in ("node", "dev", "loc", "edge"):
        raise ModelError(f"Connection {name}: unknown destination")
    if src_kind == "domain" and domain(model, src_key) is None:
        raise ModelError(f"Connection {name}: unknown source domain")
    if src_kind == "node":
        node = nodes_by_id.get(int(src_key)) if src_key.isdigit() else None
        if node is None:
            if nodes_by_id:
                warnings.append(f"Connection {name}: source device {src_key} no longer exists")
        elif node_location(model, node):
            raise ModelError(f"Connection {name}: an Edgebox can never be a source")
    if dst_kind == "dev" and device(model, dst_key) is None:
        raise ModelError(f"Connection {name}: unknown destination device")
    if dst_kind in ("loc", "edge") and location(model, dst_key) is None:
        raise ModelError(f"Connection {name}: unknown destination location")
    if dst_kind == "node" and nodes_by_id and int(dst_key) not in nodes_by_id:
        warnings.append(f"Connection {name}: destination device {dst_key} no longer exists")
    parse_ports(c.get("ports"))

    src_dom = endpoint_domain(model, c["src"], nodes_by_id)
    dst_dom = endpoint_domain(model, c["dst"], nodes_by_id)
    src_d = domain(model, src_dom) if src_dom else None
    if src_d and src_d["kind"] == "client" and dst_dom and dst_dom != src_dom:
        raise ModelError(f"Connection {name}: a client domain can never start connections to another domain")
    if src_dom and dst_dom and src_dom != dst_dom:
        dst_d = domain(model, dst_dom)
        if src_d and dst_d and src_d["kind"] != "client" and dst_d["kind"] != "client":
            warnings.append(f"Connection {name}: crosses {src_d['name']} → {dst_d['name']} (allowed, but on purpose?)")


# ------------------------------------------------------------------ mutations
def _bump(model: dict) -> None:
    model["revision"] = int(model.get("revision", 0)) + 1
    model["changed_at"] = int(time.time())


def apply_change(model: dict, kind: str, action: str, data: dict) -> tuple[dict, str]:
    """Return a changed copy of the model and a human summary (for the audit log)."""
    m = copy.deepcopy(model)
    coll = {"domain": "domains", "location": "locations", "device": "devices", "connection": "connections"}.get(kind)
    if coll is None:
        raise ModelError(f"Unknown object type {kind}")
    items = m[coll]

    if action == "delete":
        key = str(data.get("id"))
        before = len(items)
        m[coll] = [x for x in items if x["id"] != key]
        if len(m[coll]) == before:
            raise ModelError(f"{kind} {key} not found")
        _cascade_delete(m, kind, key)
        _bump(m)
        return m, f"{kind} {key} deleted"

    if action not in ("create", "update"):
        raise ModelError(f"Unknown action {action}")
    obj = _build(m, kind, data, creating=action == "create")
    if action == "create":
        if any(x["id"] == obj["id"] for x in items):
            raise ModelError(f"{kind} with ID {obj['id']} already exists")
        items.append(obj)
    else:
        idx = next((i for i, x in enumerate(items) if x["id"] == obj["id"]), None)
        if idx is None:
            raise ModelError(f"{kind} {obj['id']} not found")
        items[idx] = {**items[idx], **obj}
    _bump(m)
    label = obj.get("name") or obj["id"]
    if kind == "connection":
        label = f"{label} ({obj['src']} → {obj['dst']} {','.join(obj['ports'])}, {'on' if obj['enabled'] else 'off'})"
    return m, f"{kind} {label} {action}d"


def _cascade_delete(m: dict, kind: str, key: str) -> None:
    if kind == "domain":
        if any(loc["domain"] == key for loc in m["locations"]):
            raise ModelError("Delete the locations of this domain first")
        m["connections"] = [c for c in m["connections"] if c["src"] != f"domain:{key}"]
    if kind == "location":
        m["devices"] = [d for d in m["devices"] if d["location"] != key]
        gone = {f"loc:{key}", f"edge:{key}"}
        m["connections"] = [c for c in m["connections"] if c["dst"] not in gone]
    if kind in ("location", "device"):
        live = {f"dev:{d['id']}" for d in m["devices"]}
        m["connections"] = [c for c in m["connections"] if not c["dst"].startswith("dev:") or c["dst"] in live]


def _text(data: dict, key: str, default: str = "", limit: int = 64) -> str:
    return str(data.get(key) if data.get(key) is not None else default).strip()[:limit]


def _build(m: dict, kind: str, data: dict, creating: bool) -> dict:
    if kind == "domain":
        users = data.get("users", [])
        if isinstance(users, str):
            users = [u for u in re.split(r"[,\s]+", users) if u]
        obj = {
            "id": _text(data, "id").lower(),
            "name": _text(data, "name") or _text(data, "id"),
            "kind": _text(data, "kind", "client"),
            "users": sorted({str(u).strip().lower() for u in users}),
            "internal": _text(data, "internal", "none"),
            "home": bool(data.get("home", False)),
        }
        if not creating:
            current = domain(m, obj["id"]) or {}
            obj["home"] = current.get("home", False)  # only the migration sets the home domain
        return obj
    if kind == "location":
        number = int(data.get("number") or 0)
        local = _text(data, "local_subnet", "172.168.1.0/24")
        vpn = _text(data, "vpn_subnet") or suggest_vpn_subnet(m, number, local)
        loc_id = _text(data, "id").lower() or (f"loc{number:02d}" if number else "")
        return {
            "id": loc_id,
            "domain": _text(data, "domain"),
            "name": _text(data, "name") or loc_id,
            "number": number,
            "local_subnet": str(ipaddress.ip_network(local, strict=False)),
            "vpn_subnet": str(ipaddress.ip_network(vpn, strict=False)),
            "lan_iface": _text(data, "lan_iface", "eth0", 15),
            "note": _text(data, "note", "", 200),
        }
    if kind == "device":
        return {
            "id": _text(data, "id") or new_id("d"),
            "location": _text(data, "location"),
            "name": _text(data, "name") or _text(data, "ip"),
            "ip": str(ipaddress.IPv4Address(_text(data, "ip"))),
            "note": _text(data, "note", "", 200),
        }
    # connection
    return {
        "id": _text(data, "id") or new_id("c"),
        "name": _text(data, "name"),
        "src": _text(data, "src"),
        "dst": _text(data, "dst"),
        "ports": parse_ports(data.get("ports")),
        "enabled": bool(data.get("enabled", True)),
        "note": _text(data, "note", "", 200),
    }
