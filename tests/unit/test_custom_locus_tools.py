"""
Unit tests for Custom Locus Tools (SPEC §3.12 / F-0104).
Asserts standard tool registration, schema introspection, individual tool toggling,
parameter validation, execution error containment, and swappability.
"""
from __future__ import annotations

import pytest

from sidecar.custom_locus_tools import CustomLocusToolsProvider, _build_default_locus_tools
from sidecar.providers.custom_locus_tools import (
    BaseCustomLocusToolsProvider,
    CustomLocusToolsConfig,
    CustomToolResult,
    CustomToolSpec,
)


def test_default_tools_initialization() -> None:
    """SPEC §3.12 line 2709: "See §1.3 for the 8 custom Locus tools." """
    provider = CustomLocusToolsProvider()
    tools = provider.list_tools(include_disabled=True)
    tool_names = {t.name for t in tools}

    expected_eight = {
        "locus_checkin",
        "locus_memory",
        "locus_goals",
        "locus_life",
        "locus_vault",
        "locus_brain",
        "locus_research",
        "locus_delegate_code",
    }
    assert expected_eight.issubset(tool_names)
    assert len(tools) >= 8

    # Verify checkin tool schema
    checkin_spec = provider.get_tool("locus_checkin")
    assert checkin_spec is not None
    assert checkin_spec.category == "life_os"
    assert "energy" in checkin_spec.parameters["properties"]
    assert "mood" in checkin_spec.parameters["properties"]


def test_list_tools_filtering() -> None:
    """SPEC §3.12 line 2708: "Individual tools toggleable via locus.tools.<name>.enabled" """
    provider = CustomLocusToolsProvider()
    provider.set_tool_enabled("locus_vault", False)

    enabled_tools = provider.list_tools(include_disabled=False)
    enabled_names = {t.name for t in enabled_tools}
    assert "locus_vault" not in enabled_names
    assert "locus_checkin" in enabled_names

    all_tools = provider.list_tools(include_disabled=True)
    all_names = {t.name for t in all_tools}
    assert "locus_vault" in all_names


def test_individual_tool_toggle() -> None:
    """SPEC §3.12 line 2708: "Individual tools toggleable via locus.tools.<name>.enabled" """
    provider = CustomLocusToolsProvider()
    assert provider.is_tool_enabled("locus_memory") is True

    provider.set_tool_enabled("locus_memory", False)
    assert provider.is_tool_enabled("locus_memory") is False

    provider.set_tool_enabled("locus_memory", True)
    assert provider.is_tool_enabled("locus_memory") is True

    with pytest.raises(KeyError):
        provider.set_tool_enabled("non_existent_tool", False)


def test_execute_checkin_tool() -> None:
    """SPEC §3.12 line 2707: "- **Verdict**: 🆕 LOCUS-NEW · **Source**: Locus-unique" """
    provider = CustomLocusToolsProvider()
    params = {
        "energy": 8.0,
        "mood": 9.0,
        "sleep_hours": 8.0,
        "stress": 2.0,
        "notes": "Feeling great",
    }
    result = provider.execute_tool("locus_checkin", params)
    assert result.success is True
    assert result.tool_name == "locus_checkin"
    assert result.error is None
    assert result.output["recorded"] is True
    assert result.output["dcs"] > 7.0
    assert result.output["operating_mode"] in ("PEAK", "DEEP_WORK")


def test_execute_memory_tool() -> None:
    """SPEC §3.12 line 2709: "See §1.3 for the 8 custom Locus tools." """
    provider = CustomLocusToolsProvider()
    # Query action
    res_query = provider.execute_tool("locus_memory", {"action": "query", "query": "project goals"})
    assert res_query.success is True
    assert len(res_query.output["matches"]) >= 1

    # Store action
    res_store = provider.execute_tool("locus_memory", {"action": "store", "content": "Important meeting note"})
    assert res_store.success is True
    assert res_store.output["status"] == "persisted"


def test_execute_goals_and_life_tools() -> None:
    """SPEC §3.12 line 2709: "See §1.3 for the 8 custom Locus tools." """
    provider = CustomLocusToolsProvider()
    res_goals = provider.execute_tool("locus_goals", {"action": "list"})
    assert res_goals.success is True
    assert len(res_goals.output["goals"]) >= 1

    res_life = provider.execute_tool("locus_life", {})
    assert res_life.success is True
    assert "dcs" in res_life.output
    assert "factions" in res_life.output


def test_execute_missing_required_params() -> None:
    """SPEC §3.12 line 2706: "## Feature §3.12: Custom Locus Tools" """
    provider = CustomLocusToolsProvider()
    # locus_checkin requires energy, mood, sleep_hours, stress
    incomplete_params = {"energy": 7.0, "mood": 6.0}
    res = provider.execute_tool("locus_checkin", incomplete_params)
    assert res.success is False
    assert "Missing required parameter" in (res.error or "")


def test_execute_disabled_tool_rejected() -> None:
    """SPEC §3.12 line 2708: "Individual tools toggleable via locus.tools.<name>.enabled" """
    provider = CustomLocusToolsProvider()
    provider.set_tool_enabled("locus_delegate_code", False)

    res = provider.execute_tool("locus_delegate_code", {"task": "Build feature"})
    assert res.success is False
    assert "disabled" in (res.error or "")


def test_dynamic_tool_registration() -> None:
    """SPEC §3.12 line 2707: "- **Verdict**: 🆕 LOCUS-NEW · **Source**: Locus-unique" """
    provider = CustomLocusToolsProvider()
    custom_spec = CustomToolSpec(
        name="custom_calculator",
        description="Calculate simple math expressions",
        parameters={
            "type": "object",
            "properties": {"expr": {"type": "string"}},
            "required": ["expr"],
        },
        category="utility",
    )

    def calc_handler(params: dict) -> dict:
        return {"eval": eval(params["expr"])}

    assert provider.register_tool(custom_spec, handler=calc_handler) is True
    assert provider.get_tool("custom_calculator") is not None

    res = provider.execute_tool("custom_calculator", {"expr": "21 * 2"})
    assert res.success is True
    assert res.output["eval"] == 42


def test_custom_tool_error_containment() -> None:
    """SPEC §3.12 line 2706: "## Feature §3.12: Custom Locus Tools" """
    provider = CustomLocusToolsProvider()
    failing_spec = CustomToolSpec(
        name="failing_tool",
        description="Tool that intentionally fails",
        parameters={"type": "object"},
    )

    def explode(params: dict) -> dict:
        raise ValueError("Simulated handler crash")

    provider.register_tool(failing_spec, handler=explode)
    # Execution must NOT raise unhandled exception
    res = provider.execute_tool("failing_tool", {})
    assert res.success is False
    assert "Simulated handler crash" in (res.error or "")


def test_unregister_tool() -> None:
    """SPEC §3.12 line 2706: "## Feature §3.12: Custom Locus Tools" """
    provider = CustomLocusToolsProvider()
    dummy = CustomToolSpec(name="temp_tool", description="temp")
    provider.register_tool(dummy)
    assert provider.get_tool("temp_tool") is not None

    assert provider.unregister_tool("temp_tool") is True
    assert provider.get_tool("temp_tool") is None
    assert provider.unregister_tool("temp_tool") is False


def test_swappable_provider() -> None:
    """SPEC §3.12 line 2708: "Swappable / off state" """
    class MockCustomToolsProvider(BaseCustomLocusToolsProvider):
        def register_tool(self, spec: CustomToolSpec) -> bool:
            return True
        def unregister_tool(self, tool_name: str) -> bool:
            return True
        def get_tool(self, tool_name: str):
            return None
        def list_tools(self, include_disabled: bool = False):
            return []
        def is_tool_enabled(self, tool_name: str) -> bool:
            return True
        def set_tool_enabled(self, tool_name: str, enabled: bool) -> None:
            pass
        def execute_tool(self, tool_name: str, params: dict):
            return CustomToolResult(tool_name=tool_name, success=True, output={"mock": True})
        def get_config(self):
            return CustomLocusToolsConfig()
        def health_check(self):
            return {"status": "swapped"}

    swapped = MockCustomToolsProvider(name="mock_swapped")
    assert swapped.name == "mock_swapped"
    res = swapped.execute_tool("any", {})
    assert res.success is True
    assert res.output == {"mock": True}
    assert swapped.health_check()["status"] == "swapped"
