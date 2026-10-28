"""
Pydantic Schemas and Domain Models for Veridia Matching System
"""
from typing import List, Dict, Optional, Any
from datetime import date
from pydantic import BaseModel, Field, field_validator, ConfigDict

class BuyerRequirement(BaseModel):
    """Structured requirement specification submitted by a buyer."""
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(default="session-default", description="Unique session identifier for state isolation")
    buyer_name: str = Field(default="Buyer", description="Company or buyer identifier")
    material: str = Field(..., description="Target material (e.g. aluminium, stainless steel, brass)")
    process: str = Field(..., description="Target manufacturing process or keyword (e.g. CNC milling, machined)")
    quantity: int = Field(..., gt=0, description="Batch order quantity (units)")
    timeline_weeks: int = Field(..., gt=0, description="Delivery deadline window in weeks")
    required_certifications: List[str] = Field(default_factory=list, description="Mandatory certifications (e.g. ISO 9001)")
    as_of_date: Optional[date] = Field(default=None, description="Evaluation date anchor for deterministic validity")
    destination_country: str = Field(default="Germany", description="Destination country for logistics scoring")
    custom_weights: Optional[Dict[str, float]] = Field(default=None, description="Optional custom scoring weights")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Order quantity must be strictly greater than 0.")
        return v

    @field_validator("timeline_weeks")
    @classmethod
    def validate_timeline(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Timeline weeks must be strictly greater than 0.")
        return v


class CleanedManufacturer(BaseModel):
    """Standardized, validated, and enriched manufacturer record."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    manufacturer_id: str = Field(..., description="Unique surrogate ID (resolves CSV collisions)")
    raw_id: str = Field(..., description="Original manufacturer_id from source CSV")
    name: str
    country: str = "India"
    city: str
    state: str
    state_name: str
    full_address: str
    contact_email: str
    website: str
    founded_year: int
    employee_count: int
    company_size: str
    capacity_units_per_month: int
    capacity_tier: str
    processes: List[str]
    primary_process: str
    process_count: int
    materials: List[str]
    certifications: List[str]
    certification_count: int
    certification_expiry: date
    last_audit_date: date
    min_order_qty: int
    max_order_qty: int
    order_range: str
    lead_time_weeks: float
    lead_time_days: float
    export_experience_years: int
    on_time_delivery_pct: float
    raw_on_time_delivery_pct: float
    delivery_rating: str
    status: str
    data_quality_flags: List[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    """Transparent multi-attribute utility score components (0 - 100 scale)."""
    speed_score: float = Field(..., description="Delivery margin vs deadline score (30%)")
    reliability_score: float = Field(..., description="Historical OTD and delivery rating score (25%)")
    capacity_score: float = Field(..., description="Order batch fit vs monthly capacity (20%)")
    export_score: float = Field(..., description="International export maturity score (15%)")
    audit_score: float = Field(..., description="Audit recency score (10%)")
    total_score: float = Field(..., description="Composite weighted match score (0 - 100)")


class MatchExplanation(BaseModel):
    """Human-readable explanation of why a manufacturer was chosen or penalized."""
    summary: str
    key_strengths: List[str]
    risks_and_tradeoffs: List[str]
    capacity_utilization_pct: float
    lead_time_margin_weeks: float
    cert_validity_status: str


class MatchResult(BaseModel):
    """Enriched match recommendation card."""
    manufacturer: CleanedManufacturer
    score_breakdown: ScoreBreakdown
    explanation: MatchExplanation
    eligible: bool = True
    disqualification_reasons: List[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Top-level response payload for buyer requirement matching."""
    session_id: str
    requirement: BuyerRequirement
    as_of_date: date
    total_manufacturers_evaluated: int
    eligible_count: int
    matches: List[MatchResult]
    relaxed_matches: Optional[List[MatchResult]] = Field(
        default=None, 
        description="Closest matches when zero or few candidates pass strict filters"
    )
    query_delta_notes: Optional[List[str]] = Field(
        default=None,
        description="Notes highlighting the impact of in-flight requirement changes"
    )


class ContentionSimulationRequest(BaseModel):
    """Request for running the simultaneous Buyer A vs Buyer B contention scenario."""
    buyer_a: BuyerRequirement
    buyer_b: BuyerRequirement
    resolution_strategy: str = Field(
        default="pareto_optimal", 
        description="Strategy: 'pareto_optimal', 'fcfs' (first-come first-served), or 'capacity_split'"
    )


class ContentionSimulationResponse(BaseModel):
    """Detailed resolution breakdown of simultaneous buyer capacity contention."""
    buyer_a_independent_top: MatchResult
    buyer_b_independent_top: MatchResult
    conflict_detected: bool
    shared_manufacturer_id: Optional[str] = None
    shared_manufacturer_name: Optional[str] = None
    combined_demand: int
    monthly_capacity: int
    capacity_utilization_pct: float
    resolution_strategy: str
    buyer_a_allocated: MatchResult
    buyer_b_allocated: MatchResult
    explanation: str
