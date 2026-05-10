#!/bin/bash
# Send a prompt file to qwen2.5-coder:14b on .50 via k3master.
# Usage: ./run_local.sh <prompt_file> [model]
set -euo pipefail

PROMPT_FILE="${1:?prompt file required}"
MODEL="${2:-qwen2.5-coder:14b}"

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "ERR: prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

PAYLOAD=$(python3 -c '
import json, sys
prompt = open(sys.argv[1]).read()
print(json.dumps({
    "model": sys.argv[2],
    "prompt": prompt,
    "stream": False,
    "options": {"temperature": 0.2, "num_ctx": 8192, "num_gpu": 999}
}))
' "$PROMPT_FILE" "$MODEL")

# Wake first (idempotent), then route via k3master to ollama on .50:11500
echo "$PAYLOAD" | ssh user@192.168.100.52 \
  "wakeonlan FC:34:97:B5:A5:43 >/dev/null 2>&1; \
   curl -s -m 600 -X POST -H 'Content-Type: application/json' \
        --data-binary @- http://192.168.100.50:11500/api/generate" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("response",""))'
