"""
Unit tests for Autonomy Tiers (SPEC §13.4 / F-0108 / US-70).
"""
import pytest

from sidecar.security.autonomy_tiers import (
    AutonomyTier,
    AutonomyTierManager,
    TierEvaluationDecision,
    ToolCategory,
)
from sidecar.providers.autonomy_tiers import (
    BaseAutonomyTiersProvider,
    DefaultAutonomyTiersProvider,
)
import sidecar.config as config


def test_tier_initialization_and_parsing():
    """SPEC §13.4 line 3328: "tier definitions in locus-os (repo); current tier set in .locus/config" """
    mgr = AutonomyTierManager(initial_tier="readonly")
    assert mgr.tier == AutonomyTier.READONLY

    mgr.set_tier("full")
    assert mgr.tier == AutonomyTier.FULL

    mgr.set_tier("supervised")
    assert mgr.tier == AutonomyTier.SUPERVISED

    # Case insensitivity and aliases
    assert AutonomyTier.from_str("READ_ONLY") == AutonomyTier.READONLY
    assert AutonomyTier.from_str("ro") == AutonomyTier.READONLY
    assert AutonomyTier.from_str("trusted") == AutonomyTier.FULL
    assert AutonomyTier.from_str("unknown_tier") == AutonomyTier.SUPERVISED


def test_readonly_tier_allows_read_tools():
    """SPEC §13.4 line 3321: "READONLY:    read tools only, no writes, no terminal" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.READONLY)
    for tool in ["read_file", "search_web", "query_graph", "list_resources", "view_structure"]:
        decision = mgr.evaluate(tool)
        assert decision.allowed is True
        assert decision.requires_approval is False
        assert decision.tier == "readonly"
        assert decision.category == "read"


def test_readonly_tier_blocks_write_tools():
    """SPEC §13.4 line 3321: "READONLY:    read tools only, no writes, no terminal" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.READONLY)
    for tool in ["write_file", "edit_file", "append_file", "delete_file"]:
        decision = mgr.evaluate(tool)
        assert decision.allowed is False
        assert decision.requires_approval is False
        assert decision.tier == "readonly"
        assert decision.category == "write"
        assert "blocked" in (decision.reason or "").lower() or "forbidden" in (decision.reason or "").lower()


def test_readonly_tier_blocks_terminal_tools():
    """SPEC §13.4 line 3321: "READONLY:    read tools only, no writes, no terminal" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.READONLY)
    for tool in ["run_command", "bash", "shell", "exec"]:
        decision = mgr.evaluate(tool)
        assert decision.allowed is False
        assert decision.requires_approval is False
        assert decision.tier == "readonly"
        assert decision.category == "terminal"
        assert "blocked" in (decision.reason or "").lower() or "forbidden" in (decision.reason or "").lower()


def test_supervised_tier_allows_read_tools():
    """SPEC §13.4 line 3322: "SUPERVISED:  write tools require explicit user approval (10-min TTL)" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.SUPERVISED)
    decision = mgr.evaluate("read_file")
    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.tier == "supervised"
    assert decision.category == "read"


def test_supervised_tier_requires_approval_for_write_tools():
    """SPEC §13.4 line 3322: "SUPERVISED:  write tools require explicit user approval (10-min TTL)" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.SUPERVISED)
    decision = mgr.evaluate("write_file", has_approval=False)
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.tier == "supervised"
    assert decision.category == "write"
    assert "require explicit user approval" in (decision.reason or "")


def test_supervised_tier_allows_write_with_approval():
    """SPEC §13.4 line 3322: "SUPERVISED:  write tools require explicit user approval (10-min TTL)" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.SUPERVISED)
    decision = mgr.evaluate("write_file", has_approval=True)
    assert decision.allowed is True
    assert decision.requires_approval is False
    assert decision.tier == "supervised"
    assert "approval verified" in (decision.reason or "").lower()


def test_supervised_tier_requires_approval_for_terminal_tools():
    """SPEC §13.4 line 3322: "SUPERVISED:  write tools require explicit user approval (10-min TTL)" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.SUPERVISED)
    decision = mgr.evaluate("run_command", has_approval=False)
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.tier == "supervised"
    assert decision.category == "terminal"

    # With approval
    approved_decision = mgr.evaluate("run_command", has_approval=True)
    assert approved_decision.allowed is True
    assert approved_decision.requires_approval is False


def test_full_tier_allows_all_tools():
    """SPEC §13.4 line 3323: "FULL:        all tools allowed (trusted mode)" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.FULL)
    for tool in ["read_file", "write_file", "run_command", "set_config", "random_custom_tool"]:
        decision = mgr.evaluate(tool, has_approval=False)
        assert decision.allowed is True
        assert decision.requires_approval is False
        assert decision.tier == "full"


def test_tool_classification_heuristics():
    """SPEC §13.4 line 3327: "Component: locus/security/autonomy-tiers.ts — gates tool execution in Pi's beforeToolCall hook" """
    mgr = AutonomyTierManager()
    assert mgr.classify_tool("fetch_data_from_remote") == ToolCategory.READ
    assert mgr.classify_tool("inspect_schema") == ToolCategory.READ
    assert mgr.classify_tool("check_status") == ToolCategory.READ
    assert mgr.classify_tool("execute_script") == ToolCategory.TERMINAL
    assert mgr.classify_tool("powershell_cmd") == ToolCategory.TERMINAL
    assert mgr.classify_tool("update_record") == ToolCategory.WRITE
    assert mgr.classify_tool("delete_item") == ToolCategory.WRITE
    assert mgr.classify_tool("system_restart") == ToolCategory.SYSTEM


def test_tool_override_registration():
    """SPEC §13.4 line 3327: "Component: locus/security/autonomy-tiers.ts — gates tool execution in Pi's beforeToolCall hook" """
    mgr = AutonomyTierManager(initial_tier=AutonomyTier.READONLY)
    # By default, unknown custom tool falls back to write
    assert mgr.classify_tool("custom_sensor_probe") == ToolCategory.WRITE
    # Register an override marking an unusual tool name as read
    mgr.register_tool_override("custom_sensor_probe", ToolCategory.READ)
    assert mgr.classify_tool("custom_sensor_probe") == ToolCategory.READ
    dec = mgr.evaluate("custom_sensor_probe")
    assert dec.allowed is True


def test_provider_tier_get_and_set():
    """SPEC §13.4 line 3329: "Swappable / off state: locus.security.autonomy_tier (readonly | supervised | full). Default: supervised." """
    provider = DefaultAutonomyTiersProvider(initial_tier="supervised")
    assert provider.is_available() is True
    assert provider.get_tier() == "supervised"

    res = provider.set_tier("readonly")
    assert res["status"] == "ok"
    assert res["tier"] == "readonly"
    assert provider.get_tier() == "readonly"


def test_provider_modular_off_switches(monkeypatch):
    """SPEC §13.4 line 3329: "Swappable / off state: locus.security.autonomy_tier (readonly | supervised | full). Default: supervised." """
    provider = DefaultAutonomyTiersProvider()
    assert provider.is_available() is True

    # Test locus.autonomy_tiers.enabled: false
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.autonomy_tiers.enabled" else default)
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.autonomy_tiers.enabled" else True)
    assert provider.is_available() is False

    # Test locus.security.autonomy_tiers.enabled: false
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.security.autonomy_tiers.enabled" else default)
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.security.autonomy_tiers.enabled" else True)
    assert provider.is_available() is False


def test_swappable_provider_swap():
    """SPEC §13.4 line 3329: "Swappable / off state: locus.security.autonomy_tier (readonly | supervised | full). Default: supervised." """
    class CustomAutonomyProvider(BaseAutonomyTiersProvider):
        def is_available(self) -> bool:
            return True

        def get_tier(self) -> str:
            return "full"

        def set_tier(self, tier: str):
            return {"status": "ok", "tier": "full"}

        def classify_tool(self, tool_name: str, explicit_category=None):
            return {"status": "ok", "tool_name": tool_name, "category": "read"}

        def evaluate_tool(self, tool_name: str, has_approval=False, category=None, tier=None):
            return {
                "status": "ok",
                "decision": {
                    "allowed": True,
                    "requires_approval": False,
                    "tier": "full",
                    "tool_name": tool_name,
                    "category": "read",
                    "reason": "custom provider allow-all",
                },
            }

        def get_tiers_info(self):
            return []

    custom = CustomAutonomyProvider()
    assert isinstance(custom, BaseAutonomyTiersProvider)
    assert custom.get_tier() == "full"
    res = custom.evaluate_tool("write_file")
    assert res["decision"]["allowed"] is True
