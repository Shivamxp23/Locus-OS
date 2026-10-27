"""
SPEC §25.15 lines 4910-4922: Cross-Faction Efficiency Unit Tests (F-0116 / US-93).
"""
import pytest
from sidecar import config
from sidecar.life_os.cross_faction import (
    CrossFactionAggregateResult,
    CrossFactionAllocator,
    FactionSplitResult,
)
from sidecar.providers.cross_faction import (
    BaseCrossFactionEfficiencyProvider,
    DefaultCrossFactionEfficiencyProvider,
)


@pytest.fixture(autouse=True)
def clean_config():
    """Reset configuration keys around each test."""
    config.set("locus.cross_faction_efficiency.enabled", True)
    config.set("locus.life_os.cross_faction.enabled", True)
    yield
    config.set("locus.cross_faction_efficiency.enabled", True)
    config.set("locus.life_os.cross_faction.enabled", True)


def test_cross_faction_split_prevents_double_counting():
    """SPEC §25.15 line 4914: "tasks tagged with multiple factions count toward both targets (weighted by primary/secondary split). Prevents double-counting." """
    allocator = CrossFactionAllocator()
    duration = 100.0  # 100 minutes

    # Task with primary Craft, secondary Leverage
    res = allocator.calculate_task_split(
        task_id="task-multi-1",
        duration=duration,
        primary_faction="Craft",
        secondary_factions=["Leverage"],
    )

    assert res.task_id == "task-multi-1"
    assert res.cross_faction_enabled is True
    assert res.primary_faction == "Craft"
    assert res.secondary_factions == ["Leverage"]

    # Check weights (70% primary, 30% secondary)
    assert res.weights["Craft"] == 0.70
    assert res.weights["Leverage"] == 0.30

    # Check allocations
    assert res.allocations["Craft"] == 70.0
    assert res.allocations["Leverage"] == 30.0

    # CRITICAL: Exact sum conservation prevents double counting!
    assert sum(res.allocations.values()) == duration


def test_cross_faction_split_multiple_secondaries():
    """SPEC §25.15 line 4914: "tasks tagged with multiple factions count toward both targets (weighted by primary/secondary split). Prevents double-counting." """
    allocator = CrossFactionAllocator()
    duration = 120.0

    # Task with primary Craft, secondaries Health and Expression
    res = allocator.calculate_task_split(
        task_id="task-multi-2",
        duration=duration,
        primary_faction="Craft",
        secondary_factions=["Health", "Expression"],
    )

    # 70% to primary, 15% to each of the 2 secondaries
    assert res.weights["Craft"] == 0.70
    assert res.weights["Health"] == 0.15
    assert res.weights["Expression"] == 0.15

    assert res.allocations["Craft"] == 84.0
    assert res.allocations["Health"] == 18.0
    assert res.allocations["Expression"] == 18.0

    # Sum conservation
    assert sum(res.allocations.values()) == duration


def test_cross_faction_custom_weights():
    """SPEC §25.15 line 4914: "tasks tagged with multiple factions count toward both targets (weighted by primary/secondary split). Prevents double-counting." """
    allocator = CrossFactionAllocator()
    duration = 90.0

    # Explicit 60/40 custom split
    custom_weights = {"Craft": 0.60, "Leverage": 0.40}
    res = allocator.calculate_task_split(
        task_id="task-custom",
        duration=duration,
        primary_faction="Craft",
        secondary_factions=["Leverage"],
        custom_weights=custom_weights,
    )

    assert res.allocations["Craft"] == 54.0
    assert res.allocations["Leverage"] == 36.0
    assert sum(res.allocations.values()) == duration


def test_cross_faction_off_switch_counts_primary_only():
    """SPEC §25.15 line 4918: "Swappable / off state: locus.life_os.cross_faction.enabled. Off -> tasks count toward primary faction only." """
    allocator = CrossFactionAllocator()
    duration = 80.0

    # Disable cross-faction efficiency
    config.set("locus.life_os.cross_faction.enabled", False)
    assert allocator.is_cross_faction_enabled() is False

    res = allocator.calculate_task_split(
        task_id="task-off",
        duration=duration,
        primary_faction="Craft",
        secondary_factions=["Health", "Leverage"],
    )

    assert res.cross_faction_enabled is False
    # When OFF: 100% of duration goes to primary faction only
    assert res.allocations["Craft"] == 80.0
    assert res.allocations.get("Health", 0.0) == 0.0
    assert res.allocations.get("Leverage", 0.0) == 0.0
    assert sum(res.allocations.values()) == duration


def test_cross_faction_aggregate_tasks():
    """SPEC §25.15 line 4914: "tasks tagged with multiple factions count toward both targets (weighted by primary/secondary split). Prevents double-counting." """
    allocator = CrossFactionAllocator()
    tasks = [
        # Pure Craft task: 60 mins
        {"id": "t1", "duration": 60.0, "primary_faction": "Craft"},
        # Cross task: Craft (primary) + Health (secondary): 100 mins -> 70 Craft, 30 Health
        {"id": "t2", "duration": 100.0, "primary_faction": "Craft", "secondary_factions": ["Health"]},
        # Pure Health task: 40 mins
        {"id": "t3", "duration": 40.0, "primary_faction": "Health"},
    ]

    agg = allocator.aggregate_tasks(tasks)
    assert agg.task_count == 3
    assert agg.cross_faction_task_count == 1
    assert agg.total_duration == 200.0

    # Faction totals:
    # Craft: 60 + 70 = 130
    # Health: 30 + 40 = 70
    assert agg.faction_totals["Craft"] == 130.0
    assert agg.faction_totals["Health"] == 70.0
    assert sum(agg.faction_totals.values()) == 200.0


def test_cross_faction_provider_contract_and_modular_off_switch():
    """SPEC §25.15 lines 4910-4922: Provider contract and modular off-switch locus.cross_faction_efficiency.enabled."""
    provider = DefaultCrossFactionEfficiencyProvider()
    assert isinstance(provider, BaseCrossFactionEfficiencyProvider)
    assert provider.name == "default_cross_faction_efficiency_provider"

    # Enabled calculation
    split = provider.calculate_task_split("t1", 100.0, "Craft", ["Leverage"])
    assert split["allocations"]["Craft"] == 70.0
    assert split["allocations"]["Leverage"] == 30.0

    # Disable master switch -> 503
    config.set("locus.cross_faction_efficiency.enabled", False)
    off_split = provider.calculate_task_split("t1", 100.0, "Craft", ["Leverage"])
    assert off_split["status_code"] == 503
    assert off_split["disabled"] == "locus.cross_faction_efficiency.enabled"

    off_agg = provider.aggregate_tasks([])
    assert off_agg["status_code"] == 503
