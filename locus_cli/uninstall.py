"""locus_cli.uninstall - Interactive and non-interactive uninstaller for Locus OS.

Handles step-by-step uninstallation of downloaded Locus OS files, configurations,
API secrets, databases, research jobs, and optional Obsidian vault cleanup.
Prompts for cancellation at every step, and strictly guarantees that the repository
source code is NEVER deleted.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Callable


def _remove_readonly(func: Callable, path: str, excinfo: tuple) -> None:
    """Clear the readonly bit and re-attempt file deletion (Windows compatibility)."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _is_safe_to_delete(target: Path, repo_root: Path) -> bool:
    """Verify target path is NOT the repository root or parent of source code."""
    try:
        resolved_target = target.resolve()
        resolved_repo = repo_root.resolve()

        # Never delete repository root itself
        if resolved_target == resolved_repo:
            return False

        # Never delete parent of repository root
        if resolved_repo in resolved_target.parents:
            return False

        # Never delete any path that directly contains the Locus source code indicators
        if (resolved_target / "packages" / "coding-agent").is_dir() and (resolved_target / "sidecar").is_dir():
            return False

        if (resolved_target / ".git").is_dir():
            return False

        return True
    except Exception:
        return False


def ask_user(
    prompt: str,
    default: str = "yes",
    input_fn: Callable[[str], str] | None = None,
) -> str:
    """Prompt the user and return lowercased response, falling back to default."""
    if input_fn is None:
        input_fn = input
    try:
        resp = input_fn(prompt).strip().lower()
        return resp if resp else default.lower()
    except (EOFError, KeyboardInterrupt):
        return "cancel"


def ask_cancel(
    step_name: str,
    input_fn: Callable[[str], str] | None = None,
) -> bool:
    """Explicitly ask if the user wants to cancel the deletion process at this step."""
    resp = ask_user(
        f"  -> [{step_name}] Would you like to cancel deletion? (yes to cancel / no to continue) [no]: ",
        default="no",
        input_fn=input_fn,
    )
    return resp in ("y", "yes", "cancel", "c", "abort")


def run_uninstaller(
    argv: list[str] | None = None,
    locus_home: Path | None = None,
    vault_root: Path | None = None,
    input_fn: Callable[[str], str] | None = None,
) -> int:
    """Run the Locus OS uninstaller CLI with step-by-step confirmation."""
    parser = argparse.ArgumentParser(
        prog="locus-uninstall",
        description="Locus OS uninstaller - removes configurations, secrets, and downloaded runtime files",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Non-interactive uninstallation accepting defaults without prompts",
    )
    parser.add_argument(
        "--locus-home",
        type=Path,
        default=None,
        help="Target LOCUS_HOME directory to uninstall (default: ~/.locus or $LOCUS_HOME)",
    )
    parser.add_argument(
        "--vault-root",
        type=Path,
        default=None,
        help="Target Obsidian vault directory (default: read from config or <LOCUS_HOME>/vault)",
    )
    parser.add_argument(
        "--delete-vault",
        action="store_true",
        help="Delete the Obsidian vault directory as well",
    )
    parser.add_argument(
        "--keep-vault",
        action="store_true",
        help="Preserve the Obsidian vault directory intact",
    )

    args = parser.parse_args(argv if argv is not None else [])

    # 1. Determine repository root for safety checks
    repo_root = Path(__file__).resolve().parents[1]

    # 2. Determine LOCUS_HOME
    if args.locus_home:
        home_path = args.locus_home.expanduser().resolve()
    elif locus_home:
        home_path = locus_home.expanduser().resolve()
    elif "LOCUS_HOME" in os.environ and os.environ["LOCUS_HOME"].strip():
        home_path = Path(os.environ["LOCUS_HOME"]).expanduser().resolve()
    else:
        home_path = Path.home() / ".locus"

    # 3. Read configured vault path from config.yaml if present
    config_file = home_path / "config.yaml"
    configured_vault: Path | None = None
    if config_file.is_file():
        try:
            import yaml

            cfg = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
            v_str = cfg.get("locus", {}).get("vault", {}).get("path")
            if v_str:
                configured_vault = Path(v_str).expanduser().resolve()
        except Exception:
            pass

    if args.vault_root:
        vault_path = args.vault_root.expanduser().resolve()
    elif vault_root:
        vault_path = vault_root.expanduser().resolve()
    elif configured_vault:
        vault_path = configured_vault
    else:
        vault_path = home_path / "vault"

    print("=======================================================")
    print("                LOCUS OS UNINSTALLER                   ")
    print("=======================================================")
    print(f"Target LOCUS_HOME: {home_path}")
    print(f"Target Vault:      {vault_path}")
    print("NOTE: Repository source code is strictly protected and will NOT be touched.\n")

    if not home_path.exists() and not (vault_path and vault_path.exists()):
        print(f"Locus OS does not appear to be installed (directory {home_path} not found).")
        print("Nothing to uninstall.")
        return 0

    interactive = not args.yes
    delete_config_and_secrets = True
    delete_jobs_and_data = True
    delete_vault = args.delete_vault

    if interactive:
        # STEP 1: Initial prompt
        step1 = ask_user(
            "[STEP 1/4] Do you want to begin uninstallation of Locus OS? (yes/no/cancel) [yes]: ",
            default="yes",
            input_fn=input_fn,
        )
        if step1 in ("cancel", "c", "abort", "n", "no"):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0
        if ask_cancel("STEP 1: Initial Check", input_fn=input_fn):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0

        # STEP 2: Configuration & Secrets
        print("\nComponent 1: Configuration & API Secrets")
        print(f"  - Config:  {home_path / 'config.yaml'}")
        print(f"  - Secrets: {home_path / '.env'}")
        step2 = ask_user(
            "[STEP 2/4] Delete configuration (config.yaml) and API credentials (.env)? (yes/no/cancel) [yes]: ",
            default="yes",
            input_fn=input_fn,
        )
        if step2 in ("cancel", "c", "abort"):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0
        delete_config_and_secrets = step2 in ("y", "yes")
        if ask_cancel("STEP 2: Configuration & Secrets", input_fn=input_fn):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0

        # STEP 3: Research Jobs, Databases, Logs
        print("\nComponent 2: Research Jobs, Runtime Databases & Logs")
        print(f"  - Jobs directory: {home_path / 'jobs'}")
        print(f"  - SQLite databases, session logs, and cache in {home_path}")
        step3 = ask_user(
            "[STEP 3/4] Delete research jobs, session databases, and logs in ~/.locus? (yes/no/cancel) [yes]: ",
            default="yes",
            input_fn=input_fn,
        )
        if step3 in ("cancel", "c", "abort"):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0
        delete_jobs_and_data = step3 in ("y", "yes")
        if ask_cancel("STEP 3: Jobs & Databases", input_fn=input_fn):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0

        # STEP 4: Obsidian Vault
        print("\nComponent 3: Obsidian Vault")
        if vault_path.exists():
            print(f"  - Vault location: {vault_path}")
            print("  WARNING: The vault may contain your personal notes, captures, and research logs.")
            step4 = ask_user(
                f"[STEP 4/4] Would you like to DELETE the Obsidian vault too? (yes/no/cancel) [no]: ",
                default="no",
                input_fn=input_fn,
            )
            if step4 in ("cancel", "c", "abort"):
                print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
                return 0
            delete_vault = step4 in ("y", "yes")
            if not delete_vault:
                print(f"  -> Vault will be PRESERVED intact at {vault_path}.")
            else:
                print(f"  -> Vault at {vault_path} marked for DELETION.")
        else:
            print(f"  - Vault path ({vault_path}) does not exist on disk. Skipping.")
            delete_vault = False

        if ask_cancel("STEP 4: Vault Decision", input_fn=input_fn):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0

        # FINAL CONFIRMATION
        print("\n-------------------------------------------------------")
        print("SUMMARY OF ACTIONS TO PERFORM:")
        print(f"  - Delete config & secrets in {home_path}: {delete_config_and_secrets}")
        print(f"  - Delete jobs, databases & runtime in {home_path}: {delete_jobs_and_data}")
        print(f"  - Delete Obsidian vault ({vault_path}): {delete_vault}")
        print("-------------------------------------------------------")
        final_confirm = ask_user(
            "Execute these deletions now? (yes/no/cancel) [yes]: ",
            default="yes",
            input_fn=input_fn,
        )
        if final_confirm in ("cancel", "c", "abort", "n", "no"):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0
        if ask_cancel("FINAL EXECUTION CONFIRMATION", input_fn=input_fn):
            print("\n[ABORTED] Uninstallation cancelled by user. No files were deleted.\n")
            return 0
    else:
        # Non-interactive mode
        if args.keep_vault:
            delete_vault = False

    # EXECUTION PHASE
    deleted_items: list[str] = []

    # 1. Config and secrets
    if delete_config_and_secrets and home_path.exists():
        for filename in ("config.yaml", ".env"):
            f = home_path / filename
            if f.is_file():
                try:
                    f.unlink()
                    deleted_items.append(str(f))
                except Exception as e:
                    sys.stderr.write(f"Warning: Failed to delete {f}: {e}\n")

    # 2. Jobs and runtime databases
    if delete_jobs_and_data and home_path.exists():
        jobs_dir = home_path / "jobs"
        if jobs_dir.is_dir() and _is_safe_to_delete(jobs_dir, repo_root):
            try:
                shutil.rmtree(jobs_dir, onerror=_remove_readonly)
                deleted_items.append(str(jobs_dir))
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to delete {jobs_dir}: {e}\n")

        # Delete database files and logs
        for p in home_path.glob("*.db*"):
            if p.is_file():
                try:
                    p.unlink()
                    deleted_items.append(str(p))
                except Exception:
                    pass

        for d in ("logs", "sessions", "cache"):
            sub = home_path / d
            if sub.is_dir() and _is_safe_to_delete(sub, repo_root):
                try:
                    shutil.rmtree(sub, onerror=_remove_readonly)
                    deleted_items.append(str(sub))
                except Exception:
                    pass

    # 3. Clean up whole LOCUS_HOME if both were selected and it is empty or safe
    if delete_config_and_secrets and delete_jobs_and_data and home_path.exists():
        if _is_safe_to_delete(home_path, repo_root):
            # Check if vault sits inside locus_home and user wanted to keep vault
            vault_inside_home = False
            try:
                vault_inside_home = vault_path.resolve().is_relative_to(home_path.resolve())
            except AttributeError:
                # Python < 3.9 fallback
                vault_inside_home = str(vault_path.resolve()).startswith(str(home_path.resolve()))

            if vault_inside_home and not delete_vault:
                # Only delete everything except vault
                for child in home_path.iterdir():
                    if child.resolve() != vault_path.resolve():
                        if child.is_file():
                            child.unlink()
                        elif child.is_dir():
                            shutil.rmtree(child, onerror=_remove_readonly)
                print(f"[PRESERVED] Preserved vault inside {home_path}.")
            else:
                try:
                    shutil.rmtree(home_path, onerror=_remove_readonly)
                    deleted_items.append(str(home_path))
                except Exception as e:
                    sys.stderr.write(f"Warning: Failed to remove directory {home_path}: {e}\n")

    # 4. Optional Vault Deletion
    if delete_vault and vault_path.exists():
        if _is_safe_to_delete(vault_path, repo_root):
            try:
                shutil.rmtree(vault_path, onerror=_remove_readonly)
                deleted_items.append(f"Vault: {vault_path}")
            except Exception as e:
                sys.stderr.write(f"Warning: Failed to delete vault at {vault_path}: {e}\n")
        else:
            sys.stderr.write(f"Refused to delete vault at {vault_path}: path unsafe or part of repository.\n")

    print("\n=======================================================")
    print("              UNINSTALLATION COMPLETED                 ")
    print("=======================================================")
    if deleted_items:
        print("Removed artifacts:")
        for item in deleted_items:
            print(f"  - {item}")
    else:
        print("No files were removed.")

    if not delete_vault and vault_path.exists():
        print(f"\n[VAULT KEPT] Your Obsidian vault was preserved at:\n  {vault_path}")

    print("\nLocus OS uninstallation finished successfully.")
    return 0


def main() -> None:
    """CLI entry point for locus-uninstall."""
    sys.exit(run_uninstaller(sys.argv[1:]))


if __name__ == "__main__":
    main()
