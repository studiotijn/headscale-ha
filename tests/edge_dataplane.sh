#!/usr/bin/env bash
# Data-plane test of the generated Edgebox firewall (NAT 10.81.<n>.y <-> 192.168.1.y + allowlist),
# without root: runs in a user + network namespace with veth pairs that stand in for
# tailscale0 and the LAN. Needs: unshare, nsenter, ip, nft, python3.
#   tests/edge_dataplane.sh
set -euo pipefail
if [[ "${1:-}" != "--inside" ]]; then
    here="$(cd "$(dirname "$0")" && pwd)"
    PYTHONPATH="${here}" python3 -c "
import test_multitenant as t
from hsha import policygen as pg
print(pg.edge_nftables(t.build(), 'loc01', t.ctx()).replace('\"eth1\"', '\"lan0\"'))" > /tmp/hsha-edge-test.nft
    exec unshare -Urn -f "$0" --inside
fi

ns() { unshare -n sleep 120 >/dev/null 2>&1 & echo $!; }
TS=$(ns); LAN=$(ns); sleep 0.5
in_ts() { nsenter -t "$TS" -n "$@"; }
in_lan() { nsenter -t "$LAN" -n "$@"; }

ip link add tailscale0 type veth peer name tsp && ip link set tsp netns "$TS"
ip link add lan0 type veth peer name lanp && ip link set lanp netns "$LAN"
ip addr add 100.64.0.6/32 dev tailscale0 && ip link set tailscale0 up && ip route add 100.64.0.0/10 dev tailscale0
ip addr add 192.168.1.2/24 dev lan0 && ip link set lan0 up
echo 1 > /proc/sys/net/ipv4/ip_forward
for a in 1 4 9; do in_ts ip addr add "100.64.0.${a}/32" dev tsp; done
in_ts sh -c 'ip link set tsp up; ip route add 100.64.0.6 dev tsp; ip route add 10.81.1.0/24 via 100.64.0.6 dev tsp onlink'
in_lan sh -c 'ip addr add 192.168.1.10/24 dev lanp; ip addr add 192.168.1.20/24 dev lanp; ip link set lanp up;
  ip route add 100.64.0.0/10 via 192.168.1.2'
nft -f /tmp/hsha-edge-test.nft

srv=()
for port in 22 80 8010; do
    in_lan python3 -c "
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('0.0.0.0', $port)); s.listen()
while True:
    c, a = s.accept(); c.sendall(c.getsockname()[0].encode()); c.close()" >/dev/null 2>&1 &
    srv+=($!)
done
sleep 1

fail=0
check() { # where src dst port expect(allow|block) [expected local address]
    local where=$1 src=$2 dst=$3 port=$4 want=$5 local=${6:-}
    got=$($where python3 -c "
import socket
s = socket.socket(); s.settimeout(1.5)
if '$src': s.bind(('$src', 0))
try:
    s.connect(('$dst', $port)); print('allow', s.recv(64).decode())
except OSError:
    print('block')")
    if [[ "$got" == "$want"* && ( -z "$local" || "$got" == *"$local" ) ]]; then
        echo "ok    $src -> $dst:$port $got"
    else
        echo "FAIL  $src -> $dst:$port: wanted $want $local, got $got"; fail=1
    fi
}
check in_ts 100.64.0.1 10.81.1.10 80 allow 192.168.1.10    # pc-thuis -> camera 1 (NAT .10 -> .10)
check in_ts 100.64.0.1 10.81.1.10 8010 allow
check in_ts 100.64.0.1 10.81.1.10 22 block                 # port not in the connection
check in_ts 100.64.0.1 10.81.1.20 80 block                 # other device
check in_ts 100.64.0.4 10.81.1.20 80 allow 192.168.1.20    # pc-werk -> whole subnet, tcp/80
check in_ts 100.64.0.4 10.81.1.10 8010 block
check in_ts 100.64.0.9 10.81.1.10 80 block                 # unknown tailnet source
check in_lan "" 100.64.0.1 22 block                        # site never starts connections
kill "${srv[@]}" "$TS" "$LAN" 2>/dev/null || true
exit $fail
