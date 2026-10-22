# Development

```sh
pip install -r headscale/requirements.txt pytest ruff
ruff check . && pytest
docker build -t headscale-ha:test headscale && tests/smoke.sh headscale-ha:test
```

- **`tests/smoke.sh`** starts the image and checks Headscale, the subnet router, Headplane and the
  ingress guard.
- **`tests/test_multitenant.py`** tests the policy generator. With `headscale` on the `PATH`, the
  generated policy is also checked by the real Headscale.
- **`tests/edge_dataplane.sh`** checks the generated Edgebox firewall (NAT + allowlist) with real
  packets in a network namespace. Use `sudo` where unprivileged user namespaces are blocked.
- **`tests/fake_printer.py`** and **`tests/fake_devices.py`** simulate printers and home-network
  devices.

## Design choices

| Problem in existing Headscale apps | Approach here |
| --- | --- |
| Requires a reverse proxy for TLS, which the Headscale maintainers don't support | Headscale terminates TLS itself on port 443 |
| No subnet router, or a separate Tailscale app that doesn't support Headscale | Built-in router, tagged key, routes auto-approved |
| Headplane squeezed into HA ingress (its `/admin` base path breaks there) | Headplane on its own LAN port; a separate ingress panel for daily tasks |
| Headscale doesn't start when the DERP map download fails | DERP map is cached locally and read from file |
| Configuration by trial and error | Setup wizard that tests DNS, ports, certificate and TLS from the internet |
| Unpinned `latest` images | Every upstream component pinned, Headscale binary checksum-verified |
