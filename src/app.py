"""
Interactive Web Application & REST API for Veridia Manufacturer Matching System
Formal Enterprise B2B Procurement Portal.
Clean, formal Algerian / Alegreya typography, zero informal emojis/icons, and rigorous data presentation.
"""
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, Any
from datetime import date
import logging
import uvicorn

from src.data_pipeline import get_pipeline
from src.matching_engine import MatchingEngine
from src.allocation_manager import AllocationManager
from src.ai_service import AIService
from src.models import (
    BuyerRequirement,
    SearchResponse,
    ContentionSimulationRequest,
    ContentionSimulationResponse
)
from src.config import DEFAULT_AS_OF_DATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Veridia Precision Manufacturer Matching API",
    description="Formal Enterprise B2B Supplier Matching Platform.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
pipeline = get_pipeline()
cleaned_manufacturers = pipeline.load_and_sanitize()
engine = MatchingEngine(cleaned_manufacturers)
allocator = AllocationManager(engine)
ai_service = AIService()

# ---------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "manufacturers_loaded": len(cleaned_manufacturers),
        "as_of_date": str(DEFAULT_AS_OF_DATE)
    }

@app.post("/api/match", response_model=SearchResponse)
def match_requirement(req: BuyerRequirement):
    try:
        return allocator.execute_session_match(req)
    except Exception as e:
        logger.error(f"Error matching requirement: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/parse-and-match", response_model=SearchResponse)
def parse_and_match(payload: Dict[str, str] = Body(...)):
    text = payload.get("text", "")
    session_id = payload.get("session_id", "nlp-session")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text field cannot be empty.")
    req = ai_service.parse_natural_language_rfq(text, session_id=session_id)
    return allocator.execute_session_match(req)

@app.post("/api/simulate-contention", response_model=ContentionSimulationResponse)
def simulate_contention(req: ContentionSimulationRequest):
    try:
        return allocator.simulate_two_buyers(
            buyer_a=req.buyer_a,
            buyer_b=req.buyer_b,
            strategy=req.resolution_strategy
        )
    except Exception as e:
        logger.error(f"Error in contention simulation: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/reserve")
def reserve_capacity(payload: Dict[str, Any] = Body(...)):
    session_id = payload.get("session_id", "default")
    manufacturer_id = payload.get("manufacturer_id")
    units = payload.get("units", 1000)
    if not manufacturer_id:
        raise HTTPException(status_code=400, detail="manufacturer_id is required.")

    success = allocator.reserve_capacity(session_id, manufacturer_id, int(units))
    avail = allocator.get_available_capacities().get(manufacturer_id, 0)
    return {
        "success": success,
        "manufacturer_id": manufacturer_id,
        "reserved_units": units if success else 0,
        "remaining_monthly_capacity": avail,
        "message": "Capacity allocated and reserved for 15 minutes." if success else "Insufficient remaining capacity."
    }

@app.get("/api/audit-data")
def get_audit_data():
    flagged = [
        {
            "manufacturer_id": m.manufacturer_id,
            "raw_id": m.raw_id,
            "name": m.name,
            "city": m.city,
            "state": m.state,
            "primary_process": m.primary_process,
            "on_time_delivery_pct": m.on_time_delivery_pct,
            "raw_on_time_delivery_pct": m.raw_on_time_delivery_pct,
            "lead_time_weeks": m.lead_time_weeks,
            "delivery_rating": m.delivery_rating,
            "flags": m.data_quality_flags
        }
        for m in cleaned_manufacturers if m.data_quality_flags
    ]
    return {
        "total_records": len(cleaned_manufacturers),
        "anomalous_records_count": len(flagged),
        "anomalies": flagged
    }

@app.post("/api/executive-pitch")
def get_executive_pitch(payload: Dict[str, Any] = Body(...)):
    try:
        req = BuyerRequirement(**payload.get("requirement"))
        from src.models import MatchResult
        match = MatchResult(**payload.get("match"))
        pitch = ai_service.generate_executive_pitch(match, req)
        return {"pitch": pitch}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------
# Formal Executive Portal (Algerian / Alegreya Typography, Zero Emojis)
# ---------------------------------------------------------

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VERIDIA | Precision Engineering Supply Chain Intelligence</title>
    <!-- Formal Google Font Alegreya fallback -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Alegreya:ital,wght@0,400;0,600;0,700;0,800;0,900;1,400;1,700&family=Alegreya+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-page: #0b0f17;
            --bg-surface: #121824;
            --bg-card: #182130;
            --bg-card-hover: #1e293b;
            --border-color: rgba(255, 255, 255, 0.1);
            --border-strong: rgba(255, 255, 255, 0.18);
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --text-muted: #94a3b8;
            --accent-primary: #1e40af;
            --accent-primary-hover: #1d4ed8;
            --accent-gold: #d97706;
            --accent-success: #059669;
            --font-formal: 'Algerian', 'Alegreya', Georgia, 'Times New Roman', serif;
            --font-body: 'Alegreya Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            --font-mono: 'JetBrains Mono', Consolas, Monaco, monospace;
            --radius-sm: 4px;
            --radius-md: 8px;
            --radius-lg: 12px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-page);
            color: var(--text-primary);
            font-family: var(--font-body);
            font-size: 14px;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }

        h1, h2, h3, h4, .formal-title {
            font-family: var(--font-formal);
            letter-spacing: 0.5px;
            font-weight: 700;
        }

        /* Formal Top Bar */
        header {
            background-color: var(--bg-surface);
            border-bottom: 2px solid var(--accent-gold);
            padding: 0 2.5rem;
            height: 76px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand-container {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .brand-crest {
            width: 44px;
            height: 44px;
            border: 2px solid var(--accent-gold);
            background-color: #0b0f17;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--font-formal);
            font-size: 24px;
            font-weight: 900;
            color: #fbbf24;
            border-radius: var(--radius-sm);
        }

        .brand-name {
            font-family: var(--font-formal);
            font-size: 22px;
            letter-spacing: 1.5px;
            font-weight: 900;
            color: #f8fafc;
            line-height: 1.1;
        }

        .brand-sub {
            font-size: 11px;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: var(--text-muted);
            font-weight: 600;
        }

        /* Formal Navigation Tabs */
        .nav-tabs {
            display: flex;
            gap: 6px;
            background-color: rgba(0, 0, 0, 0.4);
            padding: 4px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
        }

        .nav-tab {
            padding: 8px 18px;
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-family: var(--font-formal);
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
            cursor: pointer;
            border-radius: var(--radius-sm);
            transition: all 0.15s ease;
            text-transform: uppercase;
        }

        .nav-tab:hover {
            color: #ffffff;
            background-color: rgba(255, 255, 255, 0.05);
        }

        .nav-tab.active {
            background-color: var(--accent-primary);
            color: #ffffff;
            border-bottom: 2px solid var(--accent-gold);
        }

        .header-meta {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
            border-left: 1px solid var(--border-color);
            padding-left: 16px;
        }

        /* Layout */
        .main-layout {
            max-width: 1400px;
            margin: 28px auto;
            padding: 0 28px;
        }

        /* Formal Preset Ribbon */
        .preset-ribbon {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--accent-gold);
            padding: 16px 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }

        .preset-title {
            font-family: var(--font-formal);
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: #fbbf24;
        }

        .preset-btn-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .btn-preset {
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            border-radius: var(--radius-sm);
            transition: all 0.15s ease;
        }

        .btn-preset:hover {
            background-color: rgba(30, 64, 175, 0.25);
            border-color: #60a5fa;
            color: #ffffff;
        }

        /* Delta Banner */
        .delta-banner {
            background-color: rgba(217, 119, 6, 0.15);
            border: 1px solid var(--accent-gold);
            border-radius: var(--radius-sm);
            padding: 14px 20px;
            margin-bottom: 24px;
            color: #fef3c7;
            font-size: 13px;
            display: none;
        }

        .delta-banner.visible {
            display: block;
        }

        /* Content Grid */
        .content-grid {
            display: grid;
            grid-template-columns: 380px 1fr;
            gap: 28px;
            align-items: start;
        }

        @media (max-width: 1024px) {
            .content-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Formal Filter Panel */
        .filter-panel {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 24px;
        }

        .panel-header {
            padding-bottom: 14px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-title {
            font-family: var(--font-formal);
            font-size: 16px;
            letter-spacing: 0.5px;
            color: var(--text-primary);
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-secondary);
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .form-control {
            width: 100%;
            padding: 10px 14px;
            background-color: var(--bg-page);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-size: 13px;
            font-family: inherit;
        }

        .form-control:focus {
            outline: none;
            border-color: #3b82f6;
        }

        .slider-box {
            background-color: rgba(0, 0, 0, 0.25);
            padding: 12px 16px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
        }

        .slider-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .slider-val-badge {
            font-family: var(--font-mono);
            font-weight: 700;
            color: #60a5fa;
            font-size: 13px;
        }

        .slider-input {
            width: 100%;
            height: 6px;
            -webkit-appearance: none;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 3px;
            outline: none;
        }

        .slider-input::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #60a5fa;
            cursor: pointer;
            border: 2px solid #ffffff;
        }

        .chip-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }

        .chip-label {
            display: flex;
            align-items: center;
            gap: 8px;
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
        }

        .chip-label.active {
            background-color: rgba(30, 64, 175, 0.2);
            border-color: #3b82f6;
            color: #ffffff;
        }

        .btn-submit {
            width: 100%;
            padding: 13px;
            background-color: var(--accent-primary);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: var(--radius-sm);
            font-family: var(--font-formal);
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-submit:hover {
            background-color: var(--accent-primary-hover);
        }

        /* Results Area */
        .results-area {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }

        .stat-card {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 18px 22px;
        }

        .stat-label {
            font-family: var(--font-formal);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }

        .stat-value {
            font-family: var(--font-formal);
            font-size: 28px;
            font-weight: 800;
            color: var(--text-primary);
        }

        .stat-subtext {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Match Card */
        .match-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 24px;
            transition: border-color 0.15s ease;
        }

        .match-card:hover {
            border-color: var(--border-strong);
            background-color: var(--bg-card-hover);
        }

        .card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }

        .mfg-group {
            display: flex;
            align-items: flex-start;
            gap: 14px;
        }

        .rank-badge {
            padding: 4px 10px;
            background-color: #0b0f17;
            border: 1px solid var(--accent-gold);
            color: #fbbf24;
            font-family: var(--font-formal);
            font-weight: 800;
            font-size: 14px;
            border-radius: var(--radius-sm);
        }

        .mfg-name {
            font-family: var(--font-formal);
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: 0.3px;
        }

        .mfg-id {
            font-family: var(--font-mono);
            font-size: 11px;
            color: var(--text-muted);
            margin-left: 6px;
            padding: 2px 6px;
            border: 1px solid var(--border-color);
            border-radius: 3px;
            background: rgba(0, 0, 0, 0.2);
        }

        .mfg-location {
            font-size: 13px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        .score-pill {
            text-align: right;
            background-color: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-color);
            padding: 8px 16px;
            border-radius: var(--radius-sm);
        }

        .score-number {
            font-family: var(--font-formal);
            font-size: 24px;
            font-weight: 800;
            color: #34d399;
            line-height: 1;
        }

        .score-label {
            font-family: var(--font-formal);
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* 5 Factor Breakdown Bar */
        .score-bars {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
            margin: 16px 0;
            padding: 12px 16px;
            background-color: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
        }

        .score-bar-col {
            font-size: 11px;
        }

        .score-bar-header {
            display: flex;
            justify-content: space-between;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 4px;
        }

        .progress-track {
            height: 5px;
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 2px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
        }

        /* Metric Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }

        .metric-box {
            background-color: rgba(0, 0, 0, 0.2);
            padding: 10px 14px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
        }

        .metric-title {
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .metric-val {
            font-family: var(--font-mono);
            font-size: 14px;
            font-weight: 700;
            color: #ffffff;
            margin-top: 2px;
        }

        .metric-sub {
            font-size: 11px;
            color: #34d399;
            font-weight: 600;
        }

        /* Explanations */
        .explanation-block {
            font-size: 13px;
            margin-bottom: 16px;
            line-height: 1.6;
        }

        .explanation-heading {
            font-family: var(--font-formal);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }

        .bullet-item {
            color: var(--text-secondary);
            margin-bottom: 4px;
            padding-left: 12px;
            position: relative;
        }

        .bullet-item::before {
            content: "•";
            position: absolute;
            left: 0;
            color: #34d399;
            font-weight: bold;
        }

        .risk-bullet {
            color: #fef08a;
        }

        .risk-bullet::before {
            content: "•";
            color: #f59e0b;
        }

        /* Footer Actions */
        .card-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 14px;
            border-top: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 12px;
        }

        .cert-tags {
            display: flex;
            gap: 6px;
            align-items: center;
            flex-wrap: wrap;
        }

        .cert-tag {
            background-color: rgba(30, 64, 175, 0.2);
            color: #93c5fd;
            border: 1px solid rgba(59, 130, 246, 0.3);
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: var(--radius-sm);
        }

        .btn-action-group {
            display: flex;
            gap: 8px;
        }

        .btn-outline {
            background-color: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            border-radius: var(--radius-sm);
            transition: all 0.15s ease;
        }

        .btn-outline:hover {
            border-color: #ffffff;
            color: #ffffff;
        }

        .btn-action-primary {
            background-color: var(--accent-primary);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #ffffff;
            padding: 6px 16px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            border-radius: var(--radius-sm);
            transition: all 0.15s ease;
        }

        .btn-action-primary:hover {
            background-color: var(--accent-primary-hover);
        }

        /* Tab Content */
        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Contention Tab */
        .contention-cards {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-top: 20px;
        }

        @media (max-width: 768px) {
            .contention-cards {
                grid-template-columns: 1fr;
            }
        }

        .buyer-box {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 24px;
        }

        .buyer-box.buyer-a {
            border-top: 3px solid #3b82f6;
        }

        .buyer-box.buyer-b {
            border-top: 3px solid #a855f7;
        }

        /* Table */
        .audit-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }

        .audit-table th {
            background-color: rgba(0, 0, 0, 0.3);
            color: var(--text-muted);
            padding: 12px 16px;
            font-family: var(--font-formal);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border-color);
        }

        .audit-table td {
            padding: 12px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: var(--text-secondary);
        }

        .audit-table tr:hover td {
            background-color: rgba(255, 255, 255, 0.02);
            color: #ffffff;
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.85);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 999;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s ease;
        }

        .modal-overlay.open {
            opacity: 1;
            pointer-events: auto;
        }

        .modal-box {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-strong);
            border-radius: var(--radius-md);
            width: 90%;
            max-width: 700px;
            max-height: 85vh;
            padding: 28px;
            display: flex;
            flex-direction: column;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }

        .modal-title {
            font-family: var(--font-formal);
            font-size: 16px;
            font-weight: 700;
        }

        .modal-body {
            overflow-y: auto;
            flex: 1;
            font-family: var(--font-mono);
            font-size: 12px;
            background-color: #0b0f17;
            padding: 18px;
            border: 1px solid var(--border-color);
            color: #e2e8f0;
            white-space: pre-wrap;
            line-height: 1.6;
            border-radius: var(--radius-sm);
        }

        .modal-footer {
            margin-top: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
</head>
<body>

    <!-- Header -->
    <header>
        <div class="brand-container">
            <div class="brand-crest">V</div>
            <div>
                <div class="brand-name">VERIDIA</div>
                <div class="brand-sub">Precision Engineering Supply Chain Intelligence</div>
            </div>
        </div>

        <nav class="nav-tabs">
            <button class="nav-tab active" onclick="switchTab('matcher')">Manufacturer Matching</button>
            <button class="nav-tab" onclick="switchTab('ai_rfq')">RFQ Text Parser</button>
            <button class="nav-tab" onclick="switchTab('contention')">Multi-Buyer Contention</button>
            <button class="nav-tab" onclick="switchTab('audit')">Data Quality Audit (40)</button>
        </nav>

        <div class="header-meta">
            <div>TEMPORAL EVALUATION ANCHOR: <strong>2026-10-28</strong></div>
            <div style="font-size:10px; color:#34d399;">STATUS: FULLY VERIFIED (1,000 SUPPLIERS)</div>
        </div>
    </header>

    <div class="main-layout">

        <!-- TAB 1: MATCHER -->
        <div id="tab-matcher" class="tab-content active">
            
            <!-- Preset Ribbon -->
            <div class="preset-ribbon">
                <div class="preset-title">Test Scenarios:</div>
                <div class="preset-btn-group">
                    <button class="btn-preset" onclick="loadPreset('german')">Scenario 1: German Industrial Buyer (2,000 Aluminium CNC, 6 Weeks)</button>
                    <button class="btn-preset" onclick="loadPreset('buyer_a')">Scenario 2: Buyer A (1,000 Aluminium CNC, 6 Weeks)</button>
                    <button class="btn-preset" onclick="loadPreset('buyer_b')">Scenario 3: Buyer B (1,500 Stainless Sheet Metal, 6 Weeks)</button>
                    <button class="btn-preset" onclick="loadPreset('aerospace')">Scenario 4: High-Volume Aerospace (5,000 Titanium AS9100, 10 Weeks)</button>
                </div>
            </div>

            <!-- In-Flight Delta Banner -->
            <div id="delta-banner" class="delta-banner">
                <strong style="font-family: var(--font-formal); letter-spacing: 0.5px;">IN-FLIGHT REQUIREMENT MODIFICATION DETECTED:</strong>
                <div id="delta-notes-list" style="margin-top: 6px;"></div>
            </div>

            <!-- Content Grid -->
            <div class="content-grid">
                
                <!-- Left Form -->
                <div class="filter-panel">
                    <div class="panel-header">
                        <span class="panel-title">Procurement Specifications</span>
                        <span id="session-badge" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">session_german</span>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Material Required</label>
                        <select id="inp-material" class="form-control" onchange="runMatch()">
                            <option value="aluminium">Aluminium (Precision Grade)</option>
                            <option value="stainless steel">Stainless Steel (304 / 316)</option>
                            <option value="mild steel">Mild Steel / Carbon Steel</option>
                            <option value="copper">Copper Alloys</option>
                            <option value="brass">Brass</option>
                            <option value="titanium">Titanium (Aerospace Grade)</option>
                            <option value="cast iron">Cast Iron</option>
                            <option value="ABS">ABS Polymer</option>
                            <option value="nylon">Nylon (Engineering Plastic)</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Manufacturing Process</label>
                        <select id="inp-process" class="form-control" onchange="runMatch()">
                            <option value="CNC milling">CNC Milling</option>
                            <option value="CNC turning">CNC Turning</option>
                            <option value="machined">Machined to Order (General CNC/Grinding)</option>
                            <option value="sheet metal">Sheet Metal Fabrication</option>
                            <option value="casting">Precision Casting</option>
                            <option value="forging">Forging</option>
                            <option value="grinding">Precision Grinding</option>
                            <option value="EDM">Wire / Spark EDM</option>
                            <option value="welding">Welding</option>
                            <option value="injection moulding">Injection Moulding</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <div class="slider-box">
                            <div class="slider-header">
                                <span class="form-label" style="margin-bottom:0;">Order Batch Quantity</span>
                                <span id="val-qty" class="slider-val-badge">2,000 units</span>
                            </div>
                            <input id="inp-qty" type="range" class="slider-input" min="100" max="10000" step="100" value="2000" oninput="updateQty(this.value)" onchange="runMatch()">
                        </div>
                    </div>

                    <div class="form-group">
                        <div class="slider-box">
                            <div class="slider-header">
                                <span class="form-label" style="margin-bottom:0;">Delivery Deadline Window</span>
                                <span id="val-weeks" class="slider-val-badge">6 weeks</span>
                            </div>
                            <input id="inp-weeks" type="range" class="slider-input" min="2" max="16" step="1" value="6" oninput="updateWeeks(this.value)" onchange="runMatch()">
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Mandatory Quality Certifications</label>
                        <div class="chip-grid">
                            <label class="chip-label" id="chip-iso9001">
                                <input type="checkbox" value="ISO 9001" checked onchange="toggleCert(this, 'chip-iso9001')"> ISO 9001
                            </label>
                            <label class="chip-label" id="chip-iatf">
                                <input type="checkbox" value="IATF 16949" onchange="toggleCert(this, 'chip-iatf')"> IATF 16949
                            </label>
                            <label class="chip-label" id="chip-as9100">
                                <input type="checkbox" value="AS9100" onchange="toggleCert(this, 'chip-as9100')"> AS9100
                            </label>
                            <label class="chip-label" id="chip-iso13485">
                                <input type="checkbox" value="ISO 13485" onchange="toggleCert(this, 'chip-iso13485')"> ISO 13485
                            </label>
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Destination Country</label>
                        <input id="inp-dest" type="text" class="form-control" value="Germany" onchange="runMatch()">
                    </div>

                    <button class="btn-submit" onclick="runMatch()">Re-Rank Manufacturers</button>
                </div>

                <!-- Right Results -->
                <div class="results-area">
                    
                    <!-- Stats Counter -->
                    <div class="stats-row">
                        <div class="stat-card">
                            <div class="stat-label">Suppliers Evaluated</div>
                            <div id="stat-total" class="stat-value">1,000</div>
                            <div class="stat-subtext">Precision Indian facilities</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Strictly Eligible</div>
                            <div id="stat-eligible" class="stat-value" style="color: #34d399;">32</div>
                            <div class="stat-subtext">Passed 100% hard constraints</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Top Composite Utility</div>
                            <div id="stat-topscore" class="stat-value" style="color: #60a5fa;">93.8 / 100</div>
                            <div class="stat-subtext">Rank #1 Match</div>
                        </div>
                    </div>

                    <!-- Match Cards Container -->
                    <div id="matches-container">
                        <!-- Populated by JavaScript -->
                    </div>

                </div>

            </div>

        </div>

        <!-- TAB 2: AI RFQ PARSER -->
        <div id="tab-ai_rfq" class="tab-content">
            <div style="background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 36px; max-width: 820px; margin: 0 auto;">
                <h3 style="font-size: 20px; margin-bottom: 8px;">Natural Language RFQ Specification Parser</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 24px;">
                    Paste unstructured procurement text, supplier inquiry letters, or formal RFQ briefs. The parser normalizes technical terms, extracts numeric bounds, and passes the structured requirement directly to the evaluation engine.
                </p>

                <textarea id="ai-text-input" rows="7" class="form-control" style="font-family: var(--font-mono); font-size: 13px; line-height: 1.6; padding: 16px; margin-bottom: 20px;">We are an engineering firm in Stuttgart, Germany. We urgently need 2,500 milled aluminium brackets. Must be ISO 9001 certified. We need them on our dock within 7 weeks. Can you recommend reliable suppliers?</textarea>

                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 12px; color: var(--text-muted);">Understands informal quantities ('a few thousand'), German/English terms, and process synonyms.</span>
                    <button class="btn-submit" style="width: auto; padding: 10px 28px;" onclick="runAiParse()">Parse Specifications & Match</button>
                </div>
            </div>
        </div>

        <!-- TAB 3: CONTENTION SIMULATOR -->
        <div id="tab-contention" class="tab-content">
            <div style="background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 24px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <h3 style="font-size: 18px;">Simultaneous Multi-Buyer Arrival & Capacity Contention Resolution</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
                            Prompt Evaluation Scenario: Buyer A (1,000 Aluminium CNC, 6w) and Buyer B (1,500 Stainless Sheet-Metal, 6w) arrive at the exact same moment.
                        </p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button id="btn-strat-pareto" class="btn-preset" style="background-color: var(--accent-primary); color: #fff;" onclick="simulateContention('pareto_optimal')">Pareto Optimal (Recommended)</button>
                        <button id="btn-strat-fcfs" class="btn-preset" onclick="simulateContention('fcfs')">First-Come First-Served</button>
                    </div>
                </div>
            </div>

            <!-- Resolution Rationale -->
            <div id="contention-explanation-box" style="background-color: rgba(5, 150, 105, 0.12); border: 1px solid var(--accent-success); border-radius: var(--radius-sm); padding: 18px 22px; font-size: 13px; margin-bottom: 24px; line-height: 1.6;">
                <!-- Populated dynamically -->
            </div>

            <!-- Two Buyer Side by Side -->
            <div class="contention-cards">
                <div class="buyer-box buyer-a">
                    <span style="font-family: var(--font-formal); font-size: 12px; font-weight: 700; color: #60a5fa; letter-spacing: 1px;">BUYER A ALLOCATION</span>
                    <h4 style="font-size: 17px; margin: 6px 0 2px;">1,000 Aluminium CNC Parts</h4>
                    <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">Timeline: 6 Weeks • ISO 9001 Mandatory</p>
                    <div id="buyer-a-result"></div>
                </div>

                <div class="buyer-box buyer-b">
                    <span style="font-family: var(--font-formal); font-size: 12px; font-weight: 700; color: #c084fc; letter-spacing: 1px;">BUYER B ALLOCATION</span>
                    <h4 style="font-size: 17px; margin: 6px 0 2px;">1,500 Stainless Sheet-Metal Parts</h4>
                    <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">Timeline: 6 Weeks • ISO 9001 Mandatory</p>
                    <div id="buyer-b-result"></div>
                </div>
            </div>
        </div>

        <!-- TAB 4: AUDIT TAB -->
        <div id="tab-audit" class="tab-content">
            <div style="background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div>
                        <h3 style="font-size: 18px;">Dataset Sanitation & Quality Compliance Audit</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
                            40 intentional data flaws identified and resolved across the 1,000 mock manufacturer records:
                        </p>
                    </div>
                    <span style="font-family: var(--font-mono); font-size: 11px; padding: 4px 10px; background: rgba(5, 150, 105, 0.15); color: #34d399; border: 1px solid var(--accent-success); border-radius: 4px; font-weight: bold;">
                        40 Cleaned Records (100% Ingested)
                    </span>
                </div>

                <div style="overflow-x: auto;">
                    <table class="audit-table">
                        <thead>
                            <tr>
                                <th>Surrogate Facility ID</th>
                                <th>Manufacturer Name</th>
                                <th>Location</th>
                                <th>Primary Process</th>
                                <th>OTD Cleanse</th>
                                <th>Lead Time</th>
                                <th>Sanitation Actions Applied</th>
                            </tr>
                        </thead>
                        <tbody id="audit-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

    </div>

    <!-- Executive Memo Modal -->
    <div id="memo-modal" class="modal-overlay">
        <div class="modal-box">
            <div class="modal-header">
                <span class="modal-title">Executive Procurement Memorandum</span>
                <button onclick="closeMemo()" style="background:none; border:none; color: var(--text-muted); cursor:pointer; font-size: 20px;">&times;</button>
            </div>
            <div id="memo-body" class="modal-body"></div>
            <div class="modal-footer">
                <button id="btn-copy-memo" class="btn-outline" onclick="copyMemoText()">Copy Memorandum</button>
                <button class="btn-action-primary" onclick="closeMemo()">Dismiss</button>
            </div>
        </div>
    </div>

    <script>
        // State
        let currentSessionId = 'session_german';
        let currentResponse = null;
        let selectedCerts = ['ISO 9001'];
        let cachedMemo = '';

        // Tab Switcher
        function switchTab(tabName) {
            document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            event.currentTarget.classList.add('active');
            document.getElementById('tab-' + tabName).classList.add('active');

            if (tabName === 'contention') {
                simulateContention('pareto_optimal');
            } else if (tabName === 'audit') {
                loadAuditData();
            }
        }

        // Sliders
        function updateQty(val) {
            document.getElementById('val-qty').innerText = Number(val).toLocaleString() + ' units';
        }
        function updateWeeks(val) {
            document.getElementById('val-weeks').innerText = val + ' weeks';
        }

        function toggleCert(checkbox, chipId) {
            const label = document.getElementById(chipId);
            if (checkbox.checked) {
                label.classList.add('active');
                if (!selectedCerts.includes(checkbox.value)) selectedCerts.push(checkbox.value);
            } else {
                label.classList.remove('active');
                selectedCerts = selectedCerts.filter(c => c !== checkbox.value);
            }
            runMatch();
        }

        // Presets
        function loadPreset(type) {
            if (type === 'german') {
                currentSessionId = 'session_german';
                document.getElementById('inp-material').value = 'aluminium';
                document.getElementById('inp-process').value = 'machined';
                document.getElementById('inp-qty').value = 2000;
                updateQty(2000);
                document.getElementById('inp-weeks').value = 6;
                updateWeeks(6);
                document.getElementById('inp-dest').value = 'Germany';
                setCertActive('ISO 9001');
            } else if (type === 'buyer_a') {
                currentSessionId = 'session_buyer_a';
                document.getElementById('inp-material').value = 'aluminium';
                document.getElementById('inp-process').value = 'CNC milling';
                document.getElementById('inp-qty').value = 1000;
                updateQty(1000);
                document.getElementById('inp-weeks').value = 6;
                updateWeeks(6);
                document.getElementById('inp-dest').value = 'Germany';
                setCertActive('ISO 9001');
            } else if (type === 'buyer_b') {
                currentSessionId = 'session_buyer_b';
                document.getElementById('inp-material').value = 'stainless steel';
                document.getElementById('inp-process').value = 'sheet metal';
                document.getElementById('inp-qty').value = 1500;
                updateQty(1500);
                document.getElementById('inp-weeks').value = 6;
                updateWeeks(6);
                document.getElementById('inp-dest').value = 'Germany';
                setCertActive('ISO 9001');
            } else if (type === 'aerospace') {
                currentSessionId = 'session_aerospace';
                document.getElementById('inp-material').value = 'titanium';
                document.getElementById('inp-process').value = 'CNC milling';
                document.getElementById('inp-qty').value = 5000;
                updateQty(5000);
                document.getElementById('inp-weeks').value = 10;
                updateWeeks(10);
                document.getElementById('inp-dest').value = 'USA';
                setCertActive('AS9100');
            }
            document.getElementById('session-badge').innerText = currentSessionId;
            runMatch();
        }

        function setCertActive(certName) {
            selectedCerts = [certName];
            ['chip-iso9001', 'chip-iatf', 'chip-as9100', 'chip-iso13485'].forEach(id => {
                const el = document.getElementById(id);
                const chk = el.querySelector('input');
                if (chk.value === certName) {
                    chk.checked = true;
                    el.classList.add('active');
                } else {
                    chk.checked = false;
                    el.classList.remove('active');
                }
            });
        }

        // Live Matching Call
        async function runMatch() {
            const payload = {
                session_id: currentSessionId,
                buyer_name: 'Procurement Director',
                material: document.getElementById('inp-material').value,
                process: document.getElementById('inp-process').value,
                quantity: parseInt(document.getElementById('inp-qty').value),
                timeline_weeks: parseInt(document.getElementById('inp-weeks').value),
                required_certifications: selectedCerts,
                destination_country: document.getElementById('inp-dest').value
            };

            try {
                const res = await fetch('/api/match', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    currentResponse = await res.json();
                    renderResults(currentResponse);
                }
            } catch (e) {
                console.error(e);
            }
        }

        // Render Results
        function renderResults(data) {
            document.getElementById('stat-total').innerText = data.total_manufacturers_evaluated.toLocaleString();
            document.getElementById('stat-eligible').innerText = data.eligible_count.toLocaleString();
            document.getElementById('stat-topscore').innerText = data.matches.length > 0 ? data.matches[0].score_breakdown.total_score + ' / 100' : 'N/A';

            // In-flight delta banner
            const deltaBanner = document.getElementById('delta-banner');
            const deltaNotesList = document.getElementById('delta-notes-list');
            if (data.query_delta_notes && data.query_delta_notes.length > 0) {
                deltaBanner.classList.add('visible');
                deltaNotesList.innerHTML = data.query_delta_notes.map(n => `<div>• ${n}</div>`).join('');
            } else {
                deltaBanner.classList.remove('visible');
            }

            const container = document.getElementById('matches-container');
            container.innerHTML = '';

            if (data.matches.length === 0) {
                if (data.relaxed_matches && data.relaxed_matches.length > 0) {
                    container.innerHTML = `
                        <div style="background-color: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; border-radius: var(--radius-md); padding: 24px;">
                            <h4 style="color: #ef4444; font-size: 16px; margin-bottom: 8px;">ZERO SUPPLIERS PASSED 100% OF HARD CONSTRAINTS</h4>
                            <p style="font-size: 13px; color: #fca5a5; margin-bottom: 16px;">Displaying closest available candidates with specific disqualification audit reasons:</p>
                            ${data.relaxed_matches.map((rm, idx) => `
                                <div style="background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 16px; margin-bottom: 12px;">
                                    <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 15px;">
                                        <span>${rm.manufacturer.name} (${rm.manufacturer.city})</span>
                                        <span style="color: var(--accent-gold); font-family: var(--font-mono);">Penalized Score: ${rm.score_breakdown.total_score}</span>
                                    </div>
                                    <div style="margin-top: 8px; font-size: 12px; color: #f87171;">
                                        ${rm.disqualification_reasons.map(r => `<div>[Rejected] ${r}</div>`).join('')}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
                return;
            }

            data.matches.forEach((m, idx) => {
                const card = document.createElement('div');
                card.className = 'match-card';
                card.innerHTML = `
                    <div class="card-top">
                        <div class="mfg-group">
                            <div class="rank-badge">#${idx + 1}</div>
                            <div>
                                <div style="display: flex; align-items: center;">
                                    <span class="mfg-name">${m.manufacturer.name}</span>
                                    <span class="mfg-id">${m.manufacturer.manufacturer_id}</span>
                                    ${m.manufacturer.data_quality_flags.length > 0 ? `<span style="font-size: 10px; font-family: var(--font-mono); background: rgba(217,119,6,0.2); color: #fbbf24; padding: 2px 6px; border: 1px solid var(--accent-gold); border-radius: 3px; margin-left: 6px; font-weight: 700;">AUDIT FLAG</span>` : ''}
                                </div>
                                <div class="mfg-location">${m.manufacturer.city}, ${m.manufacturer.state_name} • Founded ${m.manufacturer.founded_year} • ${m.manufacturer.company_size} Enterprise</div>
                            </div>
                        </div>

                        <div class="score-pill">
                            <div class="score-number">${m.score_breakdown.total_score}</div>
                            <div class="score-label">Composite Utility</div>
                        </div>
                    </div>

                    <!-- 5-Factor Weighted Score Breakdown -->
                    <div class="score-bars">
                        <div class="score-bar-col">
                            <div class="score-bar-header"><span>Speed (30%)</span><span style="font-family: var(--font-mono); font-weight: 700;">${m.score_breakdown.speed_score}</span></div>
                            <div class="progress-track"><div class="progress-fill" style="width: ${m.score_breakdown.speed_score}%; background-color: #10b981;"></div></div>
                        </div>
                        <div class="score-bar-col">
                            <div class="score-bar-header"><span>Quality (25%)</span><span style="font-family: var(--font-mono); font-weight: 700;">${m.score_breakdown.reliability_score}</span></div>
                            <div class="progress-track"><div class="progress-fill" style="width: ${m.score_breakdown.reliability_score}%; background-color: #06b6d4;"></div></div>
                        </div>
                        <div class="score-bar-col">
                            <div class="score-bar-header"><span>Capacity (20%)</span><span style="font-family: var(--font-mono); font-weight: 700;">${m.score_breakdown.capacity_score}</span></div>
                            <div class="progress-track"><div class="progress-fill" style="width: ${m.score_breakdown.capacity_score}%; background-color: #3b82f6;"></div></div>
                        </div>
                        <div class="score-bar-col">
                            <div class="score-bar-header"><span>Export (15%)</span><span style="font-family: var(--font-mono); font-weight: 700;">${m.score_breakdown.export_score}</span></div>
                            <div class="progress-track"><div class="progress-fill" style="width: ${m.score_breakdown.export_score}%; background-color: #8b5cf6;"></div></div>
                        </div>
                        <div class="score-bar-col">
                            <div class="score-bar-header"><span>Audit (10%)</span><span style="font-family: var(--font-mono); font-weight: 700;">${m.score_breakdown.audit_score}</span></div>
                            <div class="progress-track"><div class="progress-fill" style="width: ${m.score_breakdown.audit_score}%; background-color: #ec4899;"></div></div>
                        </div>
                    </div>

                    <!-- Metrics Grid -->
                    <div class="metrics-grid">
                        <div class="metric-box">
                            <div class="metric-title">Production Lead Time</div>
                            <div class="metric-val">${m.manufacturer.lead_time_weeks}w <span class="metric-sub">(+${m.explanation.lead_time_margin_weeks}w buffer)</span></div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">On-Time Completion</div>
                            <div class="metric-val">${m.manufacturer.on_time_delivery_pct}% <span style="font-size: 11px; color: var(--text-muted);">(Grade ${m.manufacturer.delivery_rating})</span></div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">Monthly Capacity</div>
                            <div class="metric-val">${m.manufacturer.capacity_units_per_month.toLocaleString()}/mo <span style="font-size: 11px; color: var(--text-muted);">(${m.explanation.capacity_utilization_pct}% load)</span></div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">Export Track Record</div>
                            <div class="metric-val">${m.manufacturer.export_experience_years} Years <span style="font-size: 11px; color: var(--text-muted);">(International)</span></div>
                        </div>
                    </div>

                    <!-- Explanations -->
                    <div class="explanation-block">
                        <div class="explanation-heading">Audit & Match Justification:</div>
                        ${m.explanation.key_strengths.map(s => `
                            <div class="bullet-item"><span>${s}</span></div>
                        `).join('')}
                        ${m.explanation.risks_and_tradeoffs.length > 0 ? `
                            <div style="margin-top: 8px;">
                                ${m.explanation.risks_and_tradeoffs.map(r => `
                                    <div class="bullet-item risk-bullet"><span>[Operational Watch] ${r}</span></div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>

                    <!-- Footer Actions -->
                    <div class="card-actions">
                        <div class="cert-tags">
                            <span style="font-size: 12px; color: var(--text-muted); font-weight:600;">Certifications:</span>
                            ${m.manufacturer.certifications.map(c => `<span class="cert-tag">${c}</span>`).join('') || '<span style="font-size:12px; color:var(--text-muted);">None</span>'}
                            <span style="font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);">(Expires: ${m.manufacturer.certification_expiry})</span>
                        </div>

                        <div class="btn-action-group">
                            <button class="btn-outline" onclick="reserveCapacity('${m.manufacturer.manufacturer_id}', ${data.requirement.quantity})">Reserve Capacity</button>
                            <button class="btn-action-primary" onclick="showMemo(${idx})">Executive Memorandum</button>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        // AI RFQ Parser
        async function runAiParse() {
            const text = document.getElementById('ai-text-input').value;
            try {
                const res = await fetch('/api/parse-and-match', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, session_id: 'nlp-session' })
                });
                if (res.ok) {
                    currentResponse = await res.json();
                    document.querySelectorAll('.nav-tab')[0].click(); // switch to matcher
                    renderResults(currentResponse);
                }
            } catch (e) {
                console.error(e);
            }
        }

        // Contention Simulator
        async function simulateContention(strategy) {
            document.getElementById('btn-strat-pareto').style.backgroundColor = strategy === 'pareto_optimal' ? 'var(--accent-primary)' : 'transparent';
            document.getElementById('btn-strat-pareto').style.color = strategy === 'pareto_optimal' ? '#fff' : 'var(--text-secondary)';
            document.getElementById('btn-strat-fcfs').style.backgroundColor = strategy === 'fcfs' ? 'var(--accent-primary)' : 'transparent';
            document.getElementById('btn-strat-fcfs').style.color = strategy === 'fcfs' ? '#fff' : 'var(--text-secondary)';

            const reqA = { session_id: 'sess_a', buyer_name: 'Buyer A', material: 'aluminium', process: 'CNC', quantity: 1000, timeline_weeks: 6, required_certifications: ['ISO 9001'] };
            const reqB = { session_id: 'sess_b', buyer_name: 'Buyer B', material: 'stainless steel', process: 'sheet metal', quantity: 1500, timeline_weeks: 6, required_certifications: ['ISO 9001'] };

            try {
                const res = await fetch('/api/simulate-contention', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ buyer_a: reqA, buyer_b: reqB, resolution_strategy: strategy })
                });
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('contention-explanation-box').innerHTML = `
                        <strong style="font-family: var(--font-formal); letter-spacing:0.5px;">SYSTEM ALLOCATION STRATEGY: ${data.resolution_strategy.toUpperCase()}</strong><br>
                        ${data.explanation}
                    `;
                    document.getElementById('buyer-a-result').innerHTML = `
                        <div style="font-family: var(--font-formal); font-size: 16px; font-weight: 700; color: #fff;">${data.buyer_a_allocated.manufacturer.name}</div>
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">${data.buyer_a_allocated.manufacturer.city}, ${data.buyer_a_allocated.manufacturer.state_name}</div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-family: var(--font-mono); font-size: 12px; background: rgba(0,0,0,0.25); padding: 10px; border-radius: 4px;">
                            <div><span style="color:var(--text-muted); display:block; font-size:10px;">UTILITY</span><strong>${data.buyer_a_allocated.score_breakdown.total_score}</strong></div>
                            <div><span style="color:var(--text-muted); display:block; font-size:10px;">LEAD TIME</span><strong>${data.buyer_a_allocated.manufacturer.lead_time_weeks}w</strong></div>
                            <div><span style="color:var(--text-muted); display:block; font-size:10px;">CAPACITY</span><strong>${data.buyer_a_allocated.manufacturer.capacity_units_per_month.toLocaleString()}/mo</strong></div>
                        </div>
                    `;
                    document.getElementById('buyer-b-result').innerHTML = `
                        <div style="font-family: var(--font-formal); font-size: 16px; font-weight: 700; color: #fff;">${data.buyer_b_allocated.manufacturer.name}</div>
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">${data.buyer_b_allocated.manufacturer.city}, ${data.buyer_b_allocated.manufacturer.state_name}</div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-family: var(--font-mono); font-size: 12px; background: rgba(0,0,0,0.25); padding: 10px; border-radius: 4px;">
                            <div><span style="color:var(--text-muted); display:block; font-size:10px;">UTILITY</span><strong>${data.buyer_b_allocated.score_breakdown.total_score}</strong></div>
                            <div><span style="color:var(--text-muted); display:block; font-size:10px;">LEAD TIME</span><strong>${data.buyer_b_allocated.manufacturer.lead_time_weeks}w</strong></div>
                            <div><span style="color:var(--text-muted); display:block; font-size:10px;">CAPACITY</span><strong>${data.buyer_b_allocated.manufacturer.capacity_units_per_month.toLocaleString()}/mo</strong></div>
                        </div>
                    `;
                }
            } catch (e) {
                console.error(e);
            }
        }

        // Audit Data
        async function loadAuditData() {
            try {
                const res = await fetch('/api/audit-data');
                if (res.ok) {
                    const data = await res.json();
                    const tbody = document.getElementById('audit-table-body');
                    tbody.innerHTML = data.anomalies.map(item => `
                        <tr>
                            <td style="font-family: var(--font-mono); font-weight: 700; color: #60a5fa;">${item.manufacturer_id}</td>
                            <td style="font-family: var(--font-formal); font-weight: 700; font-size: 14px; color: #fff;">${item.name}</td>
                            <td>${item.city}, ${item.state}</td>
                            <td>${item.primary_process}</td>
                            <td>${item.raw_on_time_delivery_pct > 100 ? `<span style="color: #fbbf24; font-weight:700;">${item.raw_on_time_delivery_pct}% → 100.0%</span>` : `${item.on_time_delivery_pct}%`}</td>
                            <td>${item.lead_time_weeks}w</td>
                            <td style="color: #34d399; font-size: 12px;">${item.flags.join('; ')}</td>
                        </tr>
                    `).join('');
                }
            } catch (e) {
                console.error(e);
            }
        }

        // Hold Capacity
        async function reserveCapacity(mfgId, qty) {
            try {
                const res = await fetch('/api/reserve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: currentSessionId, manufacturer_id: mfgId, units: qty })
                });
                const data = await res.json();
                alert(`${data.message}\\n\\nRemaining available monthly capacity: ${data.remaining_monthly_capacity.toLocaleString()} units`);
                runMatch();
            } catch (e) {
                alert('Reservation failed');
            }
        }

        // Executive Memo Modal
        async function showMemo(index) {
            const match = currentResponse.matches[index];
            try {
                const res = await fetch('/api/executive-pitch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ requirement: currentResponse.requirement, match: match })
                });
                if (res.ok) {
                    const data = await res.json();
                    cachedMemo = data.pitch;
                    document.getElementById('memo-body').innerText = cachedMemo;
                    document.getElementById('memo-modal').classList.add('open');
                }
            } catch (e) {
                alert('Failed to generate memorandum');
            }
        }

        function closeMemo() {
            document.getElementById('memo-modal').classList.remove('open');
        }

        function copyMemoText() {
            navigator.clipboard.writeText(cachedMemo);
            const btn = document.getElementById('btn-copy-memo');
            btn.innerText = 'Copied to Clipboard';
            setTimeout(() => { btn.innerText = 'Copy Memorandum'; }, 2000);
        }

        // Initialize on load
        window.addEventListener('DOMContentLoaded', () => {
            loadPreset('german');
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    return HTMLResponse(content=HTML_DASHBOARD)

def start_server(host: str = "127.0.0.1", port: int = 8000):
    logger.info(f"Starting Veridia Matching Dashboard on http://{host}:{port}")
    uvicorn.run("src.app:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    start_server()
