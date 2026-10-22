"""Multi-tenant model: network domains, project locations, LAN devices and connections.

Only used with the app option ``multi_tenant``. The model is the single source of
truth for the ACL policy in that mode (see policygen.py). It is stored in
/data/hsha/tenancy.json and contains no secrets.

Terms
-----
domain      A network domain (e.g. Private, Work, a Project with sites). Its user-owned
            devices belong to the Headscale users listed in ``users``; its servers carry
            ``tag:<domain>-server``.
location    A project site with an Edgebox (``tag:<domain>-<location>-edge``). All sites may use
            the same local subnet (e.g. 192.168.1.0/24); the Edgebox maps it 1:1 onto a unique
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
KINDS = ("private", "work", "project")
LEGACY_KINDS = {"client": "project"}  # 0.7.0-0.9.0
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
            {"id": "work", "name": "Work", "kind": "work", "users": [], "internal": "full", "home": False},
            {"id": "project", "name": "Project", "kind": "project", "users": [], "internal": "none", "home": False},
        ],
        "locations": [],
        "devices": [],
        "connections": [],
        "groups": [],
        "node_roles": {},
        "port_profiles": default_profiles(),
        "manual_grants": [],
        "applied": None,
    }


def default_profiles() -> list[dict]:
    """Ready-made port sets; editable in the app. A connection that uses one follows its changes."""
    return [
        {"id": "ssh", "name": "SSH", "ports": ["tcp:22"]},
        {"id": "web", "name": "Web (HTTP/HTTPS)", "ports": ["tcp:80", "tcp:443"]},
        {"id": "rdp", "name": "Remote Desktop", "ports": ["tcp:3389"]},
        {"id": "vnc", "name": "VNC", "ports": ["tcp:5900"]},
        {"id": "smb", "name": "File sharing (SMB)", "ports": ["tcp:445"]},
        {"id": "modbus", "name": "Modbus TCP", "ports": ["tcp:502"]},
        {"id": "opcua", "name": "OPC UA", "ports": ["tcp:4840"]},
        {"id": "mqtt", "name": "MQTT", "ports": ["tcp:1883", "tcp:8883"]},
        {"id": "ping", "name": "Ping", "ports": ["icmp:*"]},
    ]


def load(admin_user: str) -> dict:
    model = read_json(paths.TENANCY, None)
    if not isinstance(model, dict) or model.get("schema") != SCHEMA:
        return default_model(admin_user)
    for key, default in (
        ("locations", []),
        ("devices", []),
        ("connections", []),
        ("manual_grants", []),
        ("groups", []),
    ):
        model.setdefault(key, default)
    model.setdefault("port_profiles", default_profiles())
    model.setdefault("node_roles", {})
    for d in model["domains"]:  # "client" was renamed to "project"
        d["kind"] = LEGACY_KINDS.get(d.get("kind"), d.get("kind"))
    for c in model["connections"]:  # 0.7.0 stored one source and one destination as strings
        c["src"], c["dst"] = as_list(c.get("src")), as_list(c.get("dst"))
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


def device_vpn_ip(model: dict, dev: dict) -> ipaddress.IPv4Address:
    """Address a device has over the VPN: mapped at a site, unchanged behind another router."""
    if dev.get("location"):
        loc = location(model, dev["location"])
        if loc is None:
            raise ModelError(f"Device {dev['name']}: unknown location")
        return vpn_ip(loc, dev["ip"])
    return ipaddress.ip_address(dev["ip"])


def via_node_id(dev: dict) -> int | None:
    via = str(dev.get("via") or "")
    return int(via) if via.isdigit() else None


def device_in_use(model: dict, dev_id: str) -> bool:
    ref = f"dev:{dev_id}"
    return any(c.get("enabled", True) and ref in expand_refs(model, c["dst"]) for c in model["connections"])


def device_routes(model: dict, node_id: int) -> list[str]:
    """Routes the app approves on a node for devices behind it that a connection uses (one /32 each)."""
    return sorted(
        {f"{d['ip']}/32" for d in model["devices"] if via_node_id(d) == int(node_id) and device_in_use(model, d["id"])}
    )


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


# What a VPN device is, which decides how the app offers it. Servers are the usual destinations;
# workstations are mostly sources and only a destination for remote desktop or file sharing;
# phones and tablets are never a destination.
ROLES = ("server", "workstation", "mobile")
WORKSTATION_PORTS = {"tcp:3389", "tcp:5900", "tcp:445", "tcp:22", "icmp:*", "3389", "5900", "445", "22"}
WORKSTATION_PROFILES = {"rdp", "vnc", "smb", "ssh", "ping"}
_MOBILE_NAME = re.compile(r"iphone|ipad|android|pixel|galaxy|phone|tablet|ipod|sm-[a-z0-9]", re.I)


def node_role(model: dict, node: dict) -> str:
    """server / workstation / mobile, or router / edgebox for the app's own routers."""
    tags = node_tags(node)
    if "tag:homerouter" in tags:
        return "router"
    if node_location(model, node):
        return "edgebox"
    if any(tag.endswith("-server") for tag in tags):
        return "server"
    chosen = model.get("node_roles", {}).get(str(node["id"]))
    if chosen in ROLES:
        return chosen
    name = f"{node.get('given_name') or ''} {node.get('name') or ''}"
    return "mobile" if _MOBILE_NAME.search(name) else "workstation"


def _workstation_ports_only(model: dict, ports) -> bool:
    for p in as_list(ports):
        if p.startswith("profile:"):
            if p.split(":", 1)[1] not in WORKSTATION_PROFILES:
                return False
        elif p not in WORKSTATION_PORTS:
            return False
    return True


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
    out += device_routes(model, int(node["id"]))
    return sorted(set(out))


# ------------------------------------------------------------------ validation
def _net(value: str, what: str) -> ipaddress.IPv4Network:
    try:
        net = ipaddress.ip_network(str(value).strip(), strict=True)
    except ValueError as exc:
        raise ModelError(f"{what}: '{value}' is not a valid IPv4 network (e.g. 192.168.1.0/24)") from exc
    if net.version != 4:
        raise ModelError(f"{what}: only IPv4 is supported")
    return net


# ------------------------------------------------------------------ references
# A reference names something a connection or group points at:
#   user:<name>  domain:<id>  node:<headscale id>  group:<id>        (sources and destinations)
#   dev:<id>     loc:<id>     edge:<location id>                      (destinations only)
SRC_KINDS = ("user", "domain", "node", "group")
DST_KINDS = ("user", "domain", "node", "group", "dev", "loc", "edge")
MEMBER_KINDS = ("user", "domain", "node", "dev", "loc", "edge")


def as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [v for v in re.split(r"[,\s]+", value) if v]
    out: list[str] = []
    for v in value:
        v = str(v).strip()
        if v and v not in out:
            out.append(v)
    return out


def group(model: dict, group_id: str) -> dict | None:
    return next((g for g in model.get("groups", []) if g["id"] == group_id), None)


def profile(model: dict, profile_id: str) -> dict | None:
    return next((p for p in model.get("port_profiles", []) if p["id"] == profile_id), None)


def user_domain(model: dict, user: str) -> str | None:
    return next((d["id"] for d in model["domains"] if user in d.get("users", [])), None)


def expand_refs(model: dict, refs) -> list[str]:
    """Replace group references by their members (groups do not nest)."""
    out: list[str] = []
    for ref in as_list(refs):
        kind, _, key = ref.partition(":")
        members = (group(model, key) or {}).get("members", []) if kind == "group" else [ref]
        for m in members:
            if m not in out:
                out.append(m)
    return out


def expand_ports(model: dict, ports) -> list[str]:
    """Port entries with profile:<id> replaced by the ports of that profile."""
    out: list[str] = []
    for p in as_list(ports):
        if p.startswith("profile:"):
            prof = profile(model, p.split(":", 1)[1])
            items = prof["ports"] if prof else []
        else:
            items = [p]
        for i in items:
            if i not in out:
                out.append(i)
    return ["*"] if "*" in out else out


def normalize_ports(model: dict, ports) -> list[str]:
    out: list[str] = []
    for p in as_list(ports):
        if p.startswith("profile:"):
            if profile(model, p.split(":", 1)[1]) is None:
                raise ModelError(f"Unknown port profile '{p.split(':', 1)[1]}'")
            item = [p]
        else:
            item = parse_ports([p])
        for i in item:
            if i not in out:
                out.append(i)
    if not out:
        raise ModelError("A connection needs at least one port (use * for all)")
    return out


def ref_domains(model: dict, ref: str, nodes_by_id: dict[int, dict]) -> set[str]:
    kind, _, key = ref.partition(":")
    if kind == "group":
        return set().union(*[ref_domains(model, m, nodes_by_id) for m in expand_refs(model, [ref])] or [set()])
    if kind == "domain":
        return {key}
    if kind == "user":
        d = user_domain(model, key)
        return {d} if d else set()
    if kind == "node":
        node = nodes_by_id.get(int(key)) if key.isdigit() else None
        d = node_domain(model, node) if node else None
        return {d} if d else set()
    if kind == "dev":
        dev = device(model, key)
        if dev and via_node_id(dev) is not None:
            return ref_domains(model, f"node:{via_node_id(dev)}", nodes_by_id)
        loc = location(model, dev["location"]) if dev and dev.get("location") else None
        return {loc["domain"]} if loc else set()
    if kind in ("loc", "edge"):
        loc = location(model, key)
        return {loc["domain"]} if loc else set()
    return set()


def endpoint_domains(model: dict, refs, nodes_by_id: dict[int, dict]) -> set[str]:
    return set().union(*[ref_domains(model, r, nodes_by_id) for r in as_list(refs)] or [set()])


def endpoint_domain(model: dict, ref, nodes_by_id: dict[int, dict]) -> str | None:
    """Single domain of an endpoint (None when it spans several or none)."""
    doms = endpoint_domains(model, ref, nodes_by_id)
    return next(iter(doms)) if len(doms) == 1 else None


def ref_exists(model: dict, ref: str, nodes_by_id: dict[int, dict]) -> bool | None:
    """True/False, or None when it cannot be known (node list unavailable)."""
    kind, _, key = ref.partition(":")
    if kind == "user":
        return user_domain(model, key) is not None
    if kind == "domain":
        return domain(model, key) is not None
    if kind == "group":
        return group(model, key) is not None
    if kind == "dev":
        return device(model, key) is not None
    if kind in ("loc", "edge"):
        return location(model, key) is not None
    if kind == "node":
        if not key.isdigit():
            return False
        return (int(key) in nodes_by_id) if nodes_by_id else None
    return False


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
        if d.get("home") and d.get("kind") == "project":
            raise ModelError("The home network (subnet router of this app) cannot belong to a project domain")
        for u in d.get("users", []):
            if not USER_RE.match(u):
                raise ModelError(f"Invalid user name '{u}'")
            if u in owners:
                raise ModelError(f"User '{u}' is in two domains ({owners[u]} and {d['id']})")
            owners[u] = d["id"]
    if homes > 1:
        raise ModelError("Only one domain can contain the home network")
    # A domain ID that is a prefix of another (proj / proj-x) would make tag ownership ambiguous.
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
        if dom["kind"] != "project":
            raise ModelError(f"Location {loc['id']}: locations belong to project domains")
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

    site_nets = [ipaddress.ip_network(loc["vpn_subnet"]) for loc in model["locations"]]
    for dev in model["devices"]:
        if bool(dev.get("location")) == (via_node_id(dev) is not None):
            raise ModelError(f"Device {dev['name']}: choose either a location or the device it is reached through")
        if dev.get("location"):
            if location(model, dev["location"]) is None:
                raise ModelError(f"Device {dev['name']}: unknown location")
            vpn_ip(location(model, dev["location"]), dev["ip"])  # raises when outside the local subnet
            continue
        ip = ipaddress.ip_address(dev["ip"])
        if ip in TAILNET_V4:
            raise ModelError(f"Device {dev['name']}: {ip} is a tailnet address; choose the device itself instead")
        if any(ip in n for n in site_nets):
            raise ModelError(f"Device {dev['name']}: {ip} is inside a location's VPN subnet; add it to that location")
        node = nodes_by_id.get(via_node_id(dev)) if nodes_by_id else None
        if nodes_by_id and node is None:
            warnings.append(f"Device {dev['name']}: the device it is reached through no longer exists")
        elif node is not None and node_location(model, node):
            raise ModelError(f"Device {dev['name']}: behind an Edgebox, add it to that location instead")
    seen = set()
    for dev in model["devices"]:
        key = (dev.get("location") or f"via{dev.get('via')}", dev["ip"])
        if key in seen:
            raise ModelError(f"Two devices with IP {dev['ip']} in the same location")
        seen.add(key)

    for g in model.get("groups", []):
        check_group(model, g)
    for prof in model.get("port_profiles", []):
        parse_ports(prof.get("ports"))
    for c in model["connections"]:
        check_connection(model, c, nodes_by_id, warnings)
    for g in model.get("manual_grants", []):
        if not isinstance(g, dict) or not g.get("src") or not g.get("dst"):
            raise ModelError("Every manual grant needs src and dst")
    return warnings


def check_group(model: dict, g: dict) -> None:
    for m in g.get("members", []):
        kind = m.partition(":")[0]
        if kind not in MEMBER_KINDS:
            raise ModelError(f"Group {g['name']}: '{m}' cannot be a member (groups do not nest)")
        if ref_exists(model, m, {}) is False:
            raise ModelError(f"Group {g['name']}: unknown member {m}")


def check_connection(model: dict, c: dict, nodes_by_id: dict[int, dict], warnings: list[str]) -> None:
    name = c.get("name") or c.get("id")
    srcs, dsts = as_list(c.get("src")), as_list(c.get("dst"))
    if not srcs:
        raise ModelError(f"Connection {name}: choose at least one source")
    if not dsts:
        raise ModelError(f"Connection {name}: choose at least one destination")
    for ref in srcs:
        if ref.partition(":")[0] not in SRC_KINDS:
            raise ModelError(f"Connection {name}: a site, device at a site or Edgebox can never be a source")
    for ref in dsts:
        if ref.partition(":")[0] not in DST_KINDS:
            raise ModelError(f"Connection {name}: unknown destination {ref}")
    for ref in srcs + dsts:
        if ref_exists(model, ref, nodes_by_id) is False:
            if ref.startswith("node:"):
                warnings.append(f"Connection {name}: device {ref.split(':')[1]} no longer exists")
            else:
                raise ModelError(f"Connection {name}: unknown {ref}")
    for ref in expand_refs(model, srcs):
        kind, _, key = ref.partition(":")
        if kind not in ("user", "domain", "node"):
            raise ModelError(
                f"Connection {name}: the group used as source contains a site, device at a site or Edgebox; "
                "those can never start connections"
            )
        node = nodes_by_id.get(int(key)) if kind == "node" and key.isdigit() else None
        if node is not None and node_location(model, node):
            raise ModelError(f"Connection {name}: an Edgebox can never be a source")
    normalize_ports(model, c.get("ports"))
    for ref in expand_refs(model, dsts):
        kind, _, key = ref.partition(":")
        node = nodes_by_id.get(int(key)) if kind == "node" and key.isdigit() else None
        if node is None:
            continue
        role = node_role(model, node)
        label = node.get("given_name") or node.get("name")
        if role == "mobile":
            warnings.append(f"Connection {name}: {label} is a phone or tablet; those are almost never a destination")
        elif role == "workstation" and not _workstation_ports_only(model, c.get("ports")):
            warnings.append(
                f"Connection {name}: {label} is a workstation; usually only remote desktop, VNC, SSH or file "
                "sharing goes to a workstation. Is it a server? Mark it as server."
            )

    src_doms = endpoint_domains(model, srcs, nodes_by_id)
    dst_doms = endpoint_domains(model, dsts, nodes_by_id)
    for sd in src_doms:
        d = domain(model, sd)
        if d and d["kind"] == "project" and dst_doms - {sd}:
            raise ModelError(
                f"Connection {name}: {d['name']} is a project domain; it can never start connections to another domain"
            )
    for sd in src_doms:
        for dd in dst_doms - {sd}:
            a, b = domain(model, sd), domain(model, dd)
            if a and b and a["kind"] != "project" and b["kind"] != "project":
                warnings.append(f"Connection {name}: crosses {a['name']} → {b['name']} (allowed, but on purpose?)")


# ------------------------------------------------------------------ access overview
def _covering(model: dict, ref: str, nodes_by_id: dict[int, dict]) -> set[str]:
    """All references that include ``ref`` (itself, its user, domain, site, groups)."""
    kind, _, key = ref.partition(":")
    out = {ref}
    if kind == "node" and key.isdigit() and int(key) in nodes_by_id:
        node = nodes_by_id[int(key)]
        user = node_user(node)
        if user and not node_tags(node) and user_domain(model, user):
            out.add(f"user:{user}")
        d = node_domain(model, node)
        if d and not node_location(model, node):
            out.add(f"domain:{d}")
        loc = node_location(model, node)
        if loc:
            out.add(f"edge:{loc}")
    if kind == "user":
        d = user_domain(model, key)
        if d:
            out.add(f"domain:{d}")
    if kind == "dev":
        dev = device(model, key)
        if dev and dev.get("location"):
            out.add(f"loc:{dev['location']}")
    for g in model.get("groups", []):
        if out & set(g.get("members", [])):
            out.add(f"group:{g['id']}")
    return out


def access(model: dict, ref: str, nodes_by_id: dict[int, dict]) -> dict:
    """What ``ref`` may reach (outgoing) and who may reach it (incoming), per connection."""
    cover = _covering(model, ref, nodes_by_id)
    outgoing, incoming = [], []
    for c in model["connections"]:
        row = {
            "id": c["id"],
            "name": c.get("name"),
            "enabled": c.get("enabled", True),
            "ports": expand_ports(model, c["ports"]),
        }
        if cover & set(as_list(c["src"])):
            outgoing.append({**row, "refs": as_list(c["dst"]), "via": sorted(cover & set(as_list(c["src"])))})
        if cover & set(as_list(c["dst"])):
            incoming.append({**row, "refs": as_list(c["src"]), "via": sorted(cover & set(as_list(c["dst"])))})
    doms = ref_domains(model, ref, nodes_by_id)
    internal = [d for d in doms if (domain(model, d) or {}).get("internal") == "full"]
    return {"ref": ref, "outgoing": outgoing, "incoming": incoming, "internal": internal}


# ------------------------------------------------------------------ mutations
COLLECTIONS = {
    "domain": "domains",
    "location": "locations",
    "device": "devices",
    "connection": "connections",
    "group": "groups",
    "profile": "port_profiles",
}


def _bump(model: dict) -> None:
    model["revision"] = int(model.get("revision", 0)) + 1
    model["changed_at"] = int(time.time())


def apply_change(model: dict, kind: str, action: str, data: dict) -> tuple[dict, str]:
    """Return a changed copy of the model and a human summary (for the audit log)."""
    m = copy.deepcopy(model)
    m.setdefault("groups", [])
    m.setdefault("port_profiles", [])
    if kind == "noderole":
        node_id, role = str(data.get("id")), str(data.get("role") or "")
        if not node_id.isdigit():
            raise ModelError("Unknown device")
        roles = m.setdefault("node_roles", {})
        if role in ROLES:
            roles[node_id] = role
        elif role in ("", "auto"):
            roles.pop(node_id, None)
        else:
            raise ModelError(f"Unknown device type {role}")
        _bump(m)
        return m, f"device {node_id} type {role or 'auto'}"
    coll = COLLECTIONS.get(kind)
    if coll is None:
        raise ModelError(f"Unknown object type {kind}")
    items = m[coll]

    if action == "delete":
        key = str(data.get("id"))
        old = next((x for x in items if x["id"] == key), None)
        if old is None:
            raise ModelError(f"{kind} {key} not found")
        _check_unused(m, kind, key)
        m[coll] = [x for x in items if x["id"] != key]
        _cascade_delete(m, kind, key, old)
        _bump(m)
        return m, f"{kind} {old.get('name') or key} deleted"

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
        before = items[idx]
        items[idx] = {**before, **obj}
        if kind == "domain":
            gone = set(before.get("users", [])) - set(obj["users"])
            _drop_refs(m, {f"user:{u}" for u in gone})
    _bump(m)
    label = obj.get("name") or obj["id"]
    if kind == "connection":
        label = (
            f"{label} ({', '.join(obj['src'])} → {', '.join(obj['dst'])}; {', '.join(obj['ports'])}; "
            f"{'on' if obj['enabled'] else 'off'})"
        )
    return m, f"{kind} {label} {action}d"


def _check_unused(m: dict, kind: str, key: str) -> None:
    if kind == "group":
        ref = f"group:{key}"
        used = [c.get("name") or c["id"] for c in m["connections"] if ref in as_list(c["src"]) + as_list(c["dst"])]
        if used:
            raise ModelError(f"This group is used by: {', '.join(used)}. Change those connections first.")
    if kind == "profile":
        ref = f"profile:{key}"
        used = [c.get("name") or c["id"] for c in m["connections"] if ref in as_list(c["ports"])]
        if used:
            raise ModelError(f"This port profile is used by: {', '.join(used)}. Change those connections first.")
    if kind == "domain" and any(loc["domain"] == key for loc in m["locations"]):
        raise ModelError("Delete the locations of this domain first")


def _drop_refs(m: dict, refs: set[str]) -> None:
    """Remove references to deleted things; connections left without source or destination go too."""
    if not refs:
        return
    for g in m.get("groups", []):
        g["members"] = [x for x in g.get("members", []) if x not in refs]
    kept = []
    for c in m["connections"]:
        c["src"] = [x for x in as_list(c["src"]) if x not in refs]
        c["dst"] = [x for x in as_list(c["dst"]) if x not in refs]
        if c["src"] and c["dst"]:
            kept.append(c)
    m["connections"] = kept


def _cascade_delete(m: dict, kind: str, key: str, old: dict) -> None:
    if kind == "domain":
        _drop_refs(m, {f"domain:{key}"} | {f"user:{u}" for u in old.get("users", [])})
    if kind == "location":
        devs = [d for d in m["devices"] if d.get("location") == key]
        m["devices"] = [d for d in m["devices"] if d.get("location") != key]
        _drop_refs(m, {f"loc:{key}", f"edge:{key}"} | {f"dev:{d['id']}" for d in devs})
    if kind == "device":
        _drop_refs(m, {f"dev:{key}"})


def _text(data: dict, key: str, default: str = "", limit: int = 64) -> str:
    return str(data.get(key) if data.get(key) is not None else default).strip()[:limit]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", text.lower()).strip("-")[:20] or new_id("p")


def _build(m: dict, kind: str, data: dict, creating: bool) -> dict:
    if kind == "domain":
        users = data.get("users", [])
        if isinstance(users, str):
            users = [u for u in re.split(r"[,\s]+", users) if u]
        obj = {
            "id": _text(data, "id").lower(),
            "name": _text(data, "name") or _text(data, "id"),
            "kind": LEGACY_KINDS.get(_text(data, "kind", "project"), _text(data, "kind", "project")),
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
        local = _text(data, "local_subnet", "192.168.1.0/24")
        vpn = _text(data, "vpn_subnet") or suggest_vpn_subnet(m, number, local)
        loc_id = _text(data, "id").lower() or (f"loc{number:02d}" if number else "")
        if not creating:
            current = location(m, loc_id) or {}
            if current and data.get("domain") and data["domain"] != current.get("domain"):
                raise ModelError("A location cannot move to another domain; create a new one")
        return {
            "id": loc_id,
            "domain": _text(data, "domain") or (location(m, loc_id) or {}).get("domain", ""),
            "name": _text(data, "name") or loc_id,
            "number": number,
            "local_subnet": str(ipaddress.ip_network(local, strict=False)),
            "vpn_subnet": str(ipaddress.ip_network(vpn, strict=False)),
            "lan_iface": _text(data, "lan_iface", "eth0", 15),
            "note": _text(data, "note", "", 200),
        }
    if kind == "device":
        via = _text(data, "via").removeprefix("node:")
        loc = "" if via else _text(data, "location")
        return {
            "id": _text(data, "id") or new_id("d"),
            "location": loc,
            "via": via,
            "name": _text(data, "name") or _text(data, "ip"),
            "ip": str(ipaddress.IPv4Address(_text(data, "ip"))),
            "note": _text(data, "note", "", 200),
        }
    if kind == "group":
        name = _text(data, "name")
        if not name:
            raise ModelError("A group needs a name")
        return {
            "id": _text(data, "id") or new_id("g"),
            "name": name,
            "members": as_list(data.get("members")),
            "note": _text(data, "note", "", 200),
        }
    if kind == "profile":
        name = _text(data, "name")
        if not name:
            raise ModelError("A port profile needs a name")
        pid = _text(data, "id") or _slug(name)
        return {"id": pid, "name": name, "ports": parse_ports(data.get("ports"))}
    # connection
    return {
        "id": _text(data, "id") or new_id("c"),
        "name": _text(data, "name", "", 80),
        "src": as_list(data.get("src")),
        "dst": as_list(data.get("dst")),
        "ports": normalize_ports(m, data.get("ports")),
        "enabled": bool(data.get("enabled", True)),
        "note": _text(data, "note", "", 200),
    }
