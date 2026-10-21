# Changelog

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
