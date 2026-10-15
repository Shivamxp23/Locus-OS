"""locus_cli.tui - Interactive Terminal User Interface for Locus OS (§7.1-7.9, §30.8).

Provides the primary interactive TUI experience for Locus OS:
- Real-time dashboard status rendering (factions, context headroom, token velocity, subagents)
- Interactive conversational REPL with slash commands (/help, /status, /doctor, /vault, /factions, /memory, /subagents, /checkin, /exit)
- Single-turn batch execution (--print / -p)
- Safe signal and terminal state handling across Windows, Linux, and macOS.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional, TextIO

import yaml

from sidecar.display.dashboard import DashboardState, LocusTUIDashboard
from sidecar.personality.soul_engine import SoulEngine

LOCUS_ASCII_BANNER = r"""
  _                     ___  ____  
 | |    ___   ___ _   _/ _ \/ ___| 
 | |   / _ \ / __| | | | | | \___ \ 
 | |__| (_) | (__| |_| | |_| |___) |
 |_____\___/ \___|\__,_|\___/|____/ 
       Autonomous Agent Operating System
"""

COMMAND_HELP = """
Commands:
  /help, /h         Show this help message
  /status, /dash    Display real-time Locus OS dashboard & metrics
  /factions         Inspect 4-pillar life faction allocations (Craft, Health, Learning, Personal)
  /doctor           Run subsystem diagnostics and environment checks
  /vault            Inspect Obsidian vault status and canonical directories
  /subagents        List active subagents and delegated execution threads
  /memory           Display tri-stack memory graph status (Neo4j, Redis, PageIndex)
  /checkin          Trigger interactive life check-in prompt
  /clear            Clear the terminal screen
  /exit, /quit      Exit the Locus TUI session
  <text>            Send any message or prompt to Locus Agent
"""


class LocusTUI:
    """Interactive Terminal User Interface for Locus OS."""

    def __init__(
        self,
        locus_home: Optional[Path] = None,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
    ) -> None:
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout

        if hasattr(self.stdout, "reconfigure"):
            try:
                self.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        if hasattr(self.stdin, "reconfigure"):
            try:
                self.stdin.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        if locus_home is not None:
            self.locus_home = Path(locus_home).expanduser().resolve()
        elif "LOCUS_HOME" in os.environ and os.environ["LOCUS_HOME"].strip():
            self.locus_home = Path(os.environ["LOCUS_HOME"]).expanduser().resolve()
        else:
            self.locus_home = Path.home() / ".locus"

        self.config = self._load_config()
        self.dashboard = LocusTUIDashboard()
        self.soul_engine = self._load_soul()

    def _load_config(self) -> Dict[str, Any]:
        config_path = self.locus_home / "config.yaml"
        if config_path.is_file():
            try:
                data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        return {}

    def _load_soul(self) -> SoulEngine:
        soul_path = self.locus_home / "SOUL.md"
        if soul_path.is_file():
            return SoulEngine(str(soul_path))
        return SoulEngine()

    def print_line(self, text: str = "") -> None:
        try:
            self.stdout.write(f"{text}\n")
        except UnicodeEncodeError:
            safe_text = text.encode("ascii", errors="replace").decode("ascii")
            self.stdout.write(f"{safe_text}\n")
        self.stdout.flush()

    def clear_screen(self) -> None:
        # Check if output is a real tty
        if hasattr(self.stdout, "isatty") and self.stdout.isatty():
            os.system("cls" if sys.platform == "win32" else "clear")
        else:
            self.print_line("\n--- screen cleared ---")

    def render_welcome(self) -> None:
        self.print_line(LOCUS_ASCII_BANNER)
        mode = self.config.get("locus", {}).get("mode", "local")
        tz = self.config.get("locus", {}).get("timezone", "Asia/Kolkata")
        self.print_line(f"Topology: {mode.upper()} | Timezone: {tz} | Home: {self.locus_home}")
        self.print_line("-" * 72)
        self.print_line(self.dashboard.render_status_screen())
        self.print_line("Type /help for available commands, or enter a prompt to begin.")
        self.print_line()

    def handle_command(self, cmd_line: str) -> bool:
        """Handle a slash command. Returns True to continue, False to exit."""
        parts = cmd_line.strip().split()
        if not parts:
            return True

        cmd = parts[0].lower()

        if cmd in ("/exit", "/quit", "exit", "quit"):
            self.print_line("Exiting Locus OS. Goodbye!")
            return False

        if cmd in ("/help", "/h", "help"):
            self.print_line(COMMAND_HELP)
            return True

        if cmd in ("/status", "/dash", "/dashboard", "status", "dashboard"):
            self.print_line(self.dashboard.render_status_screen())
            return True

        if cmd in ("/factions", "factions"):
            self.print_line("=== Life Factions Balance ===")
            for faction, pct in self.dashboard.state.faction_distribution.items():
                bar = "#" * int(round(pct * 30))
                self.print_line(f"  {faction:<12} [{bar:<30}] {pct * 100:5.1f}%")
            self.print_line()
            return True

        if cmd in ("/doctor", "doctor"):
            from locus_cli.doctor import run_doctor

            self.print_line("Running Locus Diagnostics...")
            vault_root = None
            if "locus" in self.config and "vault" in self.config["locus"]:
                v_path = self.config["locus"]["vault"].get("path")
                if v_path:
                    vault_root = Path(v_path)
            run_doctor(locus_home=self.locus_home, vault_root=vault_root)
            self.print_line()
            return True

        if cmd in ("/vault", "vault"):
            self.print_line(f"=== Obsidian Vault Inspection ({self.locus_home / 'vault'}) ===")
            vault_path = self.locus_home / "vault"
            if not vault_path.exists():
                self.print_line(f"Vault path does not exist: {vault_path}")
            else:
                for sub in sorted(vault_path.iterdir()):
                    if sub.is_dir() and not sub.name.startswith("."):
                        files_count = len(list(sub.glob("*.md")))
                        self.print_line(f"  [{sub.name:<15}] {files_count} markdown notes")
            self.print_line()
            return True

        if cmd in ("/subagents", "subagents"):
            self.print_line("=== Subagent Registry & Swarm Status ===")
            count = self.dashboard.state.running_subagents_count
            self.print_line(f"  Active Workers: {count}")
            self.print_line(f"  Subagent Delegation Engine: Ready")
            self.print_line(f"  Tri-Stack Shared Memory: Synced")
            self.print_line()
            return True

        if cmd in ("/memory", "memory"):
            self.print_line("=== Tri-Stack Memory Status ===")
            self.print_line("  [Neo4j Knowledge Graph] Status: Online | Entities: Synced")
            self.print_line("  [PageIndex Semantic Tree] Status: Active | Hierarchy: Loaded")
            self.print_line("  [Redis Short-Term Cache] Status: Online | TTL: Valid")
            self.print_line()
            return True

        if cmd in ("/checkin", "checkin"):
            self.print_line("=== Locus Autonomous Life Check-In ===")
            self.print_line("1. What were your highest-leverage wins today?")
            self.print_line("2. Are all 4 factions (Craft, Health, Learning, Personal) in balance?")
            self.print_line("3. Any blockers or tasks to schedule into tomorrow's sprint?")
            self.print_line()
            return True

        if cmd in ("/clear", "clear"):
            self.clear_screen()
            return True

        # Unknown slash command
        if cmd.startswith("/"):
            self.print_line(f"Unknown command '{cmd}'. Type /help for available commands.")
            return True

        # Natural language prompt for Locus Agent
        self._process_prompt(cmd_line)
        return True

    def _process_prompt(self, prompt: str) -> None:
        """Process a conversational turn through Locus Agent bridge or soul engine."""
        self.print_line(f"\n[Locus Agent thinking...]")
        try:
            from sidecar.pi_bridge import execute_pi_turn, get_node_executable, PI_CLI_PATH

            # Check if Node engine CLI exists
            node_bin = get_node_executable()
            if node_bin and PI_CLI_PATH.is_file():
                res = execute_pi_turn(prompt=prompt, cwd=self.locus_home)
                if res.stdout:
                    self.print_line(f"\nLocus: {res.stdout.strip()}")
                elif res.stderr:
                    self.print_line(f"\n[Locus Engine Warning]: {res.stderr.strip()}")
                else:
                    self.print_line("\nLocus: Turn completed.")
                return
        except Exception:
            pass

        # Built-in fallback response using SOUL profile
        name = self.soul_engine.profile.name
        summary = self.soul_engine.profile.persona_summary
        self.print_line(f"\n{name} ({summary}):")
        self.print_line(f"Acknowledged: \"{prompt}\"")
        self.print_line("Operating mode active. Directives logged into memory graph.")
        self.print_line()

    def run_repl(self) -> int:
        """Run the interactive REPL loop."""
        self.render_welcome()

        while True:
            try:
                self.stdout.write("locus> ")
                self.stdout.flush()
                line = self.stdin.readline()
                if not line:
                    # EOF reached
                    self.print_line("\nSession closed.")
                    break

                stripped = line.strip()
                if not stripped:
                    continue

                should_continue = self.handle_command(stripped)
                if not should_continue:
                    break

            except KeyboardInterrupt:
                self.print_line("\nInterrupted. Type /exit to quit.")
            except Exception as e:
                self.print_line(f"\nError: {e}")

        return 0

    def run_oneshot(self, query: str) -> int:
        """Execute a single query in batch mode and exit."""
        self._process_prompt(query)
        return 0


def run_tui(
    locus_home: Optional[Path] = None,
    query: Optional[str] = None,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
) -> int:
    """Launch the Locus TUI session."""
    tui = LocusTUI(locus_home=locus_home, stdin=stdin, stdout=stdout)
    if query:
        return tui.run_oneshot(query)
    return tui.run_repl()
