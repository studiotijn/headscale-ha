# Headscale HA - Home Assistant App

[![Add App repository to my Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fstudiotijn%2Fheadscale-ha)

A Home Assistant app (add-on) that turns your Home Assistant into a complete, self-hosted
[Tailscale](https://tailscale.com) control plane based on [Headscale](https://headscale.net).
A setup wizard guides and tests every step. You can then reach your home network, printers,
cameras and media from anywhere, and optionally manage separate networks for work and clients.

## What is this?

Tailscale builds a private, encrypted mesh VPN between your devices. Normally the control server
is run by Tailscale Inc.; Headscale is an open-source replacement you host yourself. This app runs
Headscale on Home Assistant, together with everything around it: certificate, relay server,
subnet router, admin UI and a sidebar panel. You use the official Tailscale apps on your phone,
laptop and PC.

No reverse proxy and no open Home Assistant port are needed. Headscale serves HTTPS itself on
port 443 with the certificate of the Let's Encrypt or Duck DNS app.

## Features

### VPN control plane

- **Headscale** with TLS on port 443, using the certificate from `/ssl`. It restarts by itself
  when that certificate is renewed.
- **Embedded DERP relay + STUN** for devices that cannot connect directly. Tailscale's public
  relays are available as a fallback; their map is cached locally, so Headscale also starts
  without internet.
- **Subnet router and exit node** inside the app. It is registered and approved automatically
  and makes your home LAN reachable. Optionally all internet traffic of your phone can go through
  home.
- **Headplane**, a full admin UI for users, ACL policy, DNS and machines, on its own LAN port.
- **Pinned and verified components.** Every upstream part is pinned to a version, and the
  Headscale binary is checksum-verified.

### Setup wizard with built-in tests

The *Setup* tab walks you through the installation. Each step is tested and gets a green check
mark; the ⓘ button explains it. Settings you change there are saved as app options and the app
restarts by itself.

| Step | What is tested |
| --- | --- |
| Certificate | Is a certificate present in `/ssl`, and does it cover your server name and is it not expired? |
| Address (DNS) | Does your Headscale name resolve to your public IP, and is there a sign of CGNAT? |
| Port forwarding | Port-by-port test from the internet (check-host.net nodes, or your phone on mobile data): does each forward reach this app, something else, or nothing? Also detects ports already in use on the host. |
| TLS | Is the certificate served exactly as clients see it (with SNI)? |
| From the internet | Can HTTPS be reached from outside? |
| Subnet router | Is the router registered, and are its routes approved? |
| First device | Has a device signed in? |
| Headplane, printers, AirPrint | Optional steps, each with its own check. |

If the configuration is wrong, the app does not crash. Headscale waits, and the wizard explains
what to fix.

### Sidebar panel

- **Overview:** status of Headscale, DERP and the subnet router. The update buttons are *Check
  for updates*, *Update* and *Rebuild* (installs the newest code for testing).
- **Devices:**
  - one-time or reusable keys, shown with the exact `tailscale up` command;
  - instructions for iPhone and Android;
  - approve a phone sign-in by pasting the link or command;
  - log out or delete a device, approve routes.
- **Printers:**
  - mDNS discovery and an optional port scan;
  - a fixed name in the tailnet (`office-printer.tailnet.home`) and an IPP test;
  - connect instructions per platform.
- **AirPrint:** printers show up in the normal print menu on iPhones, iPads and Macs, either
  through unicast DNS-SD or through an iPhone/iPad profile. A chain test shows which DNS
  settings the devices receive and which queries reach the app.
- **Printers elsewhere:** a printer at work can be reached through a Tailscale device at that
  location. The app approves that one route itself and withdraws it when you remove the printer.
- **Home network assistants:** find, add and test devices, then explain how to use them:
  - **UniFi Protect** (cameras via the console, RTSP(S) links);
  - **Prusa** (PrusaLink and camera);
  - **Plex** (custom server URL; traffic counts as local).
- **Share:** per device you can open only that device and its ports to all tailnet users.

### Multi-tenant networks (optional)

With the option `multi_tenant` one Headscale manages several **separated network domains**, for
example *Private*, *Work* and clients with several sites. Domains cannot reach each other; only
connections you create are allowed. You set this up in the *Networks* tab:

- **Connections editor.** Pick *From*, *To* and *Ports* with buttons and chips: users, devices,
  whole domains or groups, to devices, sites, Edgeboxes or groups. Edit any connection in place,
  turn it on or off with one click, or copy it. A plain-language sentence and a live check
  ("Looks right" or the reason it is refused) show the effect before you save.
- **Groups.** Group to group in one connection.
- **Port profiles.** SSH, Web, RDP, VNC, Modbus, OPC UA, MQTT and Ping are ready to use, and
  you can make your own. Change a profile and every connection that uses it follows.
- **Who can reach what?** Pick a user, device, group or site and see what it may reach and who may
  reach it, with a direct *Edit* link.
- **Client sites with an Edgebox.**
  - All sites may use the same local subnet. The Edgebox maps it 1:1, so local `172.168.1.y` at
    site *n* is `10.81.n.y` over the VPN.
  - One button gives the Edgebox's one-time sign-in command, another its firewall (nftables NAT
    and an allowlist).
- **Safe by construction:**
  - Sites and client domains can never start connections to other domains; the editor refuses it.
  - The generated ACL policy carries tests with the isolation rules, and Headscale refuses a
    policy whose tests fail.
  - Preview and *Apply* come first; a change made elsewhere is reported (drift detection).
  - Routes an Edgebox is not entitled to are withdrawn.
  - Everything is written to an audit log and a policy history.

### Backups and security

- **Backups:** all data (database, keys, settings, audit log) is under `/data` and is included
  in Home Assistant backups.
- **Panel:** reachable only through Home Assistant (ingress), so your Home Assistant login and MFA
  protect it.
- **Exposed ports:** only 443/TCP and 3478/UDP.

## Installation

Click the button above, or manually:

1. In Home Assistant, go to **Settings → Apps → App store**.
2. Click the **⋮** menu (top right) → **Repositories**.
3. Add `https://github.com/studiotijn/headscale-ha`. For a private repository, use
   `https://<read-only-token>@github.com/studiotijn/headscale-ha` (the button above only works
   for a public repository).
4. Install **Headscale** and start it.
5. Open **Headscale** in the sidebar and follow the setup wizard.

## Requirements

- **Home Assistant OS or Supervised**, running 24/7.
- **A domain name**, e.g. a free Duck DNS name.
- **A certificate in `/ssl`** from the **Let's Encrypt** app (DNS challenge, no open port needed)
  or the **Duck DNS** app.
- **Port forwards on your router:**
  - 443/TCP and 3478/UDP to Home Assistant;
  - 41641/UDP is optional, for direct connections to the subnet router.

## Configuration

The wizard fills in and tests these options. They are also on the app's *Configuration* tab.

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
| `multi_tenant` | Separated network domains and the *Networks* tab (default off) |
| `log_level` | `trace`, `debug`, `info`, `warn`, `error` |

Full documentation: [headscale/DOCS.md](headscale/DOCS.md).

## Supported architectures

- `amd64` (x86-64, e.g. a mini PC or NUC)
- `aarch64` (Raspberry Pi 4/5, Home Assistant Green/Yellow, ARM servers)

## Why another Headscale app?

| Problem in existing apps | Approach here |
| --- | --- |
| Requires Nginx Proxy Manager or another reverse proxy for TLS, which the Headscale maintainers don't support | Headscale terminates TLS itself on port 443 |
| No subnet router, or a separate Tailscale app that doesn't support Headscale | Built-in router, tagged key, routes auto-approved |
| Headplane squeezed into HA ingress (its `/admin` base path breaks there) | Headplane on its own LAN port; a separate ingress panel for daily tasks |
| Headscale doesn't start when the DERP map download fails (internet down at boot) | DERP map is cached locally and read from file |
| Configuration by trial and error | Setup wizard that tests DNS, ports, certificate and TLS from the internet |
| Unpinned `latest` images | Every upstream component pinned, Headscale binary checksum-verified |

## Development

```sh
pip install -r headscale/requirements.txt pytest ruff
ruff check . && pytest
docker build -t headscale-ha:test headscale && tests/smoke.sh headscale-ha:test
```

- **`tests/smoke.sh`** starts the image and checks Headscale, the subnet router, Headplane and the
  ingress guard.
- **`tests/test_multitenant.py`** tests the generator. With `headscale` on the `PATH`, the
  generated policy is also checked by the real Headscale.
- **`tests/edge_dataplane.sh`** checks the generated Edgebox firewall (NAT + allowlist) with real
  packets in a network namespace. Use `sudo` where unprivileged user namespaces are blocked.
- **`tests/fake_printer.py`** and **`tests/fake_devices.py`** simulate printers and home-network
  devices.

## License

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for the bundled third-party software.
