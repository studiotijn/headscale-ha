# Headscale HA - Home Assistant App

[![Add repository to my Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fstudiotijn%2Fheadscale-ha)

A Home Assistant app (add-on) that runs [Headscale](https://headscale.net), a self-hosted
[Tailscale](https://tailscale.com) control server, together with a subnet router, a DERP relay
and the [Headplane](https://github.com/tale/headplane) admin UI.

## What is this?

This app turns your Home Assistant device into a Tailscale-compatible control plane for your own
private mesh VPN, managed from the Home Assistant sidebar. You keep using the official Tailscale
apps on your phone, laptop and PC, but they sign in to your own server instead of Tailscale's.

Headscale serves HTTPS itself on port 443 with the certificate of the Let's Encrypt or Duck DNS
app. No reverse proxy is needed and Home Assistant itself does not have to be exposed. A setup
wizard tests every step, from DNS and port forwards to the certificate as your devices see it.

## Features

- **Headscale** with TLS on port 443, using the certificate from `/ssl`. Restarts by itself when
  the certificate is renewed, and warns (also as a Home Assistant notification) when the
  certificate is not renewed on schedule.
- **Embedded DERP relay + STUN**, with Tailscale's public relays as an optional fallback.
- **Subnet router and exit node** built in: registered and approved automatically, so your home
  LAN is reachable from anywhere.
- **Headplane**: full admin UI for users, ACL policy, DNS and machines, on its own LAN port.
- **Setup wizard** with a test per step and a progress bar on the overview. Red segments show
  what stopped working; steps you don't need can be ignored. The card hides itself after an
  hour at 100% and comes back when something breaks.
- **Sidebar panel** for daily tasks: devices and keys, approving phone sign-ins, routes.
- **Printers over the VPN**: discovery, a fixed name per printer in the tailnet and AirPrint
  for iPhone/iPad (DNS-SD or a profile).
- **Home network assistants** for UniFi Protect, Prusa and Plex.
- **Multi-tenant networks** (optional): separated networks as *domains* (connected inside) or
  *clusters* (closed inside), with a connections editor, a network map, port profiles and
  gateways for sites.
- **Backup support**: all data is under `/data` and included in Home Assistant backups.
- **Pinned components**: every upstream part has a fixed version; the Headscale binary is
  checksum-verified.

## Installation

Click the button above, or add the repository manually:

1. In Home Assistant, go to **Settings → Apps → App store**.
2. Click the **⋮** menu (top right) → **Repositories**.
3. Add `https://github.com/studiotijn/headscale-ha`.
4. Install **Headscale** and start it.
5. Open **Headscale** in the sidebar and follow the setup wizard.

The button only works while the repository is public. For a private repository add
`https://<read-only-token>@github.com/studiotijn/headscale-ha` in step 3.

## Requirements

- Home Assistant OS or Supervised, running 24/7.
- A domain name, e.g. a free Duck DNS name.
- A certificate in `/ssl` from the **Let's Encrypt** app (DNS challenge, no open port needed)
  or the **Duck DNS** app.
- Port forwards on your router to Home Assistant: 443/TCP and 3478/UDP
  (41641/UDP optional, for direct connections to the subnet router).

## Configuration

The setup wizard fills in and tests these options; they are also on the app's *Configuration* tab.

| Option | Description |
| --- | --- |
| `server_url` | Public Headscale URL, e.g. `https://hs.yourname.duckdns.org` |
| `tls_mode` | `ha_certificate` (certificate from `/ssl`, recommended) or `none` (behind your own proxy) |
| `certfile` / `keyfile` | Certificate files in `/ssl` |
| `listen_port` | HTTPS port of Headscale and the DERP relay (default `443`) |
| `derp_enabled` / `stun_port` | Embedded DERP relay and its STUN port (default `3478`/UDP) |
| `tailscale_derp_fallback` | Also offer Tailscale's public relays |
| `base_domain` | MagicDNS domain of the tailnet (default `tailnet.home`) |
| `nameservers` | DNS servers pushed to devices |
| `admin_user` | Headscale user for devices added from the panel |
| `node_expiry_days` | Devices sign in again after this many days (default `180`) |
| `subnet_router` / `advertise_routes` | Make the home LAN reachable; empty = the Home Assistant LAN |
| `exit_node` | Allow all internet traffic of devices through home |
| `userspace_networking` | Subnet router without a kernel interface (recommended) |
| `headplane` / `headplane_port` | Headplane admin UI on the LAN (default port `3000`) |
| `airprint_dns` / `printer_domain` | AirPrint via VPN (DNS-SD) |
| `dns_via_home` | Send all DNS of tailnet devices to Home Assistant (e.g. AdGuard) |
| `multi_tenant` | Separated networks and the *Networks* tab (default off) |
| `log_level` | `trace`, `debug`, `info`, `warn`, `error` |

Full documentation: [headscale/DOCS.md](headscale/DOCS.md).

## Supported Architectures

- `amd64` (x86-64, e.g. a mini PC or NUC)
- `aarch64` (Raspberry Pi 4/5, Home Assistant Green/Yellow, ARM servers)

## License

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for the bundled third-party software.
Development notes: [CONTRIBUTING.md](CONTRIBUTING.md).
