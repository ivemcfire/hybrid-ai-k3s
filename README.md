# hybrid-ai-k3s

> **DEPRECATED 2026-05-11.** Local Ollama routing was scrapped from active workflow after real-world tests (3 PowerShell attempts + 1 bash task) showed 0/2 task success without cloud audit. Net cost (LAI prompts + WoL wake + cloud rewrite) exceeded pure cloud start-to-finish. Privacy use cases didn't materialize for homelab work.
>
> Default routing now: cloud Opus 4.7 + Sonnet 4.6 sub-agents (Anthropic Agent tool — `subagent_type=Explore` for read-only / `general-purpose` for write / `Plan` for design).
>
> **2026-05-11 update — hardware removed.** RTX 3060 pulled from `.50`, Ollama uninstalled. Box reverted to Windows daily-driver with GTX 1050Ti (4GB VRAM, insufficient for any useful coder model). Local AI not revivable on `.50`. To revive elsewhere: install Ollama on a host with ≥12GB VRAM, pull `qwen2.5-coder:14b` Q4_K_M (9GB), apply tuning from `eval/` companion + `~/bin/ollama-tune-vram-cap.ps1` (adapt for Linux if needed), update endpoint in consumers.

---

Companion repo for the post **["Hybrid AI on k3s: A Sleeping GPU, Local
qwen2.5-coder, and Cloud Only When Asked"](https://ivemcfire.github.io/posts/hybrid-ai-k3s.html)**.

This repo contains the sanitised manifests, scripts, and config behind a
homelab AI workflow where:

- A local model (`qwen2.5-coder:14b` on an RTX 3060 12GB, served by Ollama
  on Windows) is the **default driver** for routine k3s / platform-engineering
  work.
- The GPU box is **asleep most of the time** and woken on demand by the
  cluster via Wake-on-LAN + SSH.
- A cloud model (Gemini 3.1 Pro) is **on call**, but only ever invoked on
  **explicit manual escalation** — never auto-routed.

The shape of the system, in one line:

> The default is: nothing leaves the network unless I decide it is worth
> leaving.

## Why this layout

| Lesson from the post                                | Where it lives in this repo               |
|-----------------------------------------------------|-------------------------------------------|
| 12GB VRAM is the load-bearing constraint            | [`ollama/ollama-env.example`](ollama/ollama-env.example) |
| Kubernetes does not need to own the GPU             | [`bridge/ai-bridge.py`](bridge/ai-bridge.py), [`k8s/ai-bridge-svc.yaml`](k8s/ai-bridge-svc.yaml) |
| Wake-on-LAN, not always-on                          | [`scripts/wol.sh`](scripts/wol.sh)        |
| Manual `keep-warm`, not auto-detection              | [`scripts/keep-warm.sh`](scripts/keep-warm.sh) |
| Manual Gemini escalation, not auto-routing          | [`escalation/playbook.md`](escalation/playbook.md) |
| Sanitisation pass before any cloud call             | [`scripts/sanitise.sh`](scripts/sanitise.sh) |

## Quick start

The bridge is a small Python service that runs on the k3s control-plane
node (or anywhere reachable from the cluster). It exposes an HTTP endpoint,
wakes the Windows GPU box on demand, and proxies requests to Ollama over an
SSH tunnel.

```bash
# 1. Configure the bridge (edit MAC, host, SSH user)
cp bridge/config.example.yaml bridge/config.yaml
$EDITOR bridge/config.yaml

# 2. Drop the systemd unit in place and start the bridge
sudo cp bridge/ai-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-bridge

# 3. Expose it inside the cluster
kubectl apply -f k8s/ai-bridge-svc.yaml

# 4. Verify
curl http://localhost:8080/healthz
curl -X POST http://localhost:8080/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"echo hello","model":"qwen2.5-coder:14b"}'
```

The first call wakes the box (~12–15s cold start). Subsequent calls go
straight through. After 5 minutes of idleness the bridge stops sending
keep-alives and the box goes back to sleep.

## Sanitisation rules

Every artefact in this repo has been passed through
[`scripts/sanitise.sh`](scripts/sanitise.sh). The rules are intentionally
simple:

- LAN IPs → `192.168.X.X`
- Internal hostnames → `example.com`
- Tunnel UUIDs / cert subjects → `<TUNNEL-UUID>` / `<placeholder>`
- API keys and tokens → `<placeholder>`
- MAC addresses kept (they are public and the WoL helper needs the format)

Run the script on any payload before sending it to a cloud model:

```bash
./scripts/sanitise.sh < raw-manifest.yaml > safe-manifest.yaml
```

## What this repo deliberately does NOT do

- It does not auto-route requests between local and cloud models. That is
  the entire point — escalation is a conscious decision.
- It does not advertise the GPU as `nvidia.com/gpu` to the cluster. The
  Windows box is not a cluster node and is not pretending to be one.
- It does not chase a bigger model than fits in 12GB. `qwen2.5-coder:14b` at
  `Q4_K_M` is the calibration the rest of the system is built around.

## License

MIT. See [LICENSE](LICENSE).
