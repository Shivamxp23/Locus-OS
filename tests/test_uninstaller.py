"""tests/test_uninstaller.py - Unit and integration tests for Locus uninstaller.

Tests step-by-step confirmation, cancellation at every step, selective vault deletion/retention,
non-interactive uninstallation, and protection of the source repository.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Generator

import pytest

from locus_cli.main import init_locus_home, run_installer
from locus_cli.uninstall import (
    _is_safe_to_delete,
    ask_cancel,
    ask_user,
    run_uninstaller,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_locus_installation() -> Generator[tuple[Path, Path], None, None]:
    """Create a fully populated fake Locus installation with config, secrets, jobs, and vault."""
    with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as vault_dir:
        home_path = Path(home_dir)
        vault_path = Path(vault_dir)

        # Bootstrap installation
        init_locus_home(locus_home=home_path, vault_root=vault_path)

        # Add sample job and database file
        (home_path / "jobs" / "sample_job.yaml").write_text("name: test_job\n", encoding="utf-8")
        (home_path / "state.db").write_text("dummy database content", encoding="utf-8")

        # Add sample vault file
        (vault_path / "01-Projects" / "project_note.md").write_text("# Important Note\n", encoding="utf-8")

        yield home_path, vault_path


def test_uninstaller_launchers_exist_and_thin() -> None:
    """Verify uninstall.bat, uninstall.ps1, and uninstall.sh exist and invoke locus_cli.main."""
    bat_path = REPO_ROOT / "uninstall.bat"
    ps1_path = REPO_ROOT / "uninstall.ps1"
    sh_path = REPO_ROOT / "uninstall.sh"

    assert bat_path.is_file(), "uninstall.bat must exist at repository root"
    assert ps1_path.is_file(), "uninstall.ps1 must exist at repository root"
    assert sh_path.is_file(), "uninstall.sh must exist at repository root"

    ps1_lines = ps1_path.read_text(encoding="utf-8").splitlines()
    sh_lines = sh_path.read_text(encoding="utf-8").splitlines()

    assert len(ps1_lines) < 50
    assert len(sh_lines) < 50
    assert any("locus_cli.main uninstall" in l for l in ps1_lines)
    assert any("locus_cli.main uninstall" in l for l in sh_lines)


def test_is_safe_to_delete_guards_repository() -> None:
    """Verify _is_safe_to_delete strictly refuses to delete repo root or repo parents."""
    assert not _is_safe_to_delete(REPO_ROOT, REPO_ROOT)
    assert not _is_safe_to_delete(REPO_ROOT.parent, REPO_ROOT)
    assert not _is_safe_to_delete(REPO_ROOT / ".git", REPO_ROOT)
    assert not _is_safe_to_delete(REPO_ROOT / "sidecar", REPO_ROOT)

    with tempfile.TemporaryDirectory() as tmp:
        assert _is_safe_to_delete(Path(tmp), REPO_ROOT)


def test_step1_cancel_aborts_immediately(mock_locus_installation: tuple[Path, Path]) -> None:
    """Answering 'cancel' on step 1 aborts uninstallation without deleting any files."""
    home_path, vault_path = mock_locus_installation

    responses = iter(["cancel"])
    rc = run_uninstaller(
        locus_home=home_path,
        vault_root=vault_path,
        input_fn=lambda prompt: next(responses),
    )
    assert rc == 0
    # Everything should still exist
    assert (home_path / "config.yaml").is_file()
    assert (home_path / ".env").is_file()
    assert (home_path / "jobs" / "sample_job.yaml").is_file()
    assert (vault_path / "01-Projects" / "project_note.md").is_file()


def test_explicit_cancel_prompt_aborts_at_any_step(mock_locus_installation: tuple[Path, Path]) -> None:
    """Answering 'yes' to 'Would you like to cancel deletion?' aborts cleanly."""
    home_path, vault_path = mock_locus_installation

    # Step 1: yes to begin, then yes to cancel question
    responses = iter(["yes", "yes"])
    rc = run_uninstaller(
        locus_home=home_path,
        vault_root=vault_path,
        input_fn=lambda prompt: next(responses),
    )
    assert rc == 0
    assert (home_path / "config.yaml").is_file()
    assert (home_path / ".env").is_file()


def test_uninstaller_deletes_home_and_preserves_vault(mock_locus_installation: tuple[Path, Path]) -> None:
    """Interactive flow where user confirms deleting ~/.locus but explicitly preserves the vault."""
    home_path, vault_path = mock_locus_installation

    # Answers:
    # 1. Step 1: proceed? -> yes
    #    Cancel? -> no
    # 2. Step 2: delete config & secrets? -> yes
    #    Cancel? -> no
    # 3. Step 3: delete jobs & data? -> yes
    #    Cancel? -> no
    # 4. Step 4: delete vault? -> no
    #    Cancel? -> no
    # 5. Final confirm: execute? -> yes
    #    Cancel? -> no
    responses = iter([
        "yes", "no",  # step 1
        "yes", "no",  # step 2
        "yes", "no",  # step 3
        "no",  "no",  # step 4 (keep vault!)
        "yes", "no",  # final confirm
    ])

    rc = run_uninstaller(
        locus_home=home_path,
        vault_root=vault_path,
        input_fn=lambda prompt: next(responses),
    )
    assert rc == 0

    # Config, .env, jobs, and home directory should be removed
    assert not (home_path / "config.yaml").exists()
    assert not (home_path / ".env").exists()
    assert not (home_path / "jobs").exists()
    assert not home_path.exists()

    # Obsidian vault must be strictly preserved!
    assert vault_path.exists()
    assert (vault_path / "01-Projects" / "project_note.md").is_file()


def test_uninstaller_deletes_both_home_and_vault(mock_locus_installation: tuple[Path, Path]) -> None:
    """Interactive flow where user explicitly chooses to delete the vault as well."""
    home_path, vault_path = mock_locus_installation

    responses = iter([
        "yes", "no",  # step 1
        "yes", "no",  # step 2
        "yes", "no",  # step 3
        "yes", "no",  # step 4 (delete vault!)
        "yes", "no",  # final confirm
    ])

    rc = run_uninstaller(
        locus_home=home_path,
        vault_root=vault_path,
        input_fn=lambda prompt: next(responses),
    )
    assert rc == 0

    assert not home_path.exists()
    assert not vault_path.exists()


def test_non_interactive_keep_vault(mock_locus_installation: tuple[Path, Path]) -> None:
    """Non-interactive uninstallation with --yes --keep-vault."""
    home_path, vault_path = mock_locus_installation

    rc = run_uninstaller(
        argv=["--yes", "--keep-vault", f"--locus-home={home_path}", f"--vault-root={vault_path}"]
    )
    assert rc == 0
    assert not home_path.exists()
    assert vault_path.exists()
    assert (vault_path / "01-Projects" / "project_note.md").is_file()


def test_non_interactive_delete_vault(mock_locus_installation: tuple[Path, Path]) -> None:
    """Non-interactive uninstallation with --yes --delete-vault."""
    home_path, vault_path = mock_locus_installation

    rc = run_uninstaller(
        argv=["--yes", "--delete-vault", f"--locus-home={home_path}", f"--vault-root={vault_path}"]
    )
    assert rc == 0
    assert not home_path.exists()
    assert not vault_path.exists()
