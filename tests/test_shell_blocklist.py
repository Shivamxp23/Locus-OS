import pytest
from sidecar.security.shell_blocklist import (
    SENSITIVE_HOME_DIRS,
    SENSITIVE_HOME_FILES,
    ShellBlocklist,
)


def test_sensitive_path_blocking():
    blocklist = ShellBlocklist(home_dir="/home/user")

    # Sensitive files
    assert blocklist.is_read_blocked("/home/user/.ssh/id_rsa")
    assert blocklist.is_read_blocked("/home/user/.aws/credentials")
    assert blocklist.is_read_blocked("/home/user/.bashrc")
    assert blocklist.is_write_denied("/home/user/.ssh/authorized_keys")

    # Benign files allowed
    assert not blocklist.is_read_blocked("/home/user/project/src/main.py")
    assert not blocklist.is_write_denied("/home/user/project/README.md")


def test_dangerous_shell_command_blocking():
    blocklist = ShellBlocklist()

    assert blocklist.is_command_blocked("rm -rf /")
    assert blocklist.is_command_blocked("rm -rf ~")
    assert blocklist.is_command_blocked(":(){ :|:& };:")
    assert blocklist.is_command_blocked("mkfs.ext4 /dev/sda1")

    # Safe commands allowed
    assert not blocklist.is_command_blocked("ls -la")
    assert not blocklist.is_command_blocked("git status")
    assert not blocklist.is_command_blocked("npm run test")


def test_evaluate_command():
    blocklist = ShellBlocklist()
    res_danger = blocklist.evaluate_command("rm -rf /")
    assert not res_danger["allowed"]

    res_safe = blocklist.evaluate_command("echo 'hello'")
    assert res_safe["allowed"]
