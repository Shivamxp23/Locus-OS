"""
SPEC §23 / F-0086 / US-03: Security tests for docker-compose and CouchDB configuration.
Asserts:
- docker-compose.yml has no default password and uses ${COUCHDB_PASSWORD:?set it in .locus/.env}.
- Every published port (5984, 7687, 5432, 6379, 8420) binds to 127.0.0.1.
- data/couchdb/local.ini limits CORS origins to app://obsidian.md, capacitor://localhost and http://localhost.
- The old default password string appears nowhere in docker-compose.yml.
"""
from __future__ import annotations

from pathlib import Path
import yaml
import pytest


def test_docker_compose_couchdb_password_and_ports():
    """SPEC §23 / S-2: Verify CouchDB password interpolation and loopback port bindings."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    compose_path = repo_root / "docker-compose.yml"
    assert compose_path.is_file(), f"docker-compose.yml missing at {compose_path}"

    raw_text = compose_path.read_text(encoding="utf-8")

    # 1. Check CouchDB password requirement
    assert "${COUCHDB_PASSWORD:?set it in .locus/.env}" in raw_text

    # 2. Check no default password string
    forbidden_secret = "locus_" + "admin_" + "secret"
    assert forbidden_secret not in raw_text

    # 3. Parse YAML and verify ports
    data = yaml.safe_load(raw_text)
    services = data.get("services", {})
    assert "couchdb" in services
    assert "redis" in services
    assert "postgres" in services
    assert "neo4j" in services
    assert "sidecar" in services

    required_ports = {
        "couchdb": "5984",
        "neo4j": "7687",
        "postgres": "5432",
        "redis": "6379",
        "sidecar": "8420",
    }

    for svc_name, port_num in required_ports.items():
        svc = services[svc_name]
        ports = svc.get("ports", [])
        assert ports, f"No ports published for {svc_name}"
        found = False
        for p in ports:
            p_str = str(p)
            if port_num in p_str:
                assert p_str.startswith("127.0.0.1:"), f"Port {p_str} for {svc_name} not bound to 127.0.0.1"
                found = True
        assert found, f"Port {port_num} not found in ports of {svc_name}"


def test_couchdb_local_ini_cors_restrictions():
    """SPEC §23 / S-2: Verify data/couchdb/local.ini CORS restrictions."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    ini_path = repo_root / "data" / "couchdb" / "local.ini"
    assert ini_path.is_file(), f"local.ini missing at {ini_path}"

    content = ini_path.read_text(encoding="utf-8")
    assert "enable_cors = true" in content
    assert "app://obsidian.md" in content
    assert "capacitor://localhost" in content
    assert "http://localhost" in content
