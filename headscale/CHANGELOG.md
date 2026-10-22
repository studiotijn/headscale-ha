# Changelog

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
