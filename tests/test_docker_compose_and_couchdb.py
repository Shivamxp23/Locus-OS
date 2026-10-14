"""Unit tests for Docker Compose configuration and CouchDB hardening (US-03 / F-0086 / S-2).

Verifies:
- docker-compose.yml uses ${COUCHDB_PASSWORD:?set it in .locus/.env} without default fallback.
- All published ports (5984, 7687, 5432, 6379, 8420) are bound to 127.0.0.1 loopback.
- data/couchdb/local.ini restricts CORS origins strictly to Obsidian LiveSync endpoints.
- Old default password string does not appear in compose or ini files.
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
LOCAL_INI_FILE = REPO_ROOT / "data" / "couchdb" / "local.ini"


def test_docker_compose_exists_and_parses():
    """Verify docker-compose.yml exists and is valid YAML."""
    assert COMPOSE_FILE.is_file(), f"docker-compose.yml must exist at {COMPOSE_FILE}"
    content = COMPOSE_FILE.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert isinstance(data, dict)
    assert "services" in data


def test_couchdb_password_enforces_env_requirement():
    """Verify COUCHDB_PASSWORD has no default fallback and requires .locus/.env."""
    content = COMPOSE_FILE.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    couch = data["services"].get("locus-couchdb")
    assert couch is not None, "locus-couchdb service missing in docker-compose.yml"

    env_list = couch.get("environment", [])
    assert any("COUCHDB_PASSWORD=${COUCHDB_PASSWORD:?set it in .locus/.env}" in str(e) for e in env_list), \
        "locus-couchdb environment must enforce ${COUCHDB_PASSWORD:?set it in .locus/.env}"

    # Assert no default fallback pattern exists for COUCHDB_PASSWORD
    assert not re.search(r"COUCHDB_PASSWORD=\$\{[^}]+:-", content), \
        "COUCHDB_PASSWORD must not have a default fallback (e.g. :-)"


def test_all_ports_bind_to_loopback():
    """Verify all published ports bind to 127.0.0.1 and not 0.0.0.0 or bare port."""
    content = COMPOSE_FILE.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    expected_ports = {"5984", "7687", "5432", "6379", "8420"}
    found_ports = set()

    for service_name, service_cfg in data["services"].items():
        ports = service_cfg.get("ports", [])
        for p in ports:
            p_str = str(p)
            assert p_str.startswith("127.0.0.1:"), \
                f"Service {service_name} port {p_str} must bind to 127.0.0.1 (e.g. 127.0.0.1:port:port)"
            # Extract target port
            m = re.match(r"^127\.0\.0\.1:(\d+):(\d+)$", p_str)
            assert m is not None, f"Malformed port specification {p_str} in {service_name}"
            found_ports.add(m.group(1))

    # Ensure all headline ports are accounted for
    missing = expected_ports - found_ports
    assert not missing, f"Expected published ports missing from compose: {missing}"


def test_couchdb_local_ini_cors_restrictions():
    """Verify data/couchdb/local.ini CORS limits."""
    assert LOCAL_INI_FILE.is_file(), f"local.ini must exist at {LOCAL_INI_FILE}"

    cp = configparser.ConfigParser()
    cp.read(LOCAL_INI_FILE, encoding="utf-8")

    assert cp.has_section("httpd"), "local.ini missing [httpd] section"
    assert cp.getboolean("httpd", "enable_cors") is True

    assert cp.has_section("cors"), "local.ini missing [cors] section"
    origins = cp.get("cors", "origins").split(",")
    expected_origins = {"app://obsidian.md", "capacitor://localhost", "http://localhost"}
    assert set(origins) == expected_origins, f"CORS origins must be exactly {expected_origins}, got {origins}"
    assert cp.getboolean("cors", "credentials") is True


def test_no_old_default_password_in_repo_configs():
    """Verify obsolete default password does not leak in docker-compose.yml or local.ini."""
    compose_text = COMPOSE_FILE.read_text(encoding="utf-8")
    ini_text = LOCAL_INI_FILE.read_text(encoding="utf-8")

    forbidden_substr = "locus" + "_" + "admin" + "_" + "secret"
    assert forbidden_substr not in compose_text
    assert forbidden_substr not in ini_text
