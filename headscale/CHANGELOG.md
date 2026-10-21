# Changelog

## 0.1.0

First prototype.

- Headscale 0.29.5 with native TLS (Let's Encrypt TLS-ALPN-01 or a certificate from `/ssl`).
- Embedded DERP relay with STUN, with a cached copy of Tailscale's DERP map as fallback.
  Headscale no longer fails to start when the internet is down at boot.
- Built-in Tailscale 1.104.2 subnet router (and optional exit node), registered with a tagged
  key and routes approved automatically.
- Headplane 0.8.1 on the LAN, running unprivileged.
- Ingress panel: status, devices, auth keys, approving browser sign-ins, printer discovery
  (mDNS + port scan) with MagicDNS names and IPP test.
- Initial ACL policy (admins: everything; others: own devices).
