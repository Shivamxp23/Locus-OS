# Headless VM and Cron Setup Guide

This guide describes deploying Locus OS on a headless remote VM (e.g., Ubuntu 22.04 / Debian) and configuring Hybrid Mode per Architectural Laws and Decision D-13.

---

## 1. Architecture Overview

In **Hybrid Mode** (`locus.mode: hybrid`):
- **Backend Services**: The FastAPI sidecar daemon (:8420), CouchDB database (:5984), and APScheduler background cron runner execute on the remote VM.
- **Frontend / CLI**: The Locus Agent interactive TUI and developer commands run on the owner's local computer.
- **Transport (D-13)**: The local machine communicates with the VM backend exclusively through an **SSH loopback tunnel**:
  ```bash
  ssh -N -L 8420:127.0.0.1:8420 ubuntu@<VM_IP_OR_HOST>
  ```
- **Security (S-2)**: All database and sidecar ports on the VM bind strictly to `127.0.0.1`. No service ports are published to public network interfaces.

---

## 2. Remote VM Systemd Daemon Setup

Background execution on the VM is managed via standard systemd service units.

### 2.1 Generating Service Units
Generate the service definition using the Locus CLI:
```bash
python3 -m locus_cli.systemd --output /etc/systemd/system/locus-sidecar.service
```

The generated unit (`/etc/systemd/system/locus-sidecar.service`) contains:
```ini
[Unit]
Description=Locus OS Headless Sidecar Daemon
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/locus-os
EnvironmentFile=/home/ubuntu/.locus/.env
ExecStart=/opt/locus-os/.venv/bin/python3 -m sidecar.service
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 2.2 Enabling and Starting Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable locus-sidecar.service
sudo systemctl start locus-sidecar.service
sudo systemctl status locus-sidecar.service
```

---

## 3. CouchDB Loopback Sync Setup (S-2)

1. Start CouchDB via `docker-compose.yml`:
   ```bash
   docker compose up -d
   ```
2. Verify CouchDB binds strictly to loopback:
   ```bash
   netstat -tlpn | grep 5984
   # Expected: 127.0.0.1:5984 (never 0.0.0.0:5984)
   ```
3. Remote Obsidian LiveSync clients connect through Tailscale, WireGuard, or an SSH tunnel (`ssh -L 5984:127.0.0.1:5984`), preserving loopback isolation.

---

## 4. Local Hybrid Mode Connection

1. On your local computer, configure Locus mode:
   ```bash
   python -m locus_cli.main --setup --mode hybrid
   ```
2. Start the SSH tunnel:
   ```bash
   ssh -N -L 8420:127.0.0.1:8420 ubuntu@<VM_HOST>
   ```
3. Run diagnostics:
   ```bash
   python -m locus_cli.doctor
   ```
   All health checks will verify backend connectivity through the local forwarded loopback port.
