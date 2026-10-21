# Headscale for Home Assistant

A Home Assistant app (add-on) repository with a complete, self-hosted
[Tailscale](https://tailscale.com) control plane based on [Headscale](https://headscale.net):

- **Headscale** with native TLS: Let's Encrypt (TLS-ALPN-01) or a certificate from `/ssl`, with no reverse proxy
- **Embedded DERP relay + STUN**; Tailscale's relays as a cached fallback
- **Subnet router / exit node** inside the app, registered and approved automatically
- **[Headplane](https://github.com/tale/headplane)** admin UI on the LAN
- **Sidebar panel**: status, devices, auth keys, approving phone sign-ins, and
  **printer discovery** so you can print at home from anywhere

## Installation

1. Settings → Apps → App store → ⋮ → Repositories → add
   `https://github.com/studiotijn/headscale-ha`
   (private repository: `https://<read-only-token>@github.com/studiotijn/headscale-ha`)
2. Install **Headscale**, set `server_url`, start it.

Full documentation: [headscale/DOCS.md](headscale/DOCS.md).

## Why another Headscale app?

Lessons from existing apps:

| Problem in existing apps | Approach here |
| --- | --- |
| Requires Nginx Proxy Manager or another reverse proxy for TLS, which the Headscale maintainers don't support | Headscale terminates TLS itself on port 443 |
| No subnet router, or a separate Tailscale app that doesn't support Headscale | Built-in router, tagged key, routes auto-approved |
| Headplane squeezed into HA ingress (its `/admin` base path breaks there) | Headplane on its own LAN port; a separate ingress panel for daily tasks |
| Headscale doesn't start when the DERP map download fails (internet down at boot) | DERP map is cached locally and read from file |
| Generated config overwritten by the UI, or the UI overwritten by the config | Options are the source of truth for the server config; the ACL policy lives in the database; DNS records in a shared file |
| Unpinned `latest` images | Every upstream component pinned, Headscale binary checksum-verified |

## Development

```sh
pip install -r headscale/requirements.txt pytest ruff
ruff check . && pytest
docker build -t headscale-ha:test headscale && tests/smoke.sh headscale-ha:test
```

`tests/fake_printer.py` simulates an IPP printer announced over mDNS.

## License

MIT
