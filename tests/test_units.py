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
    raw.update(kw)
    return Options(raw)


def test_options_overlap_rejected():
    with pytest.raises(OptionsError):
        opts(server_url="https://hs.vll6.duckdns.org", base_domain="vll6.duckdns.org").validate()
    with pytest.raises(OptionsError):
        opts(server_url="https://duckdns.org", base_domain="tailnet.duckdns.org").validate()
    opts(server_url="https://hs.vll6.duckdns.org", base_domain="tailnet.home").validate()


def test_options_tls_needs_https():
    with pytest.raises(OptionsError):
        opts(server_url="http://hs.example.org", tls_mode="letsencrypt").validate()
    opts(server_url="http://127.0.0.1:8080", tls_mode="none").validate()


def test_options_no_relays_rejected():
    with pytest.raises(OptionsError):
        opts(derp_enabled=False, tailscale_derp_fallback=False).validate()


def test_internal_url():
    assert opts(server_url="https://hs.x.org").internal_url == "https://hs.x.org"
    assert opts(server_url="https://hs.x.org", listen_port=8443).internal_url == "https://hs.x.org:8443"
    assert opts(server_url="http://a:1", tls_mode="none", listen_port=8080).internal_url == "http://127.0.0.1:8080"


def test_letsencrypt_warning_on_other_port():
    assert opts(server_url="https://hs.x.org:8443").warnings()
    assert not opts(listen_port=8443).warnings()
    assert not opts(listen_port=443).warnings()


def test_headscale_config_letsencrypt():
    cfg = headscale_config(opts(server_url="https://hs.vll6.duckdns.org/"), derp_cached=True)
    assert cfg["server_url"] == "https://hs.vll6.duckdns.org"
    assert cfg["tls_letsencrypt_hostname"] == "hs.vll6.duckdns.org"
    assert cfg["tls_letsencrypt_challenge_type"] == "TLS-ALPN-01"
    assert cfg["derp"]["urls"] == []  # never: download failures stop Headscale
    assert cfg["derp"]["paths"] == [str(derp.CACHE)]
    assert cfg["policy"]["mode"] == "database"
    assert cfg["node"]["expiry"] == "4320h"


def test_headscale_config_no_fallback_cache():
    cfg = headscale_config(opts(), derp_cached=False)
    assert cfg["derp"]["paths"] == []


def test_headplane_config():
    cfg = headplane_config(opts(server_url="https://hs.x.org"), "a" * 32)
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
    from hsha.wizard import Wizard

    assert Wizard.covers(["vll6.duckdns.org"], "vll6.duckdns.org")
    assert Wizard.covers(["*.vll6.duckdns.org"], "hs.vll6.duckdns.org")
    assert not Wizard.covers(["*.vll6.duckdns.org"], "a.b.vll6.duckdns.org")
    out = Wizard._coerce({"server_url": "HS.Vll6.duckdns.org/", "listen_port": "8443", "admin_user": "Tijn"})
    assert out == {"server_url": "https://hs.vll6.duckdns.org", "listen_port": 8443, "admin_user": "tijn"}
    with pytest.raises(ValueError):
        Wizard._coerce({"log_level": "debug"})


def test_options_configured_placeholder():
    assert not opts().configured
    assert opts(server_url="https://hs.vll6.duckdns.org").configured
