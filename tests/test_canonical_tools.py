import pytest
from sidecar.tools.canonical import (
    CANONICAL_TOOL_NAMES,
    CanonicalToolRegistry,
)


def test_13_canonical_tools_registered():
    registry = CanonicalToolRegistry()
    assert len(registry.tools) == 13
    for name in CANONICAL_TOOL_NAMES:
        assert name in registry.tools


def test_tool_execution():
    registry = CanonicalToolRegistry()

    checkin = registry.execute("locus_checkin", {"dcs": 90})
    assert checkin["status"] == "ok"
    assert checkin["dcs"] == 90

    doctor = registry.execute("locus_doctor", {})
    assert doctor["status"] == "healthy"
    assert doctor["checks"] == 13

    diag = registry.execute("locus_diagram", {"type": "flowchart"})
    assert diag["status"] == "rendered"


def test_missing_tool_raises_error():
    registry = CanonicalToolRegistry()
    with pytest.raises(KeyError):
        registry.execute("unknown_tool", {})
