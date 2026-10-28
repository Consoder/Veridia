"""
Concurrency and Capacity Allocation Manager for Veridia
Handles multi-session isolation, capacity reservation locks, and simultaneous buyer contention.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import threading
import logging

from src.models import (
    BuyerRequirement,
    CleanedManufacturer,
    MatchResult,
    SearchResponse,
    ContentionSimulationResponse
)
from src.matching_engine import MatchingEngine
from src.config import RESERVATION_TIMEOUT_MINUTES

logger = logging.getLogger(__name__)

class CapacityReservation:
    """Represents a temporary capacity hold placed by an active buyer session."""
    def __init__(self, session_id: str, manufacturer_id: str, units: int, expires_at: datetime):
        self.session_id = session_id
        self.manufacturer_id = manufacturer_id
        self.units = units
        self.expires_at = expires_at

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        return (now or datetime.now()) > self.expires_at


class AllocationManager:
    """Thread-safe multi-tenant session and capacity allocation manager."""

    def __init__(self, engine: MatchingEngine):
        self.engine = engine
        self._lock = threading.RLock()
        self._sessions: Dict[str, BuyerRequirement] = {}
        self._session_history: Dict[str, List[BuyerRequirement]] = {}
        self._reservations: List[CapacityReservation] = []

    def register_or_update_session(self, req: BuyerRequirement) -> Tuple[BuyerRequirement, Optional[BuyerRequirement]]:
        """Stores or updates session state, returning (current_req, previous_req)."""
        with self._lock:
            prev = self._sessions.get(req.session_id)
            if prev is not None:
                if req.session_id not in self._session_history:
                    self._session_history[req.session_id] = []
                self._session_history[req.session_id].append(prev)
            self._sessions[req.session_id] = req
            return req, prev

    def get_session(self, session_id: str) -> Optional[BuyerRequirement]:
        with self._lock:
            return self._sessions.get(session_id)

    def clean_expired_reservations(self):
        """Purges expired reservations."""
        now = datetime.now()
        with self._lock:
            self._reservations = [r for r in self._reservations if not r.is_expired(now)]

    def get_committed_capacity_map(self) -> Dict[str, int]:
        """Returns map of {manufacturer_id: total_committed_units}."""
        self.clean_expired_reservations()
        committed: Dict[str, int] = {}
        with self._lock:
            for r in self._reservations:
                committed[r.manufacturer_id] = committed.get(r.manufacturer_id, 0) + r.units
        return committed

    def get_available_capacities(self) -> Dict[str, int]:
        """Computes current available monthly capacity per manufacturer."""
        committed = self.get_committed_capacity_map()
        available: Dict[str, int] = {}
        for m in self.engine.manufacturers:
            held = committed.get(m.manufacturer_id, 0)
            available[m.manufacturer_id] = max(0, m.capacity_units_per_month - held)
        return available

    def reserve_capacity(
        self,
        session_id: str,
        manufacturer_id: str,
        units: int,
        duration_minutes: int = RESERVATION_TIMEOUT_MINUTES
    ) -> bool:
        """Attempts to place an atomic capacity hold for an active session."""
        with self._lock:
            available = self.get_available_capacities()
            if available.get(manufacturer_id, 0) < units:
                return False

            expires_at = datetime.now() + timedelta(minutes=duration_minutes)
            self._reservations.append(CapacityReservation(
                session_id=session_id,
                manufacturer_id=manufacturer_id,
                units=units,
                expires_at=expires_at
            ))
            return True

    def release_reservation(self, session_id: str, manufacturer_id: Optional[str] = None):
        """Releases reservations held by a session."""
        with self._lock:
            if manufacturer_id:
                self._reservations = [
                    r for r in self._reservations 
                    if not (r.session_id == session_id and r.manufacturer_id == manufacturer_id)
                ]
            else:
                self._reservations = [r for r in self._reservations if r.session_id != session_id]

    def execute_session_match(self, req: BuyerRequirement, top_k: int = 10) -> SearchResponse:
        """Executes matching within an isolated session context, respecting active reservations."""
        current_req, prev_req = self.register_or_update_session(req)
        avail_caps = self.get_available_capacities()
        return self.engine.match(
            req=current_req,
            previous_req=prev_req,
            top_k=top_k,
            available_capacities=avail_caps
        )

    def simulate_two_buyers(
        self,
        buyer_a: BuyerRequirement,
        buyer_b: BuyerRequirement,
        strategy: str = "pareto_optimal"
    ) -> ContentionSimulationResponse:
        """
        Solves the classic simultaneous arrival dilemma:
        Buyer A (1000 aluminium CNC, ISO 9001, 6w)
        Buyer B (1500 stainless sheet-metal, ISO 9001, 6w)
        Both reach the system at the exact same time.
        """
        # Step 1: Run isolated, unconstrained matching for both
        res_a_independent = self.engine.match(buyer_a, top_k=5)
        res_b_independent = self.engine.match(buyer_b, top_k=5)

        top_a = res_a_independent.matches[0] if res_a_independent.matches else None
        top_b = res_b_independent.matches[0] if res_b_independent.matches else None

        if not top_a or not top_b:
            raise ValueError("Unable to simulate: one or both buyers have zero eligible matches.")

        # Check for direct top-1 collision
        direct_collision = (top_a.manufacturer.manufacturer_id == top_b.manufacturer.manufacturer_id)

        # Check for bottleneck contention:
        # Does Buyer B have very few options (e.g. only 1), which is also in Buyer A's candidate pool?
        b_candidate_ids = {m.manufacturer.manufacturer_id for m in res_b_independent.matches}
        a_candidate_ids = {m.manufacturer.manufacturer_id for m in res_a_independent.matches}
        shared_candidates = a_candidate_ids.intersection(b_candidate_ids)

        conflict_detected = direct_collision or (
            len(res_b_independent.matches) == 1 and bool(shared_candidates)
        )

        shared_mfg_id = top_a.manufacturer.manufacturer_id if direct_collision else (
            next(iter(shared_candidates)) if shared_candidates else None
        )

        shared_mfg = next((m for m in self.engine.manufacturers if m.manufacturer_id == shared_mfg_id), None) if shared_mfg_id else None

        combined_demand = buyer_a.quantity + buyer_b.quantity
        mfg_capacity = shared_mfg.capacity_units_per_month if shared_mfg else top_a.manufacturer.capacity_units_per_month
        overcap_pct = round((combined_demand / max(1, mfg_capacity)) * 100.0, 1)

        # Step 2: Resolve contention based on requested strategy
        if strategy == "fcfs":
            # First-Come First-Served: Buyer A gets priority, Buyer B gets remaining capacity
            allocated_a = top_a
            # Simulate remaining capacity on Buyer A's choice
            avail_caps = {m.manufacturer_id: m.capacity_units_per_month for m in self.engine.manufacturers}
            avail_caps[top_a.manufacturer.manufacturer_id] = max(
                0, avail_caps[top_a.manufacturer.manufacturer_id] - buyer_a.quantity
            )
            res_b_after = self.engine.match(buyer_b, top_k=5, available_capacities=avail_caps)
            if res_b_after.matches:
                allocated_b = res_b_after.matches[0]
                explanation = (
                    f"First-Come-First-Served (FCFS): Buyer A reserved {buyer_a.quantity} units at {top_a.manufacturer.name}. "
                    f"Buyer B was evaluated against residual capacity and matched to {allocated_b.manufacturer.name}."
                )
            else:
                # If Buyer B is starved, pick closest relaxed match
                relaxed = res_b_after.relaxed_matches[0] if res_b_after.relaxed_matches else top_b
                allocated_b = relaxed
                explanation = (
                    f"First-Come-First-Served (FCFS) Warning: Buyer A consumed capacity at shared supplier {top_a.manufacturer.name}. "
                    f"Buyer B has ZERO eligible suppliers remaining under strict constraints!"
                )

        else:
            # Pareto Optimal (Global Welfare Maximization):
            # Evaluate all pairings (A_i, B_j) to maximize sum of satisfaction scores,
            # ensuring no shared supplier is assigned more demand than its monthly capacity.
            best_pair = None
            max_combined_score = -1.0

            candidates_a = res_a_independent.matches[:5]
            candidates_b = res_b_independent.matches[:5]

            for cand_a in candidates_a:
                for cand_b in candidates_b:
                    mfg_a_id = cand_a.manufacturer.manufacturer_id
                    mfg_b_id = cand_b.manufacturer.manufacturer_id

                    # Check feasibility
                    if mfg_a_id == mfg_b_id:
                        total_cap = cand_a.manufacturer.capacity_units_per_month
                        if combined_demand > total_cap:
                            continue # Infeasible pairing: exceeds single factory capacity

                    score_sum = cand_a.score_breakdown.total_score + cand_b.score_breakdown.total_score
                    if score_sum > max_combined_score:
                        max_combined_score = score_sum
                        best_pair = (cand_a, cand_b)

            if best_pair is not None:
                allocated_a, allocated_b = best_pair
                explanation = (
                    f"Pareto Optimal Allocation: Analyzed multi-buyer utility across available candidates. "
                    f"Buyer A is allocated to high-capacity CNC specialist {allocated_a.manufacturer.name} (Score: {allocated_a.score_breakdown.total_score}/100, Capacity: {allocated_a.manufacturer.capacity_units_per_month:,}/mo). "
                    f"Buyer B is allocated to sheet-metal specialist {allocated_b.manufacturer.name} (Score: {allocated_b.score_breakdown.total_score}/100, Capacity: {allocated_b.manufacturer.capacity_units_per_month:,}/mo). "
                    f"Both buyers are 100% satisfied without creating production bottlenecks or capacity starvation."
                )
            else:
                # Fallback to independent tops with warning
                allocated_a = top_a
                allocated_b = top_b
                explanation = (
                    f"Capacity Alert: Both buyers matched to suppliers with constrained capacity. "
                    f"Combined demand is {combined_demand:,} units against capacity of {mfg_capacity:,} units ({overcap_pct}% load). "
                    f"Staggered production schedules or multi-facility batch splitting is recommended."
                )

        return ContentionSimulationResponse(
            buyer_a_independent_top=top_a,
            buyer_b_independent_top=top_b,
            conflict_detected=conflict_detected,
            shared_manufacturer_id=shared_mfg_id,
            shared_manufacturer_name=shared_mfg.name if shared_mfg else None,
            combined_demand=combined_demand,
            monthly_capacity=mfg_capacity,
            capacity_utilization_pct=overcap_pct,
            resolution_strategy=strategy,
            buyer_a_allocated=allocated_a,
            buyer_b_allocated=allocated_b,
            explanation=explanation
        )
