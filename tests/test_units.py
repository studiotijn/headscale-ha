"""Unit tests for the pure-Python parts (run: pytest tests/)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "headscale/rootfs/usr/lib"))

from hsha import derp, ipp, printers
from hsha.options import DEFAULTS, Options, OptionsError
from hsha.policy import initial_policy
from hsha.render import headplane_config, headscale_config


def opts(**kw) -> Options:
    raw = dict(DEFAULTS)
    raw["tls_mode"] = "none"  # certificate handling is tested separately
    raw.update(kw)
    return Options(raw)


@pytest.fixture
def ssl_dir(tmp_path, monkeypatch):
    """A /ssl folder with a certificate for vll6.duckdns.org and *.vll6.duckdns.org."""
    import subprocess

    from hsha import paths

    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "30",
            "-keyout",
            str(tmp_path / "privkey.pem"),
            "-out",
            str(tmp_path / "fullchain.pem"),
            "-subj",
            "/CN=vll6.duckdns.org",
            "-addext",
            "subjectAltName=DNS:vll6.duckdns.org,DNS:*.vll6.duckdns.org",
        ],
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(paths, "SSL", tmp_path)
    return tmp_path


def test_options_overlap_rejected():
    with pytest.raises(OptionsError):
        opts(server_url="https://hs.vll6.duckdns.org", base_domain="vll6.duckdns.org").validate()
    with pytest.raises(OptionsError):
        opts(server_url="https://duckdns.org", base_domain="tailnet.duckdns.org").validate()
    opts(server_url="https://hs.vll6.duckdns.org", base_domain="tailnet.home").validate()


def test_options_tls_needs_https(ssl_dir):
    with pytest.raises(OptionsError):
        opts(server_url="http://hs.vll6.duckdns.org", tls_mode="ha_certificate").validate()
    opts(server_url="http://127.0.0.1:8080", tls_mode="none").validate()


def test_builtin_letsencrypt_removed():
    with pytest.raises(OptionsError, match="removed"):
        opts(server_url="https://hs.vll6.duckdns.org", tls_mode="letsencrypt").validate()


def test_certificate_must_cover_host(ssl_dir):
    opts(server_url="https://hs.vll6.duckdns.org", tls_mode="ha_certificate").validate()
    opts(server_url="https://vll6.duckdns.org:8443", tls_mode="ha_certificate").validate()
    with pytest.raises(OptionsError, match="not for"):
        opts(server_url="https://a.b.vll6.duckdns.org", tls_mode="ha_certificate").validate()
    with pytest.raises(OptionsError, match="not found"):
        opts(server_url="https://hs.vll6.duckdns.org", tls_mode="ha_certificate", certfile="x.pem").validate()


def test_certificate_inventory(ssl_dir):
    from hsha import certs

    inv = certs.inventory()
    assert [c["file"] for c in inv] == ["fullchain.pem"]
    assert inv[0]["names"] == ["vll6.duckdns.org", "*.vll6.duckdns.org"]
    assert inv[0]["keyfile"] == "privkey.pem"
    assert 28 <= inv[0]["days_left"] <= 30


def test_options_no_relays_rejected():
    with pytest.raises(OptionsError):
        opts(derp_enabled=False, tailscale_derp_fallback=False).validate()


def test_internal_url():
    assert opts(server_url="https://hs.x.org", tls_mode="ha_certificate").internal_url == "https://hs.x.org"
    assert (
        opts(server_url="https://hs.x.org", tls_mode="ha_certificate", listen_port=8443).internal_url
        == "https://hs.x.org:8443"
    )
    assert opts(server_url="http://a:1", tls_mode="none", listen_port=8080).internal_url == "http://127.0.0.1:8080"

    assert not opts(listen_port=443).warnings()


def test_headscale_config_certificate():
    cfg = headscale_config(opts(server_url="https://hs.vll6.duckdns.org/", tls_mode="ha_certificate"), derp_cached=True)
    assert cfg["server_url"] == "https://hs.vll6.duckdns.org"
    assert cfg["tls_cert_path"].endswith("/fullchain.pem")
    assert not any(k.startswith("tls_letsencrypt") or k.startswith("acme") for k in cfg)
    assert cfg["derp"]["urls"] == []  # never: download failures stop Headscale
    assert cfg["derp"]["paths"] == [str(derp.CACHE)]
    assert cfg["policy"]["mode"] == "database"
    assert cfg["node"]["expiry"] == "4320h"


def test_headscale_config_no_fallback_cache():
    cfg = headscale_config(opts(), derp_cached=False)
    assert cfg["derp"]["paths"] == []


def test_headplane_config():
    cfg = headplane_config(opts(server_url="https://hs.x.org", tls_mode="ha_certificate"), "a" * 32)
    assert cfg["headscale"]["url"] == "https://hs.x.org"
    assert cfg["server"]["cookie_secret"] == "a" * 32
    # Headplane validates every integration block that is present (0.8.1 crashed on
    # a disabled kubernetes block without pod_name), so none may be written.
    assert "integration" not in cfg


def test_initial_policy_is_json_after_comments():
    text = initial_policy("tijn", ["192.168.1.0/24"], True)
    body = "\n".join(line for line in text.splitlines() if not line.startswith("//"))
    pol = json.loads(body)
    assert pol["groups"]["group:admins"] == ["tijn@"]
    assert pol["autoApprovers"]["routes"] == {"192.168.1.0/24": ["tag:homerouter"]}
    assert {"action": "accept", "src": ["group:admins"], "dst": ["autogroup:internet:*"]} in pol["acls"]


def test_derp_convert():
    out = derp.convert({"Regions": {"1": {"RegionID": 1, "Nodes": [{"HostName": "a", "IPv4": "1.2.3.4"}]}}})
    assert out == {"regions": {1: {"regionid": 1, "nodes": [{"hostname": "a", "ipv4": "1.2.3.4"}]}}}
    with pytest.raises(ValueError):
        derp.convert({"Regions": {}})


def test_ipp_roundtrip():
    req = ipp.encode_get_printer_attributes("ipp://p:631/ipp/print", 7)
    assert req[:8] == bytes([2, 0, 0, 0x0B, 0, 0, 0, 7])
    _status, attrs = ipp.decode_response(req)
    assert attrs["printer-uri"] == ["ipp://p:631/ipp/print"]
    assert attrs["requested-attributes"][:2] == ["printer-name", "printer-make-and-model"]


def test_slugify():
    assert printers.slugify("Brother HL-L2350DW (Kantoor)") == "brother-hl-l2350dw-kantoor"
    assert printers.slugify("Ëpson ÉT-2850") == "epson-et-2850"
    assert printers.slugify("!!!") == "printer"


def test_merge_prefers_mdns_and_ipp():
    entries = [
        {"ip": "192.168.1.5", "port": 9100, "protocol": "raw", "name": "x", "model": None, "source": "sweep"},
        {"ip": "192.168.1.5", "port": 631, "protocol": "ipps", "name": "HP", "model": "HP M15", "source": "mdns"},
        {"ip": "192.168.1.5", "port": 631, "protocol": "ipp", "name": "HP", "model": "HP M15", "source": "mdns"},
    ]
    merged = printers.merge(entries)
    assert len(merged) == 1
    assert merged[0]["protocol"] == "ipp"
    assert set(merged[0]["protocols"]) == {"ipp", "ipps", "raw"}


def test_wizard_covers_and_coerce():
    from hsha import certs
    from hsha.wizard import Wizard

    assert certs.covers(["vll6.duckdns.org"], "vll6.duckdns.org")
    assert certs.covers(["*.vll6.duckdns.org"], "hs.vll6.duckdns.org")
    assert not certs.covers(["*.vll6.duckdns.org"], "a.b.vll6.duckdns.org")
    out = Wizard._coerce({"server_url": "HS.Vll6.duckdns.org/", "listen_port": "8443", "admin_user": "Tijn"})
    assert out == {"server_url": "https://hs.vll6.duckdns.org", "listen_port": 8443, "admin_user": "tijn"}
    with pytest.raises(ValueError):
        Wizard._coerce({"log_level": "debug"})


def test_options_configured_placeholder():
    assert not opts(server_url=DEFAULTS["server_url"]).configured
    assert opts(server_url="https://hs.vll6.duckdns.org").configured


def test_probe_summary_elsewhere():
    from hsha.probe import PortTest

    t = PortTest(listen_port=443, external_port=443, stun_port=3478, test_ts_port=True, mode="auto", duration=1)
    t.checkhost = {"tcp_connected": True}
    t.hits.add("udp", 3478, "185.1.2.3")
    t.hits.add("tcp", 443, "192.168.6.1")  # hairpin only
    r = t._summarise([3478, 41641])
    assert r["tcp"]["status"] == "elsewhere"
    assert r["hairpin"] is True
    assert [u["status"] for u in r["udp"]] == ["ok", "not_seen"]
    t.hits.add("tcp", 443, "185.9.9.9")
    assert t._summarise([3478])["tcp"]["status"] == "ok"


def test_dnssd_zone():
    from dnslib import QTYPE, RCODE, DNSRecord
    from hsha.dnssd import Zone

    printers = [
        {
            "name": "Kantoor HP",
            "slug": "kantoor-hp",
            "ip": "192.168.6.50",
            "port": 631,
            "protocol": "ipp",
            "resource": "ipp/print",
            "model": "HP M15",
            "txt": {"URF": "W8,RS600"},
        },
        {"name": "Zolder", "slug": "zolder", "ip": "10.9.9.9", "port": 9100, "protocol": "raw"},
    ]
    z = Zone("printers.home.arpa").build(printers)

    def ask(name, qtype):
        return z.answer(DNSRecord.question(name, qtype))

    assert [str(r.rdata) for r in ask("b._dns-sd._udp.printers.home.arpa", "PTR").rr] == ["printers.home.arpa."]
    ptr = ask("_universal._sub._ipp._tcp.PRINTERS.home.arpa", "PTR")
    assert len(ptr.rr) == 1 and "Kantoor" in str(ptr.rr[0].rdata)
    assert {r.rtype for r in ptr.ar} == {QTYPE.SRV, QTYPE.TXT, QTYPE.A}  # extras for one round trip
    txt = ask("Kantoor HP._ipp._tcp.printers.home.arpa", "TXT").rr[0]
    assert b"URF=W8,RS600" in txt.rdata.data and b"pdl=application/pdf,image/urf,image/jpeg" in txt.rdata.data
    assert str(ask("kantoor-hp.printers.home.arpa", "A").rr[0].rdata) == "192.168.6.50"
    assert ask("zolder.printers.home.arpa", "A").header.rcode == RCODE.NXDOMAIN  # raw printers: no AirPrint
    assert z.inside(DNSRecord.question("x.printers.home.arpa").q.qname)
    assert not z.inside(DNSRecord.question("printers.home.arpa.evil.com").q.qname)


def test_dns_nameservers():
    from hsha.render import dns_nameservers

    o = opts(airprint_dns=True)
    assert dns_nameservers(o, None) == {"global": ["1.1.1.1", "9.9.9.9"], "split": {}}
    assert dns_nameservers(o, "100.64.0.1")["split"] == {"printers.home.arpa": ["100.64.0.1"]}
    assert dns_nameservers(opts(dns_via_home=True), "100.64.0.1")["global"] == ["100.64.0.1"]


def test_hujson_and_shares():
    from hsha.policy import apply_shares, strip_hujson

    text = """// comment
    {
      "groups": {"group:admins": ["tijn@"],},  // trailing comma
      /* block */ "acls": [
        {"action": "accept", "src": ["group:admins"], "dst": ["*:*"]},
        {"action": "accept", "src": ["autogroup:member"], "dst": ["hsha-old:80"]},
      ],
      "hosts": {"nas": "192.168.6.10/32", "hsha-old": "192.168.6.99/32"},
      "note": "keep // this and /* this */",
    }"""
    pol = json.loads(strip_hujson(text))
    assert pol["note"] == "keep // this and /* this */"
    new = apply_shares(pol, [{"slug": "plex", "ip": "192.168.6.20", "ports": [32400]}])
    assert new["hosts"] == {"nas": "192.168.6.10/32", "hsha-plex": "192.168.6.20/32"}
    assert {"action": "accept", "src": ["group:admins"], "dst": ["*:*"]} in new["acls"]
    assert {"action": "accept", "src": ["autogroup:member"], "dst": ["hsha-plex:32400"]} in new["acls"]
    assert not any("hsha-old" in str(a) for a in new["acls"])
    assert "hosts" not in apply_shares({"acls": []}, [])


def test_make_service_and_fingerprint():
    from hsha.services import _prusa_fingerprint, make_service

    s = make_service({"kind": "plex", "ip": " 192.168.6.20 ", "name": "Plex"}, {"plex"})
    assert s["slug"] == "plex-2" and s["ports"] == [32400] and s["ip"] == "192.168.6.20"
    with pytest.raises(ValueError):
        make_service({"kind": "nas", "ip": "1.2.3.4"}, set())
    assert _prusa_fingerprint({"Server": "PrusaLink"}, "") == "PrusaLink"
    assert _prusa_fingerprint({}, "<title>Buddy3D</title>") == "Buddy3D camera"
    assert _prusa_fingerprint({}, "<title>Router</title>") is None
