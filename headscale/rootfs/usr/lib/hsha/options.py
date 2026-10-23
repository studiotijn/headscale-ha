"""App options (/data/options.json) with defaults and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from . import paths
from .store import read_json

DEFAULTS = {
    "server_url": "https://hs.example.duckdns.org",
    "tls_mode": "ha_certificate",
    "certfile": "fullchain.pem",
    "keyfile": "privkey.pem",
    "listen_port": 443,
    "derp_enabled": True,
    "stun_port": 3478,
    "tailscale_derp_fallback": True,
    "base_domain": "tailnet.home",
    "nameservers": ["1.1.1.1", "9.9.9.9"],
    "admin_user": "home",
    "node_expiry_days": 180,
    "subnet_router": True,
    "advertise_routes": [],
    "exit_node": False,
    "userspace_networking": True,
    "headplane": True,
    "headplane_port": 3000,
    "airprint_dns": False,
    "dns_via_home": False,
    "multi_tenant": False,
    "printer_domain": "printers.home.arpa",
    "log_level": "info",
}


class OptionsError(ValueError):
    """Raised for option combinations that cannot work."""


@dataclass
class Options:
    raw: dict = field(default_factory=dict)

    def __getattr__(self, name: str):
        try:
            return self.raw[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    @property
    def server_host(self) -> str:
        return (urlsplit(self.server_url).hostname or "").lower()

    @property
    def server_url_clean(self) -> str:
        return self.server_url.rstrip("/")

    @property
    def tls(self) -> bool:
        return self.tls_mode in ("letsencrypt", "ha_certificate")

    @property
    def internal_url(self) -> str:
        """URL local processes use to reach Headscale (via loopback)."""
        if self.tls:
            port = "" if self.listen_port == 443 else f":{self.listen_port}"
            return f"https://{self.server_host}{port}"
        return f"http://127.0.0.1:{self.listen_port}"

    @property
    def configured(self) -> bool:
        """False while server_url still holds the placeholder from the defaults."""
        host = self.server_host
        return bool(host) and "example" not in host.split(".")

    @property
    def external_port(self) -> int:
        """Port clients (and the router's port forward) use from the internet."""
        url = urlsplit(self.server_url)
        return url.port or (443 if url.scheme == "https" else 80)

    def warnings(self) -> list[str]:
        out = []
        if not self.derp_enabled and self.tailscale_derp_fallback:
            out.append("Embedded DERP disabled: relayed traffic goes through Tailscale's public DERP servers.")
        if self.raw.get("multi_tenant") and self.dns_via_home:
            out.append(
                "dns_via_home is ignored in multi-tenant mode: it would send the DNS of every domain "
                "(work, clients) to your home network."
            )
        return out

    def validate(self) -> None:
        url = urlsplit(self.server_url)
        host = self.server_host
        if url.scheme not in ("http", "https") or not host:
            raise OptionsError(f"server_url '{self.server_url}' must be http(s)://hostname[:port]")
        if self.tls and url.scheme != "https":
            raise OptionsError(f"tls_mode '{self.tls_mode}' requires an https:// server_url")
        base = self.base_domain.lower().strip(".")
        if host == base or host.endswith("." + base) or base.endswith("." + host):
            raise OptionsError(
                f"base_domain '{base}' must not overlap with the server_url host '{host}'. "
                "Use something like 'tailnet.home'."
            )
        if not self.derp_enabled and not self.tailscale_derp_fallback:
            raise OptionsError(
                "Both the embedded DERP server and the Tailscale DERP fallback are disabled; "
                "clients behind NAT would not be able to connect. Enable at least one."
            )
        if self.tls_mode == "letsencrypt":
            raise OptionsError(
                "The built-in Let's Encrypt mode has been removed. Let the Let's Encrypt or Duck DNS app "
                "create the certificate and choose tls_mode ha_certificate (the setup wizard helps)."
            )
        if self.tls_mode == "ha_certificate":
            from .certs import check

            problem = check(self.certfile, self.keyfile, host)
            if problem:
                raise OptionsError(problem)
        if self.headplane and self.headplane_port in (self.listen_port, 19090, 50443):
            raise OptionsError("headplane_port clashes with another port used by this app")


def load() -> Options:
    raw = dict(DEFAULTS)
    raw.update({k: v for k, v in read_json(paths.OPTIONS, {}).items() if v is not None})
    raw["base_domain"] = str(raw["base_domain"]).lower().strip(".")
    raw["admin_user"] = str(raw["admin_user"]).lower()
    return Options(raw)
