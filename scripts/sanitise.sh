#!/usr/bin/env bash
# Sanitise stdin before sending it to a cloud model.
#
# Rules (intentionally simple — readability beats coverage for this use case):
#   - LAN IPs in 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16  -> 192.168.X.X
#   - Internal hostnames matching *.lan, *.local, *.home    -> example.com
#   - Cloudflare tunnel UUIDs                               -> <TUNNEL-UUID>
#   - Bearer tokens, API keys, kube tokens                  -> <placeholder>
#   - Base64-looking blobs >= 64 chars                      -> <BASE64-REDACTED>
#
# This script is the minimum bar. Anything sensitive that does not match a
# rule above is on you to redact before piping through.
#
# Usage:
#   ./sanitise.sh < raw.yaml > safe.yaml
#   kubectl get pods -A -o yaml | ./sanitise.sh | pbcopy

set -euo pipefail

sed -E '
    # LAN IPv4 in private ranges -> 192.168.X.X
    s/\b(10\.[0-9]+\.[0-9]+\.[0-9]+)\b/192.168.X.X/g
    s/\b(172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+\.[0-9]+)\b/192.168.X.X/g
    s/\b(192\.168\.[0-9]+\.[0-9]+)\b/192.168.X.X/g

    # Internal hostnames
    s/\b[a-zA-Z0-9-]+\.(lan|local|home)\b/example.com/g

    # Cloudflare tunnel UUIDs
    s/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/<TUNNEL-UUID>/g

    # Common bearer/api/key patterns
    s/(authorization:\s*Bearer\s+)[A-Za-z0-9._~+/=-]+/\1<placeholder>/gI
    s/(api[_-]?key["'"'"':\s=]+)[A-Za-z0-9._-]{16,}/\1<placeholder>/gI
    s/(token["'"'"':\s=]+)[A-Za-z0-9._-]{20,}/\1<placeholder>/gI

    # Long base64 blobs (kube secrets, certs)
    s/[A-Za-z0-9+\/]{64,}={0,2}/<BASE64-REDACTED>/g
'
