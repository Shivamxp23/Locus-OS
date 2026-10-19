"""
SPEC §17.1-17.11 / §12.1-12.5 / F-0046 / US-09: Integration test for Telegram Delivery of Research Jobs.
Crosses boundary: SchedulerProvider <-> TelegramGateway <-> Pi Bridge <-> Obsidian Vault.
Tests:
- A finished research job triggers Telegram notification to the paired owner
- Long results (>4096 chars) are truncated cleanly to fit single message and cite the vault note
- Telegram delivery failure is non-fatal: job finishes, vault note written, error logged to audit trail
"""
from __future__ import annotations

import datetime
from pathlib import Path
import subprocess
import pytest
import yaml

from sidecar import config
from sidecar.scheduler import SchedulerProvider
from sidecar.telegram.gateway import TelegramGateway
from sidecar.telegram.pairing import PairingManager


@pytest.fixture
def clean_locus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated LOCUS_HOME environment."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    return locus_home


def test_job_completion_delivers_summary_to_paired_owner_on_telegram(clean_locus_env: Path):
    """SPEC §17.1-17.11 / §12.1-12.5 F-0046 / US-09: "A finished job sends its result and its run record to the paired owner on Telegram"."""
    owner_id = 998877
    pairing_mgr = PairingManager()
    pairing_mgr.save_owner_id(owner_id)

    # Configure Telegram gateway with outbox transport capture
    sent_messages = []
    gateway = TelegramGateway(pairing_manager=pairing_mgr)
    gateway.initialize()
    gateway.set_transport(lambda payload: sent_messages.append(payload))

    # Create research job YAML
    jobs_dir = clean_locus_env / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_data = {
        "id": "quantum_materials",
        "name": "Quantum Materials Survey",
        "cron": "0 4 * * *",
        "prompt": "Survey topological insulator materials for spintronics.",
        "tier": "readonly",
        "destination": "04-Captures/Research",
    }
    (jobs_dir / "quantum_materials.yaml").write_text(yaml.dump(job_data), encoding="utf-8")

    # Mock Pi runner
    def fake_pi_runner(prompt: str, session_id: str | None = None, **kwargs):
        return subprocess.CompletedProcess(
            args=["fake-pi"],
            returncode=0,
            stdout="## Summary of Topological Insulators\n1. Bi2Se3 exhibits high spin-momentum locking.\n2. Surface states are robust to non-magnetic impurities.",
            stderr="",
        )

    scheduler = SchedulerProvider(
        pi_runner=fake_pi_runner,
        channel_provider=gateway,
        pairing_manager=pairing_mgr,
    )
    scheduler.initialize()

    record = scheduler.trigger_job("quantum_materials")
    assert record is not None
    assert record["status"] == "completed"

    # Verify vault output file
    today_str = datetime.date.today().isoformat()
    vault_file = clean_locus_env / "vault" / "04-Captures" / "Research" / f"{today_str}-quantum_materials.md"
    assert vault_file.is_file()

    # Verify message sent to paired owner on Telegram
    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert msg["chat_id"] == owner_id
    assert "Quantum Materials Survey" in msg["text"]
    assert "quantum_materials" in msg["text"]
    assert f"{today_str}-quantum_materials.md" in msg["text"]
    assert "Bi2Se3 exhibits high spin-momentum locking" in msg["text"]


def test_long_job_summary_truncates_under_4096_and_cites_vault_note(clean_locus_env: Path):
    """SPEC §17.1-17.11 line 3975: "MAX_MESSAGE_LENGTH = 4096 // Telegram limit"."""
    owner_id = 112233
    pairing_mgr = PairingManager()
    pairing_mgr.save_owner_id(owner_id)

    sent_messages = []
    gateway = TelegramGateway(pairing_manager=pairing_mgr)
    gateway.initialize()
    gateway.set_transport(lambda payload: sent_messages.append(payload))

    jobs_dir = clean_locus_env / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_data = {
        "id": "huge_synthesis",
        "name": "Huge Vault Synthesis",
        "prompt": "Analyze entire knowledge graph.",
    }
    (jobs_dir / "huge_synthesis.yaml").write_text(yaml.dump(job_data), encoding="utf-8")

    # 10,000 characters response
    huge_text = "Detailed findings on multi-layer neuro-symbolic cognitive architectures.\n" * 150

    scheduler = SchedulerProvider(
        pi_runner=lambda *a, **k: huge_text,
        channel_provider=gateway,
        pairing_manager=pairing_mgr,
    )
    scheduler.initialize()

    record = scheduler.trigger_job("huge_synthesis")
    assert record is not None
    assert record["status"] == "completed"

    # Message must be received and strictly <= 4096 chars
    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert msg["chat_id"] == owner_id
    assert len(msg["text"]) <= 4096
    assert "truncated; full report in" in msg["text"]
    assert "huge_synthesis.md" in msg["text"]


def test_telegram_delivery_failure_is_never_fatal_to_scheduler(clean_locus_env: Path):
    """SPEC 04 line 27: "Never fatal: mirroring, notification, and logging failures are logged and swallowed"."""
    owner_id = 445566
    pairing_mgr = PairingManager()
    pairing_mgr.save_owner_id(owner_id)

    class FailingChannel:
        def send_message(self, target, text):
            raise ConnectionError("Telegram network timeout (504 Gateway Timeout)")

    jobs_dir = clean_locus_env / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_data = {
        "id": "unreliable_network_job",
        "name": "Network Resilient Job",
        "prompt": "Research resilient systems.",
    }
    (jobs_dir / "unreliable_network_job.yaml").write_text(yaml.dump(job_data), encoding="utf-8")

    scheduler = SchedulerProvider(
        pi_runner=lambda *a, **k: "Research completed successfully despite network failure.",
        channel_provider=FailingChannel(),
        pairing_manager=pairing_mgr,
    )
    scheduler.initialize()

    # Trigger job must not raise exception
    record = scheduler.trigger_job("unreliable_network_job")
    assert record is not None
    assert record["status"] == "completed"

    # Vault note still written
    today_str = datetime.date.today().isoformat()
    vault_file = clean_locus_env / "vault" / "04-Captures" / "Research" / f"{today_str}-unreliable_network_job.md"
    assert vault_file.is_file()

    # Audit trail records the notification failure was swallowed
    audit_file = clean_locus_env / "vault" / "05-Daily" / "Logs" / f"audit-{today_str}.md"
    assert audit_file.is_file()
    assert "Telegram notification swallowed error" in audit_file.read_text(encoding="utf-8")
