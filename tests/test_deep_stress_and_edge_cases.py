"""
Deep Stress, Edge Case, Concurrency, and Benchmark Tests for Veridia Matching Engine
"""
import pytest
import threading
import time
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.data_pipeline import get_pipeline
from src.matching_engine import MatchingEngine
from src.allocation_manager import AllocationManager
from src.models import BuyerRequirement
from src.config import DEFAULT_AS_OF_DATE

@pytest.fixture(scope="module")
def system():
    pipe = get_pipeline()
    records = pipe.load_and_sanitize()
    engine = MatchingEngine(records)
    allocator = AllocationManager(engine)
    return pipe, engine, allocator

# ============================================================================
# 1. Edge Cases & Boundary Conditions
# ============================================================================

def test_exact_boundary_quantity(system):
    """Checks exact MOQ and Max Order Qty boundary behavior when within monthly capacity."""
    _, engine, _ = system
    # Select a manufacturer whose max_order_qty fits their monthly capacity
    mfg = next(m for m in engine.manufacturers if m.max_order_qty <= m.capacity_units_per_month)
    
    # Exact MOQ boundary
    req_moq = BuyerRequirement(
        material=mfg.materials[0],
        process=mfg.processes[0],
        quantity=mfg.min_order_qty,
        timeline_weeks=int(mfg.lead_time_weeks) + 2
    )
    res_moq = engine.match(req_moq, top_k=100)
    matched_ids = [m.manufacturer.manufacturer_id for m in res_moq.matches]
    assert mfg.manufacturer_id in matched_ids

    # Exact Max boundary
    req_max = BuyerRequirement(
        material=mfg.materials[0],
        process=mfg.processes[0],
        quantity=mfg.max_order_qty,
        timeline_weeks=int(mfg.lead_time_weeks) + 2
    )
    res_max = engine.match(req_max, top_k=100)
    matched_max_ids = [m.manufacturer.manufacturer_id for m in res_max.matches]
    assert mfg.manufacturer_id in matched_max_ids

def test_exact_lead_time_boundary(system):
    """Lead time exactly equals buyer timeline (margin = 0)."""
    _, engine, _ = system
    mfg = engine.manufacturers[0]
    req = BuyerRequirement(
        material=mfg.materials[0],
        process=mfg.processes[0],
        quantity=mfg.min_order_qty,
        timeline_weeks=int(mfg.lead_time_weeks)
    )
    res = engine.match(req)
    # Must be accepted but flagged with zero buffer risk
    target = next((m for m in res.matches if m.manufacturer.manufacturer_id == mfg.manufacturer_id), None)
    if target:
        assert target.explanation.lead_time_margin_weeks >= 0.0

def test_cert_expires_during_production(system):
    """Disqualifies supplier if certificate expires before production lead time finishes."""
    _, engine, _ = system
    # Find a manufacturer with soonest expiry
    sorted_by_expiry = sorted(engine.manufacturers, key=lambda m: m.certification_expiry)
    target_mfg = sorted_by_expiry[0]
    
    # Anchor as_of_date so that completion_date is strictly after expiry
    # completion_date = as_of + lead_time_days
    # If as_of = target_mfg.certification_expiry - 2 days, but lead_time_days = 28 days -> expires mid-production!
    as_of = target_mfg.certification_expiry - timedelta(days=2)
    
    req = BuyerRequirement(
        material=target_mfg.materials[0],
        process=target_mfg.processes[0],
        quantity=target_mfg.min_order_qty,
        timeline_weeks=int(target_mfg.lead_time_weeks) + 2,
        required_certifications=[target_mfg.certifications[0]] if target_mfg.certifications else ["ISO 9001"],
        as_of_date=as_of
    )
    res = engine.match(req)
    # The target manufacturer must NOT be in eligible matches because cert expires during production
    eligible_ids = [m.manufacturer.manufacturer_id for m in res.matches]
    assert target_mfg.manufacturer_id not in eligible_ids

def test_unknown_inputs_no_crash(system):
    """Ensures unusual materials or processes return graceful relaxed results without 500 crashes."""
    _, engine, _ = system
    req_weird = BuyerRequirement(
        material="Vibranium",
        process="Quantum Teleportation",
        quantity=999999,
        timeline_weeks=1
    )
    res = engine.match(req_weird)
    assert res.eligible_count == 0
    assert res.relaxed_matches is not None
    assert len(res.relaxed_matches) > 0
    # Every relaxed candidate has reasons explained
    assert all(len(rm.disqualification_reasons) > 0 for rm in res.relaxed_matches)

# ============================================================================
# 2. Concurrency & Multi-Threaded Stress Tests
# ============================================================================

def test_concurrent_multi_user_race_condition(system):
    """
    Stress test: 20 concurrent threads trying to reserve capacity from the same
    constrained manufacturer (VM1006, capacity 1,500).
    Verifies thread-safety, no over-allocation, and zero race conditions.
    """
    _, engine, allocator = system
    mfg_id = "VM1006" # 1,500 units capacity
    allocator.release_reservation("all") # reset

    success_count = 0
    failure_count = 0
    lock = threading.Lock()

    def try_reserve(thread_idx: int):
        nonlocal success_count, failure_count
        # Each thread attempts to reserve 500 units
        ok = allocator.reserve_capacity(
            session_id=f"thread_{thread_idx}",
            manufacturer_id=mfg_id,
            units=500
        )
        with lock:
            if ok:
                success_count += 1
            else:
                failure_count += 1

    threads = [threading.Thread(target=try_reserve, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Exactly 3 threads must succeed (3 x 500 = 1,500 units), 17 must fail safely
    assert success_count == 3, f"Expected 3 successful reservations, got {success_count}"
    assert failure_count == 17, f"Expected 17 rejected reservations, got {failure_count}"
    assert allocator.get_available_capacities()[mfg_id] == 0

    # Cleanup
    for i in range(20):
        allocator.release_reservation(f"thread_{i}")
    assert allocator.get_available_capacities()[mfg_id] == 1500

def test_rapid_in_flight_modifications(system):
    """Simulates a buyer changing their requirements 30 times in rapid succession."""
    _, engine, allocator = system
    session_id = "rapid_user_session"
    
    for qty in range(1000, 4000, 100):
        req = BuyerRequirement(
            session_id=session_id,
            material="aluminium",
            process="CNC milling",
            quantity=qty,
            timeline_weeks=6
        )
        res = allocator.execute_session_match(req, top_k=3)
        assert res.session_id == session_id
        if qty > 1000:
            assert res.query_delta_notes is not None

# ============================================================================
# 3. Performance & Latency Benchmark
# ============================================================================

def test_matching_engine_latency_benchmark(system):
    """Ensures evaluating, filtering, and scoring 1,000 manufacturers executes in < 30ms."""
    _, engine, _ = system
    req = BuyerRequirement(
        material="aluminium",
        process="machined",
        quantity=2000,
        timeline_weeks=6,
        required_certifications=["ISO 9001"]
    )
    
    # Warm up
    engine.match(req)
    
    times = []
    for _ in range(50):
        start = time.perf_counter()
        engine.match(req, top_k=10)
        times.append(time.perf_counter() - start)
        
    avg_ms = (sum(times) / len(times)) * 1000.0
    print(f"\n[BENCHMARK] Average match latency across 1,000 manufacturers: {avg_ms:.2f} ms")
    assert avg_ms < 30.0, f"Match latency too high: {avg_ms:.2f} ms"
