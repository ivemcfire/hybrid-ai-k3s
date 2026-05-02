#!/usr/bin/env bash
# Standalone Wake-on-LAN helper. Useful for testing the WoL path
# independently of the bridge process.
#
# Usage:
#   ./wol.sh AA:BB:CC:DD:EE:FF [192.168.X.255]
#
# The bridge has an embedded WoL implementation; this script exists so the
# WoL path can be debugged without spinning up the bridge.

set -euo pipefail

MAC=${1:?usage: wol.sh <mac> [broadcast]}
BROADCAST=${2:-192.168.255.255}

if ! command -v wakeonlan >/dev/null 2>&1; then
    echo "wakeonlan not found. install with: apt install wakeonlan" >&2
    exit 127
fi

echo "WoL: mac=$MAC broadcast=$BROADCAST"
wakeonlan -i "$BROADCAST" "$MAC"

# Wait for SSH (default 30s). The bridge does the same poll internally.
HOST=${SSH_TARGET_HOST:-192.168.X.X}
TIMEOUT=${SSH_TIMEOUT:-30}
echo "waiting for ssh on $HOST (up to ${TIMEOUT}s)..."
end=$(( $(date +%s) + TIMEOUT ))
while [ "$(date +%s)" -lt "$end" ]; do
    if nc -z -w 2 "$HOST" 22 2>/dev/null; then
        echo "ssh up after $(( $(date +%s) - end + TIMEOUT ))s"
        exit 0
    fi
    sleep 1
done
echo "ssh did not come up within ${TIMEOUT}s" >&2
exit 1
