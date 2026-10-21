# Headscale

Run your own [Tailscale](https://tailscale.com) control server on Home Assistant with
[Headscale](https://headscale.net). Use the official Tailscale apps on your phone and laptop
to reach Home Assistant, your home network and your printers from anywhere, without
exposing Home Assistant itself to the internet.

The app bundles:

| Component | Purpose |
| --- | --- |
| **Headscale** | Control server. Native TLS (Let's Encrypt or your `/ssl` certificate), no reverse proxy needed. |
| **Embedded DERP relay** | Relays traffic when two devices cannot connect directly. Tailscale's public relays are available as a fallback. |
| **Subnet router** | A Tailscale node inside the app that makes your LAN reachable. Registered and approved automatically. |
| **Headplane** | Full admin UI (users, ACL policy, DNS, machines) on your LAN. |
| **Panel in the sidebar** | Status, devices, one-click auth keys, approving phone sign-ins and printers. |

## Before you start

1. A hostname pointing to your home IP, e.g. `hs.yourname.duckdns.org`. With Duck DNS every
   sub-domain of your Duck DNS name points to the same IP, so you don't need to change anything.
2. Home Assistant must run 24/7. If it is down, devices that are already connected keep their
   direct connections for a while, but nothing new can sign in.

## Configuration

Minimal configuration:

```yaml
server_url: https://hs.yourname.duckdns.org
tls_mode: letsencrypt
base_domain: tailnet.home
admin_user: yourname
```

Important options:

- **`server_url`**: the public address. Don't change it after devices have joined; they
  would all have to sign in again.
- **`tls_mode`**:
  - `letsencrypt` (recommended): Headscale requests and renews its own certificate through the
    TLS-ALPN-01 challenge. Let's Encrypt connects to **port 443**, so external port 443 must reach
    `listen_port`.
  - `ha_certificate`: use `certfile`/`keyfile` from `/ssl`, for example from the Duck DNS app.
    The certificate must cover the `server_url` hostname.
  - `none`: plain HTTP for setups with your own reverse proxy. The proxy must pass WebSocket
    upgrades and must not buffer. The Headscale maintainers don't support this setup, so use it
    only if you know why you need it.
- **`base_domain`**: MagicDNS suffix for your devices (`laptop.tailnet.home`). It must not be the
  same as, or a parent or child of, the `server_url` domain.
- **`advertise_routes`**: leave empty to advertise the Home Assistant host's LAN automatically.
- **`exit_node`**: lets your phone send all internet traffic through home, which is handy on
  public Wi-Fi.

## Port forwarding

On your router, forward to the IP of the Home Assistant host:

| External | Internal | Protocol | Required for |
| --- | --- | --- | --- |
| 443 | `listen_port` (443) | TCP | Headscale, DERP relay, Let's Encrypt |
| `stun_port` (3478) | `stun_port` | UDP | DERP/STUN (NAT traversal) |
| 41641 | 41641 | UDP | optional: direct connections to the subnet router |

**Don't** forward the Headplane port (3000) or Home Assistant's 8123. Once everything works,
close any existing 8123 forward: you reach Home Assistant through the tailnet now.

At home your devices resolve `hs.yourname.duckdns.org` to your public IP. If your router doesn't
support NAT loopback (hairpinning), add a local DNS override that points that name to the
Home Assistant host.

## Setup wizard

Open the **Headscale** panel in the sidebar. As long as the setup is incomplete, the panel
opens on **Setup**. Every step is tested automatically and gets a green check mark; the ⓘ
button explains it. Settings you change there are saved as app options and the app restarts
by itself. You can also edit the options on the app's Configuration tab; the wizard reads the
same values.

**Let's Encrypt quota:** each certificate attempt that fails counts toward a limit of 5 per
hour per hostname, after which Let's Encrypt blocks it for an hour. Set up the port forwards
first, then use *Test certificate now*.

## First steps

1. Start the app and check the log for `Headscale ready`. Open the **Headscale** panel in
   the sidebar. Under *Subnet router* the state should be `Running`, with your LAN approved.
2. **Laptop / desktop**: *Devices → Create key*, then run the shown `tailscale up …` command.
3. **iPhone / Android**: set the custom coordination server in the Tailscale app
   (see the instructions in the panel) and sign in. The app opens a page with a registration
   command. Paste the page address or the command into *Approve a device*.
4. **Headplane**: *Overview → Create API key*, open Headplane and sign in with that key.

## ACL policy

On first start the app installs a policy where:

- members of `group:admins` (your `admin_user`) reach every device, your LAN and the exit node;
- other users only reach their own devices;
- the subnet router (`tag:homerouter`) gets its routes approved automatically.

After that the app never overwrites the policy. Edit it in Headplane → *Access Control*.

## Printers

mDNS/AirPrint discovery does not cross a VPN tunnel, so the panel discovers printers at home:

1. *Printers → Scan network* (mDNS; optionally also a port scan for 631/9100).
2. *Add* gives the printer a fixed name, e.g. `office-printer.tailnet.home`. If the printer is
   outside the advertised LAN (another VLAN), its address is added to the subnet router.
3. *Test* checks that it responds over IPP, and *How to connect* shows the address for each
   platform.

**iPhone/iPad:** AirPrint only finds printers through local discovery, so it does not work over
Tailscale. Use the manufacturer's app or an IPP printing app with the address shown.

## Security

- Headscale is the key to your network: whoever controls it can add devices that reach your LAN.
  Keep the app updated, protect your Home Assistant account with MFA, and keep backups. The app's
  data (database, keys) is included in Home Assistant backups, so store those somewhere safe.
- Only ports 443/TCP and 3478/UDP are exposed. Headplane and the panel are LAN and ingress only.
  The panel refuses requests that don't come through Home Assistant ingress.
- The subnet router gives tailnet devices access to your LAN as allowed by the ACL policy.
  Restrict the policy if you share the tailnet with others. Expire or delete lost devices
  immediately (*Devices → Log out / Delete*).
- Device keys expire after `node_expiry_days` (default 180).

## Troubleshooting

- **"Invalid configuration"**: the log names the option. A common cause is `base_domain`
  overlapping the server domain.
- **No certificate**: check that external port 443 reaches Home Assistant and that no other
  app uses port 443 on the host.
- **Headscale keeps restarting**: the app stops after 5 failed starts, so check the log.
  A port already in use by another app is a common cause.
- **Upgrades**: Headscale only supports upgrading one minor version at a time (0.29 → 0.30).
  This app follows that rule, so don't skip app versions that change the Headscale minor version.
