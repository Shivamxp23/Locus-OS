"""
SPEC §10 S-1 / F-0083 / US-04: Setup CLI helper for generating Telegram pairing code.
Shows the one-time code ONLY on the machine running setup.
"""
from __future__ import annotations

import argparse
import sys

from sidecar.telegram.pairing import PairingManager


def generate_and_print_pairing_code(manager: PairingManager | None = None) -> str:
    """Generate and display the one-time Telegram pairing code on this machine."""
    mgr = manager or PairingManager()
    code = mgr.generate_pairing_code()
    print("=" * 60)
    print("LOCUS TELEGRAM SECURE PAIRING")
    print(f"One-time pairing code: {code}")
    print("Valid for 10 minutes. Works once.")
    print(f"Send this message from your Telegram account: /pair {code}")
    print("=" * 60)
    return code


def main() -> None:
    parser = argparse.ArgumentParser(description="Locus Telegram Pairing Setup")
    parser.add_argument("--repair", action="store_true", help="Re-pair Telegram owner")
    args = parser.parse_args()
    generate_and_print_pairing_code()


if __name__ == "__main__":
    main()
