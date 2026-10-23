# Changelog

## 0.13.1

- **Fix: the panel could keep showing the previous version after an update.** The browser cached
  the scripts; they are now versioned and revalidated, so new features show up right away.

## 0.13.0

- **Network map** in *Networks → Who may reach what?*: every network is a circle with its users,
  devices and locations inside (locations as smaller circles with their Edgebox and equipment).
  Connections are arrows from the side that starts the connection to the destination; disabled
  connections are dashed. Click a network, location, user or device to see its access below the
  map; the arrows involved are highlighted.
- **Device lists grouped per network** (Devices tab and *Networks and devices*), sorted by
  location and name. Without networks, devices are grouped per Headscale user or tag.

## 0.12.3

- **Rename devices.** *Devices → Rename* changes the name a device has in the tailnet (and its
  MagicDNS name), e.g. to tell several Edgeboxes with the same hostname apart. The hostname on
  the device itself stays the same; the original hostname is shown below the name.

## 0.12.2

- **Take over a previous installation.** Installed the app again from the repository under
  another URL (e.g. without an access token)? On its first start it copies the data and options
  of the other Headscale app (through a temporary backup), so devices keep working. Stop the old
  app first, then uninstall it afterwards.

## 0.12.1

- **Fix: *Update* in the panel did nothing.** The Supervisor doesn't let an app update itself, so
  the panel now asks Home Assistant to install the update (the same as the button in Settings).
- A failed update or rebuild is now shown in the panel instead of only in the log.

## 0.12.0

- **Certificate renewal is monitored.** Every 15 minutes the app checks that the certificate in
  `/ssl` is renewed on schedule (when a third of its lifetime is left: 30 days for Let's Encrypt).
  About a week late, or close to expiry, the Certificate step turns amber or red and Home
  Assistant shows a notification; it disappears once the certificate is renewed. The step shows
  when renewal is expected and also warns when Headscale still serves an old certificate.
  The app now uses the Home Assistant API (`homeassistant_api`) for these notifications.
- **Progress bar per step.** Green is done; red means a step no longer works (it worked before
  and has been failing for 10 minutes) or fails; amber is a warning.
- **Ignore a step.** Every step that isn't done can be ignored. It no longer counts, so the bar is
  green at 100% again. *Count again* undoes it. This replaces *Skip* (skipped steps become ignored).
- **Hide the setup card on the overview.** With *Hide*, or automatically after an hour at 100%.
  It comes back as soon as something stops working.
- The setup checks also run in the background, so a step that breaks is noticed without opening
  the panel.
- README restructured; development notes moved to `CONTRIBUTING.md`.

## 0.11.0

- **Move a device to another network.** In a device's access panel (Networks), choose the
  network and *Move*. A personal device gets the other network's user as owner and keeps its
  name, IP address and keys; nothing has to be done on the device. Headscale has no command for
  this, so the app stops Headscale for a few seconds, changes the owner in its database (backup
  `db.sqlite.before-move`) and starts it again. Servers move by getting the other network's tag.
- API without networks: `POST /api/nodes/<id>/move {"user": "..."}`.

## 0.10.0

- **Generic names.** Multi-tenant mode starts with the networks *Private*, *Work* and *Project*
  (kinds private / work / project), without users except your admin user. Rename them, change
  them or add more. Existing installations keep their names; the kind `client` becomes `project`.
- **Device types.** Every VPN device is a *server*, *workstation* or *phone/tablet* (automatic,
  or set it yourself in the device dialog). Routers and Edgeboxes are recognised.
  - Pickers offer servers and equipment first as destinations, and people and their devices
    first as sources. Phones are not offered as destinations.
  - A connection to a workstation for anything other than remote desktop, VNC, SSH or file
    sharing gets a warning; so does one to a phone.
  - *Register as a server of this network*: the device gets the network's tag
    (`tag:<network>-server`), is no longer tied to a person and does not expire.
  - *Add a device* can create a key for a server of a network directly.
- In the app, "domain" is now called "network".
- The internal design document with example customer names was removed from the repository.

## 0.9.0

- **Networks tab always visible.** While access control is off it explains what it does and has
  a button *Enable access control* (sets the option `multi_tenant` and restarts the app).
- **Access per device.** *Devices → Access* (and every device row under *Networks*) opens one
  dialog per device:
  - group membership as on/off buttons;
  - what it may reach and who may reach it, with *Add access* and *Give access*;
  - **routing**: the addresses behind that device.
- **Opening a port sets the routing.** A device behind any VPN device (e.g. a printer or PLC
  behind the work PC) is added with its IP address. When a connection opens a port to it, the app
  approves exactly `<ip>/32` as a route on that device, and withdraws it again when the connection
  is switched off or removed. The rest of the network behind it is never routed.
  - The dialog shows per address whether the route is advertised and approved, the
    `tailscale set --advertise-routes=…` command when it is missing, and which connections open it.
  - Routes the device offers but nothing uses can be turned into an address with one click.

## 0.8.0

- **Networks tab, easy editing:** every connection, location, device, domain, group and port
  profile is edited in place in a dialog (no more delete and re-create).
  - Connections have several sources and destinations: users, devices, all users of a domain,
    groups → devices, whole sites, Edgeboxes, users, domains, groups.
  - **Groups** (group → group) and **port profiles** (SSH, Web, RDP, VNC, SMB, Modbus TCP, OPC UA,
    MQTT, Ping, plus your own); changing a profile changes every connection that uses it.
  - Port buttons plus free entry, a plain-language sentence, and a live check that shows why a
    connection would be refused before you save.
  - *Who can reach what?*: outgoing and incoming access of any user, device, group or site.
  - Sub-tabs, search, on/off switch and copy per connection.
- Edgebox firewall merges a host into a whole-site subnet in the same rule (nftables rejects overlaps).
- Connections from 0.7.0 are migrated automatically.
- README: *Add App repository to my Home Assistant* button and an overview of all features.

## 0.7.0

- **Multi-tenant networks (optional, option `multi_tenant`, off by default).** Separated network
  domains (private, work, clients) in one Headscale, managed in a new *Networks* tab:
  - Domains with their own users and tags; client locations with an Edgebox each. Sites may share
    one local subnet (e.g. 192.168.1.0/24); the Edgebox maps it 1:1 onto `10.81.<n>.0/24`.
  - Explicit connections (device / all users of a domain → device, site subnet, Edgebox, port list).
    Everything else is denied; sites and client domains can never start connections to other domains.
  - The ACL policy is generated (grants, hosts, autoApprovers) with a `tests` block holding the
    isolation rules, previewed and checked by Headscale before it is applied. Drift detection,
    automatic re-apply after device changes, audit log, policy history.
  - Edgebox: one-time tagged key + `tailscale up` command, generated nftables (NAT + allowlist).
    Routes outside the model are withdrawn from Edgeboxes.
  - Device keys and phone approvals per domain/user; route approval only for routes in the model.
- `headscale policy` errors now show every failed test.

## 0.6.0

- Printers elsewhere (e.g. at work): add manually with *Reachable via* a Tailscale device at that location. The app approves that /32 route on the device, withdraws it on removal, shows the route status and the command to run. Included in DNS names, AirPrint DNS-SD and the iPhone profile.

## 0.5.4

- iPhone profile opens in a new tab and is served inline, so iOS offers to install it; clearer install steps.

## 0.5.3

- iPhone/iPad profile (AirPrint payload) in the Printers tab: adds the printers by IP address, so they show up in the print menu over Tailscale even when iOS doesn't browse wide-area Bonjour over the VPN.

## 0.5.2

- AirPrint test also resolves each printer's own name (A record) through port 53 and directly, and explains when AdGuard is the one in the way (cache, rate limit).

## 0.5.1

- AirPrint step: shows which DNS settings Headscale pushes to devices, and the latest DNS
  queries that reached the printer DNS through the VPN. That shows whether an iPhone asks for
  printers at all.

## 0.5.0

- **Home network tab** with three separate assistants. Each one searches, adds the device
  under a fixed MagicDNS name, tests every port and explains how to use it:
  - **UniFi Protect:** finds the console by its Protect stream ports (7441/7447). Through the VPN
    the Protect app connects to the console directly; RTSP(S) links for VLC/Frigate.
  - **Prusa 3D printer + camera:** finds PrusaLink (web UI) and RTSP cameras such as the
    Buddy3D (`rtsp://<name>/live`).
  - **Plex:** finds servers with Plex's own GDM discovery and a port scan, and checks `/identity`.
    It gives the *Custom server access URL*. Traffic through the subnet router counts as local
    for Plex.
- **Share with all tailnet users:** per device, adds an ACL rule for only that device and its
  ports (managed `hsha-*` host aliases).
- The wizard step *Close port 8123* has been removed.

## 0.4.0

- **AirPrint via VPN (experimental, off by default):** iPhones, iPads and Macs find the added
  printers on the road through unicast DNS-SD ("wide-area Bonjour").
  - A small DNS server in the app publishes the printers under `printer_domain`
    (default `printers.home.arpa`), replaying each printer's own mDNS TXT record.
  - Headscale gives devices that search domain and sends its queries (split DNS) to the
    subnet router; Tailscale delivers them to port 53 of the Home Assistant host.
  - With AdGuard Home on port 53, AdGuard forwards only this domain to the app with the rule
    `[/printers.home.arpa/]127.0.0.1:15353`. Without it, the app listens on port 53 itself
    and forwards all other queries.
  - New wizard step with the AdGuard rule and a chain test.
- **All DNS via home (optional):** all tailnet DNS goes through AdGuard at home.

## 0.3.0

- **Certificates come from a separate app.** The built-in Let's Encrypt client has been removed.
  The Let's Encrypt or Duck DNS app puts the certificate in `/ssl`; they use the DNS challenge,
  which needs no open port and cannot be locked out by failed validations.
  - Wizard step *Certificate*: lists the certificates in `/ssl` (names, days left), the
    certificate apps and their state, and sets certificate + server address in one click.
  - The certificate must cover the server address; otherwise the app explains why.
  - Headscale restarts by itself when the certificate app renews the certificate.
  - Existing `tls_mode: letsencrypt` configurations go into setup mode with an explanation.
- **External port test, port by port:** the app pauses Headscale briefly and listens on
  443/TCP, 3478/UDP and 41641/UDP itself while check-host.net nodes connect to your public IP.
  It reports whether each forward reaches *this* app, reaches something else (for example
  Home Assistant on 8123), or is closed. It also reports whether NAT loopback works.
  Alternatively you can test with your phone on mobile data through a QR code.
- **External HTTPS test:** check-host.net nodes open `https://<server>/health`.
- The services read options from `/data/options.json` instead of the Supervisor API.
- App linter fixes (removed keys that only repeated the default).

## 0.2.1

- App version card on the overview with *Check for updates*, *Update* and *Rebuild*
  (*Rebuild* installs the newest code from GitHub even without a version bump, for quick tests).
  The app now uses the Supervisor role `manager` for this.
- Fix: Headplane polled Headscale every 30 s before a certificate existed, and every poll
  triggered a new Let's Encrypt attempt. With `letsencrypt`, Headplane now starts only once
  the certificate has been issued.

## 0.2.0

- Setup wizard in the sidebar panel: nine steps with automatic checks, green check marks,
  ⓘ explanations and a progress percentage on the overview.
  - Checks that the server address resolves to your public IP (and warns about CGNAT).
  - Port forwarding helper with a decision tree when port 443 is already in use: internal
    port 8443, another external port with a certificate from `/ssl`, or an existing reverse proxy.
  - Certificate test, an external test with a QR code for your phone, subnet router status
    (and a warning when the separate Tailscale app also runs), first device, Headplane,
    printers and closing port 8123.
  - Settings are saved through the Supervisor and the app restarts by itself.
- Setup mode: an empty or invalid configuration, or a port that is already in use, no longer
  stops the app. Headscale waits and the wizard explains what to fix.
- Fix: Headplane did not start (`integration.kubernetes.pod_name` missing).
- Fix: protect the Let's Encrypt quota. The subnet router only signs in once a valid
  certificate is served, and certificate checks are rare until the port forwards are confirmed.
  Before, every retry triggered a new validation, so Let's Encrypt blocked the hostname for an hour.
- Fix: finish scripts logged the service name as `.`.

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
