"""
Unit tests for Veridia Deterministic Matching & Scoring Engine
"""
import pytest
from datetime import date
from src.data_pipeline import get_pipeline
from src.matching_engine import MatchingEngine
from src.models import BuyerRequirement
from src.config import DEFAULT_AS_OF_DATE

@pytest.fixture(scope="module")
def engine():
    pipe = get_pipeline()
    records = pipe.load_and_sanitize()
    return MatchingEngine(records)

def test_german_buyer_scenario(engine):
    """A buyer in Germany is looking for aluminium parts, machined to order, in batches of a few thousand over time."""
    req = BuyerRequirement(
        buyer_name="German Precision Buyer",
        material="aluminium",
        process="machined",
        quantity=2000,
        timeline_weeks=6,
        required_certifications=["ISO 9001"],
        destination_country="Germany"
    )

    res = engine.match(req, top_k=5)
    assert res.eligible_count > 0
    assert len(res.matches) == 5

    # Verify top match criteria
    top = res.matches[0]
    assert top.eligible is True
    assert "aluminium" in [m.lower() for m in top.manufacturer.materials]
    assert any(p.lower() in ["cnc milling", "cnc turning", "grinding"] for p in top.manufacturer.processes)
    assert top.manufacturer.min_order_qty <= 2000 <= top.manufacturer.max_order_qty
    assert top.manufacturer.lead_time_weeks <= 6.0
    assert "ISO 9001" in [c.upper() for c in top.manufacturer.certifications]
    assert top.score_breakdown.total_score >= 85.0

def test_hard_gatekeeper_process_filtering(engine):
    """Disqualifies suppliers lacking the requested process."""
    req = BuyerRequirement(
        material="aluminium",
        process="forging",
        quantity=500,
        timeline_weeks=12,
        required_certifications=[]
    )
    res = engine.match(req, top_k=10)
    for m in res.matches:
        assert "forging" in [p.lower() for p in m.manufacturer.processes]

def test_order_quantity_moq_and_max(engine):
    """Disqualifies suppliers when order quantity violates MOQ or Max Order Qty."""
    # Extremely small order: 10 units (below virtually all MOQs)
    req_tiny = BuyerRequirement(
        material="aluminium",
        process="CNC milling",
        quantity=10,
        timeline_weeks=10
    )
    res_tiny = engine.match(req_tiny)
    assert res_tiny.eligible_count == 0
    assert res_tiny.relaxed_matches is not None
    # Check that reasons mention MOQ
    assert any("below MOQ" in r for rm in res_tiny.relaxed_matches for r in rm.disqualification_reasons)

def test_matching_determinism(engine):
    """The same request on the same as_of_date must ALWAYS yield bit-exact identical rankings."""
    req = BuyerRequirement(
        buyer_name="Deterministic Audit Test",
        material="aluminium",
        process="CNC milling",
        quantity=1500,
        timeline_weeks=6,
        required_certifications=["ISO 9001"],
        as_of_date=date(2026, 10, 28)
    )

    res1 = engine.match(req, top_k=5)
    res2 = engine.match(req, top_k=5)

    assert res1.eligible_count == res2.eligible_count
    for m1, m2 in zip(res1.matches, res2.matches):
        assert m1.manufacturer.manufacturer_id == m2.manufacturer.manufacturer_id
        assert m1.score_breakdown.total_score == m2.score_breakdown.total_score
        assert m1.score_breakdown.speed_score == m2.score_breakdown.speed_score
        assert m1.score_breakdown.reliability_score == m2.score_breakdown.reliability_score

def test_in_flight_requirement_delta_tracking(engine):
    """Tracks and reports notes when a buyer modifies requirement partway through."""
    prev_req = BuyerRequirement(
        session_id="session_delta",
        material="aluminium",
        process="CNC milling",
        quantity=1000,
        timeline_weeks=6
    )
    curr_req = BuyerRequirement(
        session_id="session_delta",
        material="aluminium",
        process="CNC milling",
        quantity=3500,
        timeline_weeks=4
    )

    res = engine.match(curr_req, previous_req=prev_req)
    assert res.query_delta_notes is not None
    assert len(res.query_delta_notes) >= 2
    assert any("increased from 1,000 to 3,500" in n for n in res.query_delta_notes)
    assert any("compressed from 6w to 4w" in n for n in res.query_delta_notes)
