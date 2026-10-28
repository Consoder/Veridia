"""
Unit tests for Veridia Concurrency & Capacity Allocation Manager
"""
import pytest
from src.data_pipeline import get_pipeline
from src.matching_engine import MatchingEngine
from src.allocation_manager import AllocationManager
from src.models import BuyerRequirement

@pytest.fixture(scope="module")
def allocator():
    pipe = get_pipeline()
    records = pipe.load_and_sanitize()
    engine = MatchingEngine(records)
    return AllocationManager(engine)

def test_two_buyer_contention_pareto_resolution(allocator):
    """
    Prompt Scenario:
    Buyer A: 1,000 aluminium CNC parts with ISO 9001, within 6 weeks.
    Buyer B: 1,500 stainless sheet-metal parts with ISO 9001, within 6 weeks.
    Both reach you at the same time.
    """
    req_a = BuyerRequirement(
        session_id="buyer_a_session",
        buyer_name="Buyer A",
        material="aluminium",
        process="CNC",
        quantity=1000,
        timeline_weeks=6,
        required_certifications=["ISO 9001"]
    )
    req_b = BuyerRequirement(
        session_id="buyer_b_session",
        buyer_name="Buyer B",
        material="stainless steel",
        process="sheet metal",
        quantity=1500,
        timeline_weeks=6,
        required_certifications=["ISO 9001"]
    )

    sim = allocator.simulate_two_buyers(req_a, req_b, strategy="pareto_optimal")

    assert sim.buyer_a_allocated is not None
    assert sim.buyer_b_allocated is not None
    assert sim.buyer_a_allocated.score_breakdown.total_score > 70.0
    assert sim.buyer_b_allocated.score_breakdown.total_score > 50.0

    # Under Pareto Optimal, Buyer A gets dedicated CNC specialist and Buyer B gets sheet metal specialist
    assert "Betwa Crest Precision Components" in sim.buyer_b_allocated.manufacturer.name

def test_capacity_reservation_and_depletion(allocator):
    """Verifies that placing a soft reservation depletes available capacity for concurrent buyers."""
    mfg_id = "VM1006" # Has 1,500 capacity
    initial_cap = allocator.get_available_capacities()[mfg_id]
    assert initial_cap == 1500

    # Session 1 reserves 1,000 units
    ok = allocator.reserve_capacity(session_id="user_1", manufacturer_id=mfg_id, units=1000)
    assert ok is True

    # Check residual capacity
    cap_after_reserve = allocator.get_available_capacities()[mfg_id]
    assert cap_after_reserve == 500

    # Session 2 tries to reserve 1,000 units (fails because only 500 left)
    ok_fail = allocator.reserve_capacity(session_id="user_2", manufacturer_id=mfg_id, units=1000)
    assert ok_fail is False

    # Session 1 releases reservation
    allocator.release_reservation(session_id="user_1")
    cap_after_release = allocator.get_available_capacities()[mfg_id]
    assert cap_after_release == 1500
