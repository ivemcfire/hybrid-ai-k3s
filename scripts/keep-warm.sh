#!/usr/bin/env bash
# Tell the bridge to suppress its idle-sleep timer for the next 60 minutes.
# Useful at the start of a focused session so the cold-start tax does not
# hit every time you switch contexts.
#
# Auto-detection of "active session" was tried and abandoned — it kept the
# box awake overnight after one stray request. Manual is uglier and more
# reliable.

set -euo pipefail

BRIDGE_URL=${BRIDGE_URL:-http://localhost:8080}
curl -fsS "${BRIDGE_URL}/v1/keep-warm"
echo
