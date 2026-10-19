# Locus Headless VM & Cron Setup Guide

> **Architecture Reference**: Section 04 / errata D-13 Option a / 10-security.md S-1 & S-2.
> **Topology**: `vm` or `hybrid` (services on remote VM, TUI and local client on personal computer).

---

## 1. Overview & Security Foundation
In **hybrid mode**, the Locus backend (FastAPI sidecar, background research scheduler, and database containers) runs unattended on an always-on Linux Virtual Machine (VM).

### Non-Negotiable Security Rules (10-security.md, D-13 Option a)
1. **No Public Plain HTTP (0.0.0.0)**:
   The sidecar daemon binds **strictly to loopback `127.0.0.1:8420`**. It never opens public plain HTTP on `0.0.0.0`.
2. **Encrypted Loopback Access via SSH Tunnel**:
   The owner's personal computer connects to the VM's sidecar over an SSH tunnel:
   ```bash
   ssh -N -L 8420:127.0.0.1:8420 <user>@<vm-host> -p 22 -i <ssh-key>
   ```
   Or using the built-in Locus CLI helper:
   ```bash
   locus tunnel --host <vm-host> --user <user>
   ```
3. **Database Ports Bound to 127.0.0.1**:
   All database services (CouchDB `5984`, Redis `6379`, Postgres `5432`, Neo4j `7687`) publish exclusively on `127.0.0.1`.
4. **Fail-Closed Pairing**:
   The Telegram gateway rejects all unauthorized messages until paired via a one-time code shown on the host terminal.

---

## 2. VM Prerequisites & Initial Setup
Supported VM Distributions: Ubuntu 22.04 LTS / 24.04 LTS, Debian 12+.

Run the automated installation on the VM:
```bash
git clone https://github.com/Shivamxp23/Locus-OS.git locus-os
cd locus-os
./install.sh --yes --answers tests/fixtures/install_answers.json
```

Or run interactively and select mode `[2] vm`:
```bash
./install.sh
```

---

## 3. Systemd Headless Supervisor Service
Create `/etc/systemd/system/locus-sidecar.service`:

```ini
[Unit]
Description=Locus Headless Sidecar & Scheduler Supervisor
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/locus-os
Environment="LOCUS_HOME=/home/ubuntu/.locus"
EnvironmentFile=/home/ubuntu/.locus/.env
ExecStart=/usr/bin/python3 -m sidecar.service
Restart=always
RestartSec=10
LimitNOFILE=65536

# Security sandbox
PrivateTmp=true
ProtectSystem=full
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable locus-sidecar.service
sudo systemctl start locus-sidecar.service
sudo systemctl status locus-sidecar.service
```

---

## 4. Connecting from Local Computer (Hybrid Mode)
On your personal computer (Windows, macOS, or Linux):

1. **Configure Hybrid Mode**:
   ```bash
   locus install --reconfigure topology
   # Select: hybrid
   locus install --reconfigure vm
   # Enter your VM host IP and SSH user
   ```

2. **Open the SSH Tunnel**:
   ```bash
   locus tunnel
   ```
   Or specify parameters directly:
   ```bash
   locus tunnel --host 203.0.113.10 --user ubuntu --key ~/.ssh/id_rsa
   ```

3. **Verify Connection**:
   In another terminal:
   ```bash
   locus doctor --check-sidecar
   ```
   All checks will report `[PASS]`, confirming local tools reach the remote VM over loopback port 8420.

---

## 5. Unattended Research Jobs (Cron)
Research jobs are defined in YAML under `~/.locus/jobs/<job_id>.yaml`:

```yaml
id: tech-brief
name: Daily Autonomous Tech Brief
cron: "0 8 * * *"
tier: supervised
budget_max_tokens: 50000
destination: "04-Captures/Research"
prompt: "Research recent AI compiler developments and summarize actionable findings."
```

When triggered by the scheduler:
- Executes unattended via `sidecar.pi_bridge.run_pi_turn`.
- Captures output into `~/.locus/vault/04-Captures/Research/<date>-tech-brief.md`.
- Posts executive summary to the paired owner via Telegram.
- Logs execution record in persistent SQLite audit trail.

---

## 6. Health & Diagnostics
Run diagnostics on the VM or over the tunnel:
```bash
locus doctor
```
Expected output:
```
Locus Doctor Diagnostics (R7):
  [PASS] python: Python 3.10+
  [PASS] node: Node.js v18+
  [PASS] git: git version 2.x
  [PASS] docker: Docker daemon running
  [PASS] port-8420: Port 8420 (sidecar) is free / active
  [PASS] vault: ... is writable
  [PASS] env: Found .env with defined variables
  [PASS] providers: registered provider(s) healthy
[OK] System is healthy and ready.
```
