"""
Core Deterministic Matching and Scoring Engine for Veridia
Implements two-stage filtering, multi-attribute scoring, explainability, and relaxed constraint search.
"""
from typing import List, Dict, Tuple, Optional, Set
from datetime import date, timedelta
import math
import logging

from src.config import (
    DEFAULT_AS_OF_DATE,
    DEFAULT_SCORING_WEIGHTS,
    DELIVERY_RATING_POINTS,
    PROCESS_SYNONYMS,
    MATERIAL_SYNONYMS,
    CERTIFICATION_SYNONYMS,
    OPTIMAL_CAPACITY_RATIO_MIN,
    OPTIMAL_CAPACITY_RATIO_MAX,
    CRITICAL_CAPACITY_RATIO
)
from src.models import (
    CleanedManufacturer,
    BuyerRequirement,
    MatchResult,
    ScoreBreakdown,
    MatchExplanation,
    SearchResponse
)

logger = logging.getLogger(__name__)

class MatchingEngine:
    """Deterministic, auditable matching engine with transparent scoring."""

    def __init__(self, manufacturers: List[CleanedManufacturer]):
        self.manufacturers = manufacturers

    @staticmethod
    def normalize_process(input_process: str) -> List[str]:
        """Maps freeform process text to canonical database process names."""
        clean = input_process.strip().lower()
        if clean in PROCESS_SYNONYMS:
            return PROCESS_SYNONYMS[clean]
        for key, val in PROCESS_SYNONYMS.items():
            if key in clean or clean in key:
                return val
        return [input_process.strip()]

    @staticmethod
    def normalize_material(input_material: str) -> str:
        """Maps freeform material text to canonical database material names."""
        clean = input_material.strip().lower()
        return MATERIAL_SYNONYMS.get(clean, input_material.strip())

    @staticmethod
    def normalize_cert(input_cert: str) -> str:
        """Maps freeform certification text to canonical certification names."""
        clean = input_cert.strip().lower().replace("-", " ")
        return CERTIFICATION_SYNONYMS.get(clean, input_cert.strip())

    def match(
        self,
        req: BuyerRequirement,
        previous_req: Optional[BuyerRequirement] = None,
        top_k: int = 10,
        available_capacities: Optional[Dict[str, int]] = None
    ) -> SearchResponse:
        """
        Executes end-to-end matching:
        1. Normalizes requirement terms
        2. Applies hard gatekeeper filters
        3. Computes multi-attribute utility score
        4. Generates transparent explainability cards
        5. Computes delta if previous_req was modified partway
        """
        as_of = req.as_of_date or DEFAULT_AS_OF_DATE
        target_processes = self.normalize_process(req.process)
        target_material = self.normalize_material(req.material)
        target_certs = [self.normalize_cert(c) for c in req.required_certifications]

        weights = req.custom_weights or DEFAULT_SCORING_WEIGHTS

        eligible_matches: List[MatchResult] = []
        ineligible_candidates: List[Tuple[CleanedManufacturer, List[str]]] = []

        for mfg in self.manufacturers:
            disqualifications: List[str] = []

            # 1. Active Status Check
            if mfg.status != "active":
                disqualifications.append(f"Manufacturer is inactive (status: {mfg.status}).")

            # 2. Process Capability Check
            has_process = any(
                p.lower() in [proc.lower() for proc in mfg.processes] 
                for p in target_processes
            )
            if not has_process:
                disqualifications.append(
                    f"Process mismatch: does not support '{req.process}' (Offers: {', '.join(mfg.processes)})."
                )

            # 3. Material Compatibility Check
            has_material = target_material.lower() in [mat.lower() for mat in mfg.materials]
            if not has_material:
                disqualifications.append(
                    f"Material mismatch: does not handle '{req.material}' (Handles: {', '.join(mfg.materials)})."
                )

            # 4. Order Quantity Feasibility Check
            if req.quantity < mfg.min_order_qty:
                disqualifications.append(
                    f"Quantity below MOQ: order {req.quantity} < factory min {mfg.min_order_qty} units."
                )
            elif req.quantity > mfg.max_order_qty:
                disqualifications.append(
                    f"Quantity exceeds Max Order Qty: order {req.quantity} > factory max {mfg.max_order_qty} units."
                )

            # 5. Lead Time Feasibility Check
            if mfg.lead_time_weeks > req.timeline_weeks:
                disqualifications.append(
                    f"Lead time too slow: factory requires {mfg.lead_time_weeks:.1f} weeks vs required {req.timeline_weeks} weeks."
                )

            # 6. Certification Validity & Expiry Horizon Check
            # Check if all required certs are held
            mfg_certs_clean = [c.upper().replace("-", " ") for c in mfg.certifications]
            for rc in target_certs:
                if rc.upper().replace("-", " ") not in mfg_certs_clean:
                    disqualifications.append(
                        f"Missing required certification: '{rc}' (Has: {', '.join(mfg.certifications) or 'None'})."
                    )

            # Check if certification will remain valid throughout production lead time
            completion_date = as_of + timedelta(days=int(mfg.lead_time_days))
            if target_certs and mfg.certification_expiry < completion_date:
                disqualifications.append(
                    f"Certification expires before delivery: expires {mfg.certification_expiry} vs production completion {completion_date}."
                )

            # Check available capacity if concurrent reservation map is provided
            current_capacity = (
                available_capacities.get(mfg.manufacturer_id, mfg.capacity_units_per_month)
                if available_capacities is not None else mfg.capacity_units_per_month
            )
            if current_capacity < req.quantity:
                disqualifications.append(
                    f"Remaining monthly capacity depleted: {current_capacity} units available < {req.quantity} required."
                )

            if not disqualifications:
                score_bd, explanation = self._score_and_explain(
                    mfg=mfg,
                    req=req,
                    as_of=as_of,
                    weights=weights,
                    current_capacity=current_capacity
                )
                eligible_matches.append(MatchResult(
                    manufacturer=mfg,
                    score_breakdown=score_bd,
                    explanation=explanation,
                    eligible=True,
                    disqualification_reasons=[]
                ))
            else:
                ineligible_candidates.append((mfg, disqualifications))

        # Sort eligible matches by total score descending
        eligible_matches.sort(key=lambda x: x.score_breakdown.total_score, reverse=True)

        relaxed_matches = None
        if len(eligible_matches) == 0:
            logger.info("Zero eligible matches found; computing relaxed constraint matches.")
            relaxed_matches = self._find_relaxed_matches(
                ineligible_candidates=ineligible_candidates,
                req=req,
                as_of=as_of,
                weights=weights
            )

        # Compute query delta notes if buyer changed requirements partway
        delta_notes = self._compute_delta_notes(req, previous_req) if previous_req else None

        return SearchResponse(
            session_id=req.session_id,
            requirement=req,
            as_of_date=as_of,
            total_manufacturers_evaluated=len(self.manufacturers),
            eligible_count=len(eligible_matches),
            matches=eligible_matches[:top_k],
            relaxed_matches=relaxed_matches[:5] if relaxed_matches else None,
            query_delta_notes=delta_notes
        )

    def _score_and_explain(
        self,
        mfg: CleanedManufacturer,
        req: BuyerRequirement,
        as_of: date,
        weights: Dict[str, float],
        current_capacity: int
    ) -> Tuple[ScoreBreakdown, MatchExplanation]:
        """Computes transparent multi-attribute utility score and generates explanation cards."""

        # 1. Speed Score (30% weight)
        lead_weeks = mfg.lead_time_weeks
        timeline_weeks = req.timeline_weeks
        margin_weeks = timeline_weeks - lead_weeks
        # 100 points if margin >= 3 weeks, scaling down to 60 if margin is 0
        if margin_weeks >= 3.0:
            speed_score = 100.0
        elif margin_weeks > 0:
            speed_score = 60.0 + (margin_weeks / 3.0) * 40.0
        elif margin_weeks == 0:
            speed_score = 60.0
        else:
            speed_score = max(0.0, 60.0 - abs(margin_weeks) * 20.0)

        # 2. Delivery Reliability Score (25% weight)
        # 60% weight on on_time_delivery_pct + 40% on delivery rating letter grade
        otd_score = min(100.0, max(0.0, mfg.on_time_delivery_pct))
        rating_score = DELIVERY_RATING_POINTS.get(mfg.delivery_rating, 60.0)
        reliability_score = (otd_score * 0.6) + (rating_score * 0.4)

        # 3. Capacity Fit Score (20% weight)
        # Optimal ratio: order represents between 5% and 35% of monthly capacity
        cap_utilization = (req.quantity / max(1, current_capacity)) * 100.0
        ratio = req.quantity / max(1, current_capacity)

        if OPTIMAL_CAPACITY_RATIO_MIN <= ratio <= OPTIMAL_CAPACITY_RATIO_MAX:
            capacity_score = 100.0
        elif ratio < OPTIMAL_CAPACITY_RATIO_MIN:
            # Order is slightly too small for a giant factory (might be de-prioritized)
            capacity_score = 75.0 + (ratio / OPTIMAL_CAPACITY_RATIO_MIN) * 25.0
        elif ratio <= CRITICAL_CAPACITY_RATIO:
            # Moderate load: 40% to 70%
            over_span = CRITICAL_CAPACITY_RATIO - OPTIMAL_CAPACITY_RATIO_MAX
            capacity_score = 100.0 - ((ratio - OPTIMAL_CAPACITY_RATIO_MAX) / over_span) * 35.0
        else:
            # Dangerous load: > 70%
            capacity_score = max(20.0, 65.0 - ((ratio - CRITICAL_CAPACITY_RATIO) / 0.3) * 45.0)

        # 4. Export Maturity Score (15% weight)
        # Log-scaled: 20+ years = 100, 10 years = ~80, 2 years = ~40
        exp_years = mfg.export_experience_years
        export_score = min(100.0, max(20.0, (math.log(max(1, exp_years) + 1) / math.log(26)) * 100.0))

        # 5. Audit Recency Score (10% weight)
        days_since_audit = (as_of - mfg.last_audit_date).days
        if days_since_audit <= 90:
            audit_score = 100.0
        elif days_since_audit <= 270:
            audit_score = 85.0
        elif days_since_audit <= 450:
            audit_score = 70.0
        else:
            audit_score = 50.0

        # Composite Weighted Total
        total_score = (
            speed_score * weights.get("delivery_speed", 0.30) +
            reliability_score * weights.get("delivery_reliability", 0.25) +
            capacity_score * weights.get("capacity_fit", 0.20) +
            export_score * weights.get("export_maturity", 0.15) +
            audit_score * weights.get("audit_recency", 0.10)
        )
        total_score = round(min(100.0, max(0.0, total_score)), 1)

        score_breakdown = ScoreBreakdown(
            speed_score=round(speed_score, 1),
            reliability_score=round(reliability_score, 1),
            capacity_score=round(capacity_score, 1),
            export_score=round(export_score, 1),
            audit_score=round(audit_score, 1),
            total_score=total_score
        )

        # Synthesize Human-in-the-Loop Explanation
        strengths: List[str] = []
        risks: List[str] = []

        if margin_weeks >= 2.0:
            strengths.append(f"Fast turnaround: {lead_weeks:.1f} weeks lead time leaves a healthy {margin_weeks:.1f}-week buffer before deadline.")
        elif margin_weeks >= 0:
            strengths.append(f"Meets deadline: {lead_weeks:.1f} weeks lead time matches your target timeline.")

        if mfg.delivery_rating == "A" and mfg.on_time_delivery_pct >= 95.0:
            strengths.append(f"Top-tier delivery track record: Grade 'A' rating with {mfg.on_time_delivery_pct:.1f}% on-time completion.")

        if mfg.export_experience_years >= 10:
            strengths.append(f"Experienced international exporter: {mfg.export_experience_years} years shipping to global markets.")

        if OPTIMAL_CAPACITY_RATIO_MIN <= ratio <= OPTIMAL_CAPACITY_RATIO_MAX:
            strengths.append(f"Ideal production volume: Batch of {req.quantity} units utilizes {cap_utilization:.1f}% of monthly capacity (Tier: {mfg.capacity_tier}).")

        # Flag Risks
        if ratio > CRITICAL_CAPACITY_RATIO:
            risks.append(f"High capacity load: Batch utilizes {cap_utilization:.1f}% of factory's available monthly output.")
        if days_since_audit > 400:
            risks.append(f"Audit age: Last audited on {mfg.last_audit_date} ({days_since_audit} days ago).")
        if margin_weeks == 0:
            risks.append("Zero delivery buffer: Any logistics or customs delay between India and destination could breach deadline.")
        if mfg.data_quality_flags:
            risks.append(f"Data note: {', '.join(mfg.data_quality_flags)}")

        cert_status = (
            f"Valid until {mfg.certification_expiry} ({', '.join(mfg.certifications) or 'Uncertified'})"
        )

        summary = (
            f"{mfg.name} in {mfg.city}, {mfg.state_name} scored {total_score}/100. "
            f"Offers {mfg.primary_process} with {lead_weeks:.1f}w lead time and {mfg.export_experience_years}y export track record."
        )

        explanation = MatchExplanation(
            summary=summary,
            key_strengths=strengths,
            risks_and_tradeoffs=risks,
            capacity_utilization_pct=round(cap_utilization, 1),
            lead_time_margin_weeks=round(margin_weeks, 1),
            cert_validity_status=cert_status
        )

        return score_breakdown, explanation

    def _find_relaxed_matches(
        self,
        ineligible_candidates: List[Tuple[CleanedManufacturer, List[str]]],
        req: BuyerRequirement,
        as_of: date,
        weights: Dict[str, float]
    ) -> List[MatchResult]:
        """Provides closest candidates when zero manufacturers meet 100% of hard filters."""
        # Score candidates by fewness of disqualification reasons
        relaxed_results: List[MatchResult] = []
        for mfg, reasons in ineligible_candidates:
            # We compute a score ignoring hard failures to evaluate closeness
            score_bd, explanation = self._score_and_explain(
                mfg=mfg,
                req=req,
                as_of=as_of,
                weights=weights,
                current_capacity=mfg.capacity_units_per_month
            )
            # Penalty per disqualification
            penalized_total = max(10.0, score_bd.total_score - (len(reasons) * 20.0))
            score_bd.total_score = round(penalized_total, 1)

            relaxed_results.append(MatchResult(
                manufacturer=mfg,
                score_breakdown=score_bd,
                explanation=explanation,
                eligible=False,
                disqualification_reasons=reasons
            ))

        relaxed_results.sort(
            key=lambda x: (len(x.disqualification_reasons), -x.score_breakdown.total_score)
        )
        return relaxed_results

    def _compute_delta_notes(
        self,
        current: BuyerRequirement,
        previous: BuyerRequirement
    ) -> List[str]:
        """Highlights the operational impact of mid-flight requirement modifications."""
        notes: List[str] = []
        if current.quantity != previous.quantity:
            diff = current.quantity - previous.quantity
            direction = "increased" if diff > 0 else "decreased"
            notes.append(
                f"Batch quantity was {direction} from {previous.quantity:,} to {current.quantity:,} units ({diff:+,} units). "
                f"This adjusts factory capacity utilization and filters out facilities outside this order range."
            )

        if current.timeline_weeks != previous.timeline_weeks:
            diff = current.timeline_weeks - previous.timeline_weeks
            direction = "lengthened" if diff > 0 else "compressed"
            notes.append(
                f"Required delivery timeline was {direction} from {previous.timeline_weeks}w to {current.timeline_weeks}w ({diff:+d}w). "
                f"Tighter timelines disqualify slower production cycles."
            )

        if set(current.required_certifications) != set(previous.required_certifications):
            added = set(current.required_certifications) - set(previous.required_certifications)
            removed = set(previous.required_certifications) - set(current.required_certifications)
            if added:
                notes.append(f"Added mandatory certifications: {', '.join(added)}.")
            if removed:
                notes.append(f"Removed mandatory certifications: {', '.join(removed)}.")

        if current.material != previous.material:
            notes.append(f"Material changed from '{previous.material}' to '{current.material}'.")

        if current.process != previous.process:
            notes.append(f"Target process changed from '{previous.process}' to '{current.process}'.")

        return notes
