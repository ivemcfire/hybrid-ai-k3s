#!/usr/bin/env python3
"""ai-bridge — small HTTP service that wakes a sleeping Windows GPU box on
demand and proxies inference requests to Ollama over an SSH tunnel.

This is the bridge described in the post. It is deliberately small:
~200 lines, one process, one SSH connection at a time. It does not try to
be a load balancer, an authn layer, or a model router. Those concerns belong
elsewhere.

The flow on each request:
  1. If no SSH tunnel is up, send a Wake-on-LAN packet to the Windows MAC.
  2. Wait for SSH to accept connections (bounded by wake_timeout_seconds).
  3. Open a local-forward tunnel: localhost:11434 -> windows:127.0.0.1:11434.
  4. Forward the HTTP request body verbatim to Ollama on localhost.
  5. Stream the response back to the caller.
  6. Reset an idle timer. When it fires, tear down the tunnel and let the
     box go back to sleep.

Manual `keep-warm` ping suppresses the idle timer for 60 minutes.
"""

import json
import logging
import socket
import struct
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

import yaml  # PyYAML

CONFIG_PATH = Path("/etc/ai-bridge/config.yaml")
KEEP_WARM_SECONDS = 60 * 60

log = logging.getLogger("ai-bridge")


def load_config(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def send_magic_packet(mac: str, broadcast: str) -> None:
    """Send a Wake-on-LAN magic packet to the given MAC over UDP/9."""
    mac_bytes = bytes.fromhex(mac.replace(":", ""))
    packet = b"\xff" * 6 + mac_bytes * 16
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(packet, (broadcast, 9))
    sock.close()
    log.info("wol_sent mac=%s broadcast=%s", mac, broadcast)


def wait_for_ssh(host: str, port: int = 22, timeout: int = 30) -> bool:
    """Poll TCP/22 on host until it accepts a connection or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            time.sleep(1)
    return False


class Tunnel:
    """SSH local-forward tunnel managed as a subprocess."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()
        self.last_used = 0.0
        self.warm_until = 0.0

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def ensure_up(self) -> None:
        with self.lock:
            if self.is_alive():
                return

            mac = self.cfg["windows_gpu"]["mac"]
            host = self.cfg["windows_gpu"]["host"]
            broadcast = self.cfg["windows_gpu"]["broadcast"]
            timeout = self.cfg["windows_gpu"]["wake_timeout_seconds"]

            send_magic_packet(mac, broadcast)
            if not wait_for_ssh(host, timeout=timeout):
                raise TimeoutError(f"ssh did not come up within {timeout}s")

            ssh = self.cfg["ssh"]
            cmd = [
                "ssh", "-N",
                "-o", f"UserKnownHostsFile={ssh['known_hosts']}",
                "-o", "StrictHostKeyChecking=yes",
                "-o", "ServerAliveInterval=15",
                "-o", "ExitOnForwardFailure=yes",
                "-i", ssh["key_path"],
                "-L", f"{ssh['local_port']}:{ssh['remote_host']}:{ssh['remote_port']}",
                f"{ssh['user']}@{host}",
            ]
            self.proc = subprocess.Popen(cmd)
            time.sleep(1)  # let the forward come up
            log.info("tunnel_up host=%s pid=%d", host, self.proc.pid)

    def teardown(self) -> None:
        with self.lock:
            if self.is_alive():
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                log.info("tunnel_down")
            self.proc = None

    def touch(self) -> None:
        self.last_used = time.time()

    def keep_warm(self) -> None:
        self.warm_until = time.time() + KEEP_WARM_SECONDS

    def maybe_idle_close(self, idle_seconds: int) -> None:
        now = time.time()
        if now < self.warm_until:
            return
        if self.last_used and now - self.last_used > idle_seconds:
            self.teardown()


class Handler(BaseHTTPRequestHandler):
    tunnel: Tunnel
    cfg: dict

    def log_message(self, fmt: str, *args) -> None:
        log.info("http " + fmt, *args)

    def do_GET(self):  # noqa: N802
        if self.path == "/healthz":
            self._reply(200, b"ok\n")
            return
        if self.path == "/v1/keep-warm":
            self.tunnel.keep_warm()
            self._reply(200, b'{"status":"warm","window_seconds":3600}\n')
            return
        self._reply(404, b"not found\n")

    def do_POST(self):  # noqa: N802
        if self.path != "/v1/generate":
            self._reply(404, b"not found\n")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            self.tunnel.ensure_up()
            local_port = self.cfg["ssh"]["local_port"]
            req = Request(
                f"http://127.0.0.1:{local_port}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urlopen(req, timeout=120) as resp:
                payload = resp.read()
            self.tunnel.touch()
            self._reply(200, payload)
        except Exception as e:
            log.exception("bridge_error")
            self._reply(502, json.dumps({"error": str(e)}).encode())

    def _reply(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def idle_watcher(tunnel: Tunnel, idle_seconds: int) -> None:
    while True:
        time.sleep(15)
        try:
            tunnel.maybe_idle_close(idle_seconds)
        except Exception:
            log.exception("idle_watcher_error")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    cfg = load_config(CONFIG_PATH)

    tunnel = Tunnel(cfg)
    idle_seconds = cfg["bridge"]["idle_seconds"]
    threading.Thread(target=idle_watcher, args=(tunnel, idle_seconds), daemon=True).start()

    Handler.tunnel = tunnel
    Handler.cfg = cfg

    host, port = cfg["bridge"]["listen"].split(":")
    server = ThreadingHTTPServer((host, int(port)), Handler)
    log.info("listening on %s", cfg["bridge"]["listen"])
    try:
        server.serve_forever()
    finally:
        tunnel.teardown()


if __name__ == "__main__":
    main()
