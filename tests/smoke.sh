#!/usr/bin/env bash
# Start the app image outside Home Assistant and check that all parts come up:
# Headscale, the subnet router registration + route approval, Headplane and the
# ingress guard. Usage: tests/smoke.sh <image>
set -euo pipefail

IMAGE="${1:?usage: $0 <image>}"
NAME="hsha-smoke-$$"
DATA="$(mktemp -d)"
LAN="10.99.0.0/24"

cleanup() {
    local rc=$?
    if [[ ${rc} -ne 0 ]]; then
        echo "::group::container log"
        docker logs "${NAME}" 2>&1 | tail -n 200 || true
        echo "::endgroup::"
        # Also as an annotation: readable through the API without downloading the log.
        local tail_log
        tail_log=$(docker logs "${NAME}" 2>&1 | tail -n 60 | sed 's/%/%25/g' | awk '{printf "%s%%0A", $0}')
        echo "::error title=Smoke test container log (last 60 lines)::${tail_log}"
    fi
    docker rm -f "${NAME}" >/dev/null 2>&1 || true
    sudo rm -rf "${DATA}" 2>/dev/null || rm -rf "${DATA}"
    exit "${rc}"
}
trap cleanup EXIT

cat > "${DATA}/options.json" <<JSON
{
  "server_url": "http://127.0.0.1:18080",
  "tls_mode": "none",
  "acme_email": "",
  "certfile": "fullchain.pem",
  "keyfile": "privkey.pem",
  "listen_port": 18080,
  "derp_enabled": true,
  "stun_port": 13478,
  "tailscale_derp_fallback": true,
  "base_domain": "tailnet.test",
  "nameservers": ["1.1.1.1"],
  "admin_user": "smoke",
  "node_expiry_days": 180,
  "subnet_router": true,
  "advertise_routes": [],
  "exit_node": true,
  "userspace_networking": true,
  "headplane": true,
  "headplane_port": 13000,
  "airprint_dns": true,
  "dns_via_home": false,
  "printer_domain": "printers.home.arpa",
  "log_level": "info"
}
JSON

docker run -d --name "${NAME}" --network host \
    -v "${DATA}:/data" \
    -e HSHA_LAN_CIDRS="10.99.0.1/24" \
    -e HSHA_INGRESS_PORT=18099 \
    "${IMAGE}" >/dev/null

hs() { docker exec "${NAME}" headscale -c /data/headscale/config.yaml "$@"; }

wait_for() {
    local what="$1" timeout="$2"; shift 2
    local deadline=$((SECONDS + timeout))
    until "$@" >/dev/null 2>&1; do
        if ((SECONDS > deadline)); then
            echo "FAIL: ${what}"
            echo "::error title=Smoke test failed::${what}"
            return 1
        fi
        sleep 2
    done
    echo "ok: ${what}"
}

router_approved() {
    hs nodes list -o json | python3 -c '
import json, sys
nodes = json.load(sys.stdin) or []
want = {"'"${LAN}"'", "0.0.0.0/0", "::/0"}
ok = any(want <= set(n.get("approved_routes") or []) and n.get("online") for n in nodes)
sys.exit(0 if ok else 1)'
}

wait_for "headscale health" 90 curl -fsS http://127.0.0.1:18080/health
wait_for "admin user created" 60 bash -c "docker exec ${NAME} headscale -c /data/headscale/config.yaml users list -o json | grep -q '\"smoke\"'"
wait_for "ACL policy installed" 60 bash -c "docker exec ${NAME} headscale -c /data/headscale/config.yaml policy get | grep -q homerouter"
wait_for "subnet router online with approved routes" 120 router_approved
wait_for "headplane responds" 90 curl -fsS -o /dev/null http://127.0.0.1:13000/admin/login

airprint_dns_answers() {
    docker exec "${NAME}" python3 -c '
import sys
from hsha import dnssd
r = dnssd.lookup("b._dns-sd._udp.printers.home.arpa", "PTR", "127.0.0.1", 53)
sys.exit(0 if r.get("ok") else 1)'
}
split_dns_pushed() {
    docker exec "${NAME}" grep -q "printers.home.arpa" /data/headscale/config.yaml
}
wait_for "printer DNS answers DNS-SD on 127.0.0.1:53" 60 airprint_dns_answers
wait_for "split DNS for the printer domain pushed to devices" 90 split_dns_pushed

code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18099/api/status)
if [[ "${code}" != "403" ]]; then
    echo "FAIL: ingress UI must refuse non-ingress clients (got ${code})"
    exit 1
fi
echo "ok: ingress guard"

node_version=$(docker exec "${NAME}" node --version)
if [[ ! "${node_version}" =~ ^v24\. ]]; then
    echo "FAIL: Headplane needs Node.js 24, image has ${node_version}"
    exit 1
fi
echo "ok: node ${node_version}"

docker exec "${NAME}" test -s /data/headscale/derp-tailscale.yaml && echo "ok: Tailscale DERP map cached"

echo "--- nodes"
hs nodes list
echo "Smoke test passed"
