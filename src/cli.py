"""
Command-Line Interface (CLI) for Veridia Matching Engine
Allows instant command-line matching, dirty data inspection, and multi-buyer contention simulation.
"""
import argparse
import sys
import json
from datetime import datetime, date

from src.data_pipeline import get_pipeline
from src.matching_engine import MatchingEngine
from src.allocation_manager import AllocationManager
from src.ai_service import AIService
from src.models import BuyerRequirement
from src.config import DEFAULT_AS_OF_DATE

def print_separator(title: str = ""):
    print("\n" + "=" * 70)
    if title:
        print(f" {title.upper()} ".center(70, "="))
        print("=" * 70)

def handle_match(args, engine: MatchingEngine):
    """Executes matching for a single requirement."""
    certs = [c.strip() for c in args.certs.split(",") if c.strip()] if args.certs else []
    as_of = datetime.strptime(args.as_of_date, "%Y-%m-%d").date() if args.as_of_date else DEFAULT_AS_OF_DATE

    req = BuyerRequirement(
        session_id=args.session_id,
        buyer_name=args.buyer_name,
        material=args.material,
        process=args.process,
        quantity=args.qty,
        timeline_weeks=args.weeks,
        required_certifications=certs,
        as_of_date=as_of,
        destination_country=args.destination
    )

    print_separator(f"Matching Results for {req.buyer_name}")
    print(f"Material: {req.material} | Process: {req.process} | Batch: {req.quantity:,} units")
    print(f"Deadline: {req.timeline_weeks} weeks | Certs: {certs or 'None'} | As-Of Date: {as_of}")

    res = engine.match(req, top_k=args.top_k)
    print(f"\nEvaluated: {res.total_manufacturers_evaluated} factories | Eligible: {res.eligible_count}")

    if res.matches:
        for idx, match in enumerate(res.matches, 1):
            m = match.manufacturer
            sb = match.score_breakdown
            exp = match.explanation
            print(f"\n[{idx}] {m.name} ({m.city}, {m.state_name})")
            print(f"    Manufacturer ID: {m.manufacturer_id} (Raw: {m.raw_id})")
            print(f"    Total Score: {sb.total_score}/100 | Lead Time: {m.lead_time_weeks:.1f}w (Margin: {exp.lead_time_margin_weeks:+.1f}w)")
            print(f"    OTD: {m.on_time_delivery_pct:.1f}% (Grade {m.delivery_rating}) | Export Experience: {m.export_experience_years} years")
            print(f"    Capacity Tier: {m.capacity_tier} ({m.capacity_units_per_month:,}/mo) | Batch Load: {exp.capacity_utilization_pct:.1f}%")
            print(f"    Certifications: {', '.join(m.certifications)} (Expiry: {m.certification_expiry})")
            print(f"    Score Breakdown: Speed={sb.speed_score}, Reliability={sb.reliability_score}, Capacity={sb.capacity_score}, Export={sb.export_score}, Audit={sb.audit_score}")
            if exp.risks_and_tradeoffs:
                print(f"    Risk Watch: {'; '.join(exp.risks_and_tradeoffs)}")

        if args.memo:
            ai = AIService()
            print_separator("Executive Procurement Pitch")
            print(ai.generate_executive_pitch(res.matches[0], req))

    elif res.relaxed_matches:
        print("\n⚠️ ZERO manufacturers passed 100% of strict hard filters.")
        print("Displaying closest available candidates with disqualification reasons:")
        for idx, rm in enumerate(res.relaxed_matches[:3], 1):
            m = rm.manufacturer
            print(f"\n[{idx}] {m.name} ({m.city}, {m.state_name})")
            print(f"    Penalized Score: {rm.score_breakdown.total_score}/100")
            print(f"    Disqualification Reasons:")
            for reason in rm.disqualification_reasons:
                print(f"      ❌ {reason}")

def handle_simulate_conflict(args, engine: MatchingEngine):
    """Executes the prompt's Buyer A vs Buyer B contention scenario."""
    allocator = AllocationManager(engine)

    req_a = BuyerRequirement(
        session_id="session_buyer_a",
        buyer_name="Buyer A",
        material="aluminium",
        process="CNC",
        quantity=1000,
        timeline_weeks=6,
        required_certifications=["ISO 9001"]
    )

    req_b = BuyerRequirement(
        session_id="session_buyer_b",
        buyer_name="Buyer B",
        material="stainless steel",
        process="sheet metal",
        quantity=1500,
        timeline_weeks=6,
        required_certifications=["ISO 9001"]
    )

    print_separator("Simultaneous Buyer Arrival & Contention Simulation")
    print("Buyer A: 1,000 aluminium CNC parts, ISO 9001, within 6 weeks")
    print("Buyer B: 1,500 stainless sheet-metal parts, ISO 9001, within 6 weeks")
    print("Both buyers submit requirements simultaneously.\n")

    sim = allocator.simulate_two_buyers(req_a, req_b, strategy=args.strategy)

    print(f"Resolution Strategy: {sim.resolution_strategy.upper()}")
    print(f"Conflict Status: {'Conflict / Contention Detected' if sim.conflict_detected else 'Clear Separation'}")
    print(f"\nBuyer A Allocated:")
    print(f"  Supplier: {sim.buyer_a_allocated.manufacturer.name} ({sim.buyer_a_allocated.manufacturer.manufacturer_id})")
    print(f"  Score: {sim.buyer_a_allocated.score_breakdown.total_score}/100 | Monthly Cap: {sim.buyer_a_allocated.manufacturer.capacity_units_per_month:,}")
    print(f"  Lead Time: {sim.buyer_a_allocated.manufacturer.lead_time_weeks:.1f}w")

    print(f"\nBuyer B Allocated:")
    print(f"  Supplier: {sim.buyer_b_allocated.manufacturer.name} ({sim.buyer_b_allocated.manufacturer.manufacturer_id})")
    print(f"  Score: {sim.buyer_b_allocated.score_breakdown.total_score}/100 | Monthly Cap: {sim.buyer_b_allocated.manufacturer.capacity_units_per_month:,}")
    print(f"  Lead Time: {sim.buyer_b_allocated.manufacturer.lead_time_weeks:.1f}w")

    print(f"\nOperational Analysis:\n{sim.explanation}")

def handle_inspect_dirty_data(args, pipe):
    """Summarizes dirty data anomalies detected in the raw mock dataset."""
    records = pipe.load_and_sanitize()
    print_separator("Dataset Sanitation & Data Quality Audit")
    print(f"Total Records Ingested: {len(records):,}")

    flagged = [r for r in records if r.data_quality_flags]
    print(f"Records with Data Quality Anomalies Cleaned: {len(flagged)} ({len(flagged)/len(records)*100:.1f}%)")

    # Categories
    duplicates = [r for r in records if any("DUPLICATE_ID" in f for f in r.data_quality_flags)]
    otd_clamped = [r for r in records if any("OTD_CLAMPED" in f for f in r.data_quality_flags)]
    imputed_lead = [r for r in records if any("LEAD_TIME_IMPUTED" in f for f in r.data_quality_flags)]

    print(f"\n1. Duplicate ID Collisions: {len(duplicates)} records")
    for r in duplicates[:6]:
        print(f"   - {r.manufacturer_id}: {r.name} in {r.city} (Raw ID: {r.raw_id})")

    print(f"\n2. Out-of-Bounds On-Time Delivery (> 100%): {len(otd_clamped)} records")
    for r in otd_clamped[:6]:
        print(f"   - {r.manufacturer_id}: {r.name} -> Raw OTD: {r.raw_on_time_delivery_pct:.1f}% clamped to {r.on_time_delivery_pct:.1f}%")

    print(f"\n3. Missing Lead Times (NaN): {len(imputed_lead)} records")
    for r in imputed_lead[:6]:
        print(f"   - {r.manufacturer_id}: {r.name} -> Imputed {r.lead_time_weeks:.1f} weeks based on {r.primary_process} median")

def handle_parse_rfq(args, engine: MatchingEngine):
    """Parses natural language text into a match."""
    ai = AIService()
    print_separator("Natural Language RFQ Parser")
    print(f"Input Text:\n\"{args.text}\"\n")

    req = ai.parse_natural_language_rfq(args.text)
    print("Extracted Structured Requirements:")
    print(json.dumps(req.model_dump(exclude={'as_of_date', 'custom_weights'}), indent=2))

    res = engine.match(req, top_k=3)
    print(f"\nMatches Found: {res.eligible_count}")
    if res.matches:
        top = res.matches[0]
        print(f"Top Recommendation: {top.manufacturer.name} (Score: {top.score_breakdown.total_score}/100)")
        print(ai.generate_executive_pitch(top, req))

def main():
    parser = argparse.ArgumentParser(description="Veridia Precision Manufacturer Matching System CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Match command
    match_parser = subparsers.add_parser("match", help="Match a buyer requirement")
    match_parser.add_argument("--material", required=True, help="Material (e.g. aluminium, stainless steel)")
    match_parser.add_argument("--process", required=True, help="Process (e.g. machined, CNC milling, sheet metal)")
    match_parser.add_argument("--qty", type=int, required=True, help="Batch quantity (units)")
    match_parser.add_argument("--weeks", type=int, required=True, help="Timeline in weeks")
    match_parser.add_argument("--certs", default="", help="Comma-separated certifications (e.g. 'ISO 9001')")
    match_parser.add_argument("--buyer-name", default="Anonymous Buyer", help="Buyer or company name")
    match_parser.add_argument("--session-id", default="cli-session", help="Session ID for state isolation")
    match_parser.add_argument("--as-of-date", default=None, help="Temporal evaluation anchor (YYYY-MM-DD)")
    match_parser.add_argument("--destination", default="Germany", help="Destination country")
    match_parser.add_argument("--top-k", type=int, default=5, help="Number of results to display")
    match_parser.add_argument("--memo", action="store_true", help="Generate executive procurement memo")

    # Contention simulation command
    conflict_parser = subparsers.add_parser("simulate-conflict", help="Simulate simultaneous Buyer A & B contention")
    conflict_parser.add_argument("--strategy", choices=["pareto_optimal", "fcfs"], default="pareto_optimal")

    # Inspect dirty data command
    subparsers.add_parser("inspect-dirty-data", help="Audit dirty data sanitation & anomalies")

    # Natural language RFQ command
    rfq_parser = subparsers.add_parser("parse-rfq", help="Parse freeform RFQ text using AI")
    rfq_parser.add_argument("text", help="Unstructured RFQ message or email text")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    pipe = get_pipeline()
    records = pipe.load_and_sanitize()
    engine = MatchingEngine(records)

    if args.command == "match":
        handle_match(args, engine)
    elif args.command == "simulate-conflict":
        handle_simulate_conflict(args, engine)
    elif args.command == "inspect-dirty-data":
        handle_inspect_dirty_data(args, pipe)
    elif args.command == "parse-rfq":
        handle_parse_rfq(args, engine)

if __name__ == "__main__":
    main()
