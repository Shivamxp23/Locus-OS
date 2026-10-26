"""
Unit tests for File Safety (SPEC §13.2 / F-0107 / US-69).
"""
from pathlib import Path
import shutil
import tempfile
import pytest

from sidecar.security.file_safety import (
    CwdJail,
    FileStateRecord,
    FileStateTracker,
    PathValidationDecision,
)
from sidecar.providers.file_safety import DefaultFileSafetyProvider
import sidecar.config as config


@pytest.fixture
def temp_jail_env():
    root = tempfile.mkdtemp()
    root_path = Path(root).resolve()
    # Create sample files
    (root_path / "src").mkdir()
    (root_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (root_path / ".git").mkdir()
    (root_path / ".git" / "config").write_text("git config", encoding="utf-8")
    (root_path / ".env").write_text("SECRET=123", encoding="utf-8")

    yield root_path
    shutil.rmtree(root, ignore_errors=True)


def test_cwd_jail_allowed_inside_root(temp_jail_env):
    """SPEC §13.2 line 3148: "cwd_jail: confine file operations to project root + allowed paths" """
    jail = CwdJail(root=temp_jail_env)
    dec = jail.validate("src/main.py", operation="read")
    assert dec.allowed is True
    assert dec.violation_type is None


def test_cwd_jail_path_traversal_blocked(temp_jail_env):
    """SPEC §13.2 line 3148: "cwd_jail: confine file operations to project root + allowed paths" """
    jail = CwdJail(root=temp_jail_env)
    # Attempt to traverse outside jail root
    dec = jail.validate("../../etc/passwd", operation="read")
    assert dec.allowed is False
    assert dec.violation_type == "outside_jail"
    assert "escapes project jail" in (dec.reason or "")


def test_cwd_jail_null_byte_blocked(temp_jail_env):
    """SPEC §13.2 line 3148: "cwd_jail: confine file operations to project root + allowed paths" """
    jail = CwdJail(root=temp_jail_env)
    dec = jail.validate("src/main.py\0.txt", operation="read")
    assert dec.allowed is False
    assert dec.violation_type == "path_traversal"


def test_blocked_pattern_git_write(temp_jail_env):
    """SPEC §13.2 line 3150: "BLOCKED_PATTERNS layered on top of Pi's shell safety" """
    jail = CwdJail(root=temp_jail_env)
    # Write or delete on .git must be blocked
    dec_write = jail.validate(".git/config", operation="write")
    assert dec_write.allowed is False
    assert dec_write.violation_type == "blocked_pattern"

    dec_del = jail.validate(".git/HEAD", operation="delete")
    assert dec_del.allowed is False
    assert dec_del.violation_type == "blocked_pattern"


def test_blocked_pattern_env_and_keys(temp_jail_env):
    """SPEC §13.2 line 3150: "BLOCKED_PATTERNS layered on top of Pi's shell safety" """
    jail = CwdJail(root=temp_jail_env)
    # .env files are blocked
    dec_env = jail.validate(".env", operation="write")
    assert dec_env.allowed is False
    assert dec_env.violation_type == "blocked_pattern"

    # Private key patterns are blocked
    dec_key = jail.validate("src/id_rsa", operation="read")
    assert dec_key.allowed is False
    assert dec_key.violation_type == "blocked_pattern"


def test_file_state_tracking(temp_jail_env):
    """SPEC §13.2 line 3149: "file_state tracking: track file modifications across tool calls" """
    storage_dir = temp_jail_env / "state_dir"
    tracker = FileStateTracker(storage_dir=storage_dir)

    target_file = temp_jail_env / "src" / "main.py"
    rec = tracker.record(str(target_file), operation="modify", content=b"updated code")

    assert rec.path == str(target_file)
    assert rec.operation == "modify"
    assert rec.size_bytes == len(b"updated code")
    assert rec.sha256 is not None

    hist = tracker.get_history()
    assert len(hist) == 1
    assert hist[0].path == str(target_file)


def test_file_safety_provider_off_switches(temp_jail_env, monkeypatch):
    """SPEC §13.2 line 3158: "Swappable / off state: locus.security.file_safety.enabled. Off → Pi's default file access controls apply." """
    provider = DefaultFileSafetyProvider(
        storage_dir=temp_jail_env / "state",
        root_dir=temp_jail_env,
    )

    monkeypatch.setattr(config, "get", lambda key: True if "enabled" in key else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: True)
    assert provider.is_available() is True

    # Off-switch 1: locus.file_safety.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.file_safety.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.file_safety.enabled" else True)
    assert provider.is_available() is False

    # Off-switch 2: locus.security.file_safety.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.file_safety.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.file_safety.enabled" else True)
    assert provider.is_available() is False
