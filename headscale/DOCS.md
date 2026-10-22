# Headscale

Run your own [Tailscale](https://tailscale.com) control server on Home Assistant with
[Headscale](https://headscale.net). Use the official Tailscale apps on your phone and laptop
to reach Home Assistant, your home network and your printers from anywhere, without
exposing Home Assistant itself to the internet.

The app bundles:

| Component | Purpose |
| --- | --- |
| **Headscale** | Control server. Serves HTTPS itself with the certificate from `/ssl`, no reverse proxy needed. |
| **Embedded DERP relay** | Relays traffic when two devices cannot connect directly. Tailscale's public relays are available as a fallback. |
| **Subnet router** | A Tailscale node inside the app that makes your LAN reachable. Registered and approved automatically. |
| **Headplane** | Full admin UI (users, ACL policy, DNS, machines) on your LAN. |
| **Panel in the sidebar** | Status, devices, one-click auth keys, approving phone sign-ins and printers. |

## Before you start

1. **A certificate in `/ssl`**, made by the **Let's Encrypt** app or the **Duck DNS** app.
   This app does not request certificates itself.
   - Let's Encrypt app: use the DNS challenge (`dns: provider: dns-duckdns` with your Duck DNS
     token). No port needs to be open. Add `hs.yourname.duckdns.org` to `domains` if you want a
     separate name for Headscale. The app only runs briefly, so start it weekly with an
     automation to renew.
   - Duck DNS app: enable `lets_encrypt: accept_terms: true`. It keeps running and renews by itself.
   When the certificate is renewed, this app restarts Headscale by itself.
2. Home Assistant must run 24/7. If it is down, devices that are already connected keep their
   direct connections for a while, but nothing new can sign in.

## Configuration

Run the **setup wizard** (Headscale panel → Setup). It fills in and tests everything below.

```yaml
server_url: https://hs.yourname.duckdns.org   # must be covered by the certificate
tls_mode: ha_certificate
certfile: fullchain.pem
keyfile: privkey.pem
base_domain: tailnet.home
admin_user: yourname
```

- **`server_url`**: the public address. Don't change it after devices have joined; they
  would all have to sign in again.
- **`tls_mode`**: `ha_certificate` (recommended), or `none` behind your own reverse proxy.
  With `none` the proxy must pass WebSocket upgrades and must not buffer.
- **`base_domain`**: MagicDNS suffix for your devices (`laptop.tailnet.home`). It must not be the
  same as, or a parent or child of, the `server_url` domain.
- **`advertise_routes`**: leave empty to advertise the Home Assistant host's LAN automatically.
- **`exit_node`**: lets your phone send all internet traffic through home.

## Port forwarding

On your router, forward to the IP of the Home Assistant host:

| External | Internal | Protocol | Required for |
| --- | --- | --- | --- |
| 443 | `listen_port` (443) | TCP | Headscale and the DERP relay |
| `stun_port` (3478) | `stun_port` | UDP | DERP/STUN (NAT traversal) |
| 41641 | 41641 | UDP | optional: direct connections to the subnet router |

**Don't** forward the Headplane port (3000).

At home your devices resolve `hs.yourname.duckdns.org` to your public IP. If your router doesn't
support NAT loopback (hairpinning), add a local DNS override that points that name to the
Home Assistant host.

## Setup wizard

Open the **Headscale** panel in the sidebar. As long as the setup is incomplete, the panel
opens on **Setup**. Every step is tested automatically and gets a green check mark; the ⓘ
button explains it. Settings you change there are saved as app options and the app restarts
by itself. You can also edit the options on the app's Configuration tab; the wizard reads the
same values.

The wizard tests as much as possible itself: DNS against your public IP, a port-by-port test
from the internet (through check-host.net nodes, or your phone on mobile data), the certificate
as clients see it, HTTPS from the internet, the subnet router and your first device.

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

**iPhone/iPad:** iOS normally finds AirPrint printers only on the local network. Install the
profile from *Printers → Download iPhone/iPad profile* (open the page in Safari): it adds every
IPP printer by IP address, so it shows up in the print menu over Tailscale too. Settings →
General → VPN & Device Management → install.

### A printer somewhere else (e.g. at work)

A PC at that location that runs Tailscale (logged in to this Headscale) can pass on the
printer's address:

1. On that PC: `tailscale set --advertise-routes=<printer-ip>/32` (list any routes it already
   advertises too; on Windows enable *Run unattended*). Ask your IT department first.
2. *Printers → Add manually*, choose that PC under *Reachable via*. The app approves exactly
   that /32 route on the PC and withdraws it again when you remove the printer.
3. Download the iPhone profile again, so it includes the new printer.

The printer's address must lie outside the home network. The app's own router does not use other
devices' routes, so *Test* checks the path (PC online, route advertised and approved); test the
printer itself from your phone.

### AirPrint via VPN (experimental)

Option `airprint_dns` (or the wizard step) publishes the added IPP printers via DNS-SD
under `printer_domain`. Apple devices browse that search domain and show the printers in the
normal print menu.

- **AdGuard Home on port 53:** add `[/printers.home.arpa/]127.0.0.1:15353` under
  AdGuard Home → Settings → DNS settings → Upstream DNS servers.
- **Nothing on port 53:** the app answers on port 53 itself and forwards other queries.

`dns_via_home` sends **all** DNS of tailnet devices to Home Assistant, which gives ad blocking
on the road. When home is down, DNS stops working on the road.

## Home network devices

The **Home network** tab has assistants for UniFi Protect, a Prusa printer/camera and Plex.
Each one finds the device, gives it a name such as `plex.tailnet.home`, tests the ports and
explains the settings in the device or app. *Share with all tailnet users* opens only that
device and its ports to every user of your tailnet. Admins always have access.

## Multi-tenant networks (optional)

With the option `multi_tenant` one Headscale manages several **separated network domains**,
for example *Private* (home), *Dynteq* (work) and a client such as *SRS/SHP* with several sites.
Off by default; with the option off nothing below changes.

- **Domains.** A domain owns Headscale users (its people's laptops and phones) and tagged
  servers (`tag:<domain>-server`). Your existing `admin_user` becomes the *Private* domain, so
  existing devices keep working. Devices of different domains cannot reach each other.
- **Locations** (client sites). Each site has a Linux **Edgebox** (`tag:<domain>-<location>-edge`)
  behind the local router (e.g. a Teltonika RUTX50). All sites may use the *same* local subnet
  (e.g. `172.168.1.0/24`, the default of Seyond LiDARs): the Edgebox maps it 1:1 onto a unique
  VPN subnet, so local `172.168.1.y` at location *n* is `10.81.n.y` over the VPN. Headscale
  has no 4via6, so this mapping is what makes identical sites possible.
- **Connections.** Only explicit connections are allowed: from a device or all users of a
  domain, to a device at a site, a whole site subnet, the Edgebox itself (SSH) or a device in
  another domain, on given ports (`tcp:22`, `udp:2368`, `tcp:8000-8010`, `icmp`, `*`). Replies
  come back; nothing at a site can start a connection, and a client domain can never be a
  source towards another domain (the app refuses such a connection).
- **Apply.** Changes are pending until you press *Apply* (the first time: *Activate*; the hand-made
  policy is kept in `/data/hsha/policy-history/`). The app generates the whole ACL policy,
  including a `tests` block with the isolation rules; Headscale refuses a policy whose tests fail.
  Device changes (a new laptop for a client user) are re-applied automatically.
- **Edgebox.** *Locations → Edgebox key* gives a one-time `tailscale up` command with the right tag
  and route; *Firewall (nftables)* gives the NAT and an allowlist that only forwards the
  configured connections. Load it with `nft -f`, enable `net.ipv4.ip_forward`, and give the Edgebox
  its own firewall zone on the RUTX50. Download the firewall again after changing connections and
  run `conntrack -D -s 100.64.0.0/10` after revoking access.
- **Routes.** An Edgebox may only have the VPN subnet of its own location approved; anything else is
  withdrawn automatically and logged. Other unexpected routes show up as warnings.
- **Log.** Every change and applied policy is written to `/data/hsha/audit.jsonl` (in backups).
- **Policy owner.** In this mode the app owns the ACL policy. Changes made in Headplane are reported
  as drift and replaced on the next *Apply*. *Share* in the Home network tab and printers
  elsewhere apply to the Private domain only.
- `dns_via_home` is ignored in this mode (it would send the DNS of work and client devices home).
  Devices that use routes to sites need *accept routes* (`tailscale set --accept-routes`, default
  on Windows/macOS/mobile).

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
- **Port forward doubts**: Setup → *Port forwarding* → *Test ports automatically*. It shows per
  port whether the forward reaches this app, something else, or nothing.
- **Headscale keeps restarting**: the app stops after 5 failed starts, so check the log.
  A port already in use by another app is a common cause.
- **Upgrades**: Headscale only supports upgrading one minor version at a time (0.29 → 0.30).
  This app follows that rule, so don't skip app versions that change the Headscale minor version.
