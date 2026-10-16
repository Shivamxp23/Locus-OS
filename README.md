# Locus OS

> **Personal Cognitive Operating System & Autonomous Agent Intelligence Framework**  
> Built as an extensible, modular architecture on top of the Pi Coding Agent.

---

## 1. Overview

**Locus OS** is a self-hosted, personal-intelligence framework designed to serve as an always-on cognitive copilot and autonomous executive companion. It unifies goal tracking, life equilibrium, memory graphs, multi-channel messaging (Telegram, Terminal UI), background research loops, and coding harness delegation into a cohesive operating system.

### Core Architecture Principles
* **Strictly Modular:** Every single capability (channels, memory backends, LLM providers, life tracking) is governed by a central Provider Registry and can be independently enabled, disabled, or swapped via configuration.
* **Primarily Headless:** Built to run 24/7 on a remote virtual machine (or local daemon) that autonomously conducts research and executes tasks without requiring active user prompting.
* **Never Fork Upstream:** Extends the Pi Coding Agent (`packages/coding-agent`) cleanly via external Python sidecar services and TypeScript extensions—keeping the upstream core pinned and read-only.
* **Full Auditability:** Every turn, trajectory, decision, and chat transcript is automatically redacted and backed up into a local **Obsidian Vault**.
* **Four Fundamental Pillars:**
  1. **Meta-Harness:** Orchestrates and delegates subtasks to specialized CLI coding harnesses (Pi, Claude Code, OpenCode) in isolated scratch worktrees.
  2. **Multi-Factor Task Priority (TWS):** Dynamic priority scoring across tasks and goals at all scales.
  3. **Graph Memory Substrate:** Neo4j Agent Memory integration for persistent semantic, episodic, and associative memory.
  4. **Vault & LiveSync:** Bi-directional note synchronisation and daily markdown audit logs.

---

## 2. System Architecture & Topologies

Locus OS operates in three primary deployment modes:

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           TOPOLOGY MODES                              │
  └────────────────────────────────────────────────────────────────────────┘

     1. LOCAL MODE                 2. VM MODE                 3. HYBRID MODE
  ┌───────────────────┐      ┌───────────────────┐      ┌─────────────────────────┐
  │ Local Machine     │      │ Remote Cloud / VM │      │ Local Machine (TUI)     │
  │ • Locus TUI       │      │ • Headless Daemon │      │            │            │
  │ • Sidecar Service │      │ • Sidecar Service │      │   [SSH Loopback Tunnel] │
  │ • Pi Agent        │      │ • Telegram Bot    │      │   ssh -L 8420:localhost │
  │ • Obsidian Vault  │      │ • Research Crons  │      │            ▼            │
  │ • Local CouchDB   │      │ • Vault / CouchDB │      │ Remote VM (Headless)    │
  └───────────────────┘      └───────────────────┘      │ • Sidecar Daemon :8420  │
                                                        │ • LiveSync CouchDB :5984│
                                                        └─────────────────────────┘
```

* **Local:** Everything runs locally on your workstation.
* **VM:** Sidecar daemon and background research crons run continuously on a headless cloud VM.
* **Hybrid:** The backend daemon and databases run securely on an always-on VM (binding strictly to loopback `127.0.0.1`), while you interact via the native Terminal User Interface (TUI) on your local machine over an encrypted SSH loopback tunnel.

### Repository Layout
```text
locus-os/
├── packages/           # Upstream Pi Coding Agent (Read-only baseline)
├── sidecar/            # Locus Python Sidecar service & cognitive micro-engines
│   ├── channel_telegram.py # Telegram bot gateway with pairing
│   ├── life_os/        # 4 Factions, Task Weighting Score (TWS), Goal Stack
│   ├── memory/         # Neo4j Agent Memory & semantic retrieval
│   ├── personality/    # SOUL.md parser & wants engine
│   ├── routing/        # Adaptive model tiering & classifier
│   ├── storage/        # Obsidian LiveSync CouchDB bridge & Shorthand
│   └── voice/          # VAD, Whisper STT, and TTS pipeline
├── locus-extension/    # TypeScript extension hooks for Pi Agent runtime
├── locus_cli/          # Command-line interface, TUI, doctor & installer
├── tests/              # Automated unit, integration, and guard test suites
├── tools/              # Guardrails, evidence tracker, and CI verification
├── install.bat / .ps1  # Cross-platform installation launchers
├── locus.bat / .cmd    # Interactive Locus TUI entry points
└── uninstall.bat / .ps1# Safe uninstaller with step-by-step confirmation
```

---

## 3. Installation & Getting Started

### Prerequisites
* **Python 3.11+** (Python 3.12 or 3.13 recommended)
* **Git**
* *(Optional)* **Node.js 18+** (for TypeScript extension development)
* *(Optional)* **Docker & Docker Compose** (for local CouchDB, Neo4j, Redis services)

### Quick Install

Run the installer using your platform's launcher:

```powershell
# Windows (PowerShell)
.\install.ps1

# Windows (Command Prompt / CMD)
install.bat

# Linux / macOS (Bash)
./install.sh
```

Alternatively, invoke via Python:
```powershell
py -3 -m locus_cli.main install
```

### What the Installer Does
1. Creates your Locus home directory at `~/.locus/` (or custom `$LOCUS_HOME`).
2. Configures `~/.locus/config.yaml` with chosen topology mode (`local`, `vm`, `hybrid`).
3. Prompts for your LLM API keys (Anthropic, OpenAI, Gemini) and saves them with strict `0600` permissions into `~/.locus/.env`.
4. Initializes the **8 Canonical Obsidian Vault Directories**:
   * `00-System` · `01-Projects` · `02-Areas` · `03-Resources`
   * `04-Captures` · `05-Daily` · `06-Content` · `07-Archives`
5. *(Optional)* Sets up your personal Telegram Bot via an interactive pairing flow.

---

## 4. Running Locus

### Interactive Terminal User Interface (TUI)
Launch the interactive Locus workspace:
```powershell
locus
```
*(or run `locus.bat`, `.\locus.cmd`, or `py -3 -m locus_cli.main`)*

The TUI features:
* Real-time ASCII banner and topology indicator (`LOCAL` / `VM` / `HYBRID`).
* Live **4-Pillar Faction Balance Meters** (Craft, Health, Learning, Personal).
* System metrics (Context Headroom %, Active Subagents, Token Velocity).
* Natural language conversation routing and slash commands.

#### TUI Slash Commands
* `/help` — List available slash commands.
* `/status` or `/dashboard` — Render full system telemetry screen.
* `/factions` — View weekly life faction equilibrium and time lag bonuses.
* `/doctor` — Run diagnostic connectivity checks.
* `/vault` — Inspect active Obsidian vault location and sync state.
* `/subagents` — Display active background subagents and task trees.
* `/memory` — Inspect Neo4j graph memory node count and context cache.
* `/checkin` — Trigger a proactive daily alignment check-in.
* `/clear` — Clear the terminal viewport.
* `/exit` or `/quit` — Exit the TUI session.

### Batch Execution (One-Shot Turn)
Send a single prompt without entering the interactive REPL:
```powershell
locus --print "Summarize the active tasks in 01-Projects"
```

### Environment Diagnostics
Verify prerequisites, loopback ports, and configuration integrity:
```powershell
locus doctor
```

---

## 5. Background Research & Cron Engine

Locus executes autonomous research jobs without requiring user prompting:
1. Define research jobs as YAML files under `~/.locus/jobs/` (or in `config.yaml` under `locus.research.jobs`).
2. Example job definition (`~/.locus/jobs/biotech_scan.yaml`):
   ```yaml
   name: biotech_literature_scan
   schedule: "0 8 * * *"   # Every morning at 08:00
   prompt: "Conduct a literature review of recent preprint breakthroughs in genomic variant effect prediction."
   tier: "reasoning"
   destination: "05-Daily/Research/biotech-briefing.md"
   notify:
     telegram: true
   ```
3. The scheduler fires via `APScheduler`, executes through `run_pi_turn`, logs structured summaries into your Obsidian vault, and sends completion briefings to your paired Telegram chat.

---

## 6. Uninstallation

Locus includes a dedicated uninstaller that removes downloaded configurations, credentials, and runtime data **without ever touching the repository source code**.

### Running the Uninstaller
```powershell
# Interactive uninstaller (prompts for confirmation at each step):
locus uninstall

# Or via platform launchers:
.\uninstall.ps1
uninstall.bat
./uninstall.sh
```

### Step-by-Step Confirmation & Vault Protection
The uninstaller guides you through four distinct steps and asks whether to cancel at every phase:
1. **Initial Confirmation:** Verifies intent to uninstall.
2. **Configuration & Secrets:** Cleans up `~/.locus/config.yaml` and `~/.locus/.env`.
3. **Jobs & Databases:** Deletes research jobs, SQLite databases, and session caches.
4. **Obsidian Vault:** Prompts explicitly whether to delete or **keep** your Obsidian vault (defaults to **keep safe** to protect your personal notes).

#### Non-Interactive Uninstallation (for Automation)
```powershell
# Uninstall runtime files while keeping your vault safe:
locus uninstall --yes --keep-vault

# Uninstall everything including the vault:
locus uninstall --yes --delete-vault
```

---

## 7. Development & Verification

Locus enforces automated architectural guardrails and cryptographic evidence proofs before code is committed.

### Running Test Suites
```powershell
# Run the complete test suite (600+ tests across all subsystems):
py -3 -m pytest tests/

# Run guardrail verification tests:
py -3 -m pytest tests/guard/
```

### Architectural Guard Check
Verifies layout purity, secret leaks, upstream isolation, and import integrity:
```powershell
py -3 tools/guard/check.py --full
```

### Recomputing Evidence & Proof Status
The Evidence Tracker recomputes feature verification percentages against automated proofs:
```powershell
py -3 tools/tracker/verify.py
py -3 tools/tracker/export_xlsx.py
```

---

## 8. License

Locus OS framework code is licensed under the MIT License.  
Upstream Pi Coding Agent components under `packages/` remain governed by their respective upstream licenses.
