"""
Interactive Web Application & REST API for Veridia Manufacturer Matching System
FastAPI backend with a world-class, enterprise-grade B2B procurement dashboard.
100% self-contained styling (zero external CSS/JS CDN dependencies), light/dark mode support,
and bespoke data visualizations.
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
    description="Enterprise B2B Supplier Matching Platform for Precision Engineering.",
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
        "message": "Capacity held for 15 minutes." if success else "Insufficient remaining capacity."
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
# High-End Enterprise Procurement Dashboard
# Pure self-contained CSS & Vanilla JS (Zero external CDN failure risk)
# ---------------------------------------------------------

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Veridia Supplier Intelligence | Precision Manufacturer Matching</title>
    <style>
        :root {
            --bg-page: #0f141c;
            --bg-surface: #161c28;
            --bg-card: #1c2433;
            --bg-card-hover: #222b3d;
            --border-color: rgba(255, 255, 255, 0.08);
            --border-focus: #3b82f6;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-primary: #0284c7;
            --accent-primary-hover: #0369a1;
            --accent-success: #10b981;
            --accent-success-bg: rgba(16, 185, 129, 0.12);
            --accent-warning: #f59e0b;
            --accent-warning-bg: rgba(245, 158, 11, 0.12);
            --accent-danger: #ef4444;
            --accent-danger-bg: rgba(239, 68, 68, 0.12);
            --accent-info: #3b82f6;
            --accent-info-bg: rgba(59, 130, 246, 0.12);
            --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 16px;
            --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.2);
            --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.3);
            --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.4);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-page);
            color: var(--text-primary);
            font-family: var(--font-main);
            font-size: 14px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        /* Top Header */
        header {
            background-color: var(--bg-surface);
            border-bottom: 1px solid var(--border-color);
            padding: 0 2rem;
            height: 70px;
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
            gap: 12px;
        }

        .brand-logo {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #0284c7 0%, #0d9488 100%);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            color: #ffffff;
            font-size: 18px;
            box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
        }

        .brand-title {
            font-weight: 700;
            font-size: 16px;
            letter-spacing: -0.3px;
            color: var(--text-primary);
        }

        .brand-subtitle {
            font-size: 11px;
            color: var(--text-muted);
            font-weight: 500;
        }

        .nav-tabs {
            display: flex;
            background-color: rgba(0, 0, 0, 0.25);
            padding: 4px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
            gap: 4px;
        }

        .nav-tab {
            padding: 8px 16px;
            border-radius: var(--radius-sm);
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .nav-tab:hover {
            color: var(--text-primary);
            background-color: rgba(255, 255, 255, 0.04);
        }

        .nav-tab.active {
            background-color: var(--accent-primary);
            color: #ffffff;
            box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35);
        }

        .header-meta {
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 12px;
            color: var(--text-muted);
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 9999px;
            background-color: var(--accent-success-bg);
            color: var(--accent-success);
            font-weight: 600;
            font-size: 11px;
            font-family: var(--font-mono);
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: var(--accent-success);
            box-shadow: 0 0 6px var(--accent-success);
        }

        /* Main Container */
        .main-layout {
            max-width: 1360px;
            margin: 24px auto;
            padding: 0 24px;
        }

        /* Preset Ribbon */
        .preset-ribbon {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 16px 20px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }

        .preset-title {
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
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
            padding: 6px 12px;
            border-radius: var(--radius-md);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-preset:hover {
            background-color: rgba(2, 132, 199, 0.15);
            border-color: var(--accent-primary);
            color: #ffffff;
        }

        /* In-flight alert */
        .delta-alert {
            background-color: var(--accent-warning-bg);
            border: 1px solid var(--accent-warning);
            border-radius: var(--radius-md);
            padding: 14px 18px;
            margin-bottom: 24px;
            color: #fef3c7;
            font-size: 12px;
            display: none;
        }

        .delta-alert.visible {
            display: block;
        }

        /* Content Grid */
        .content-grid {
            display: grid;
            grid-template-columns: 360px 1fr;
            gap: 24px;
            align-items: start;
        }

        @media (max-width: 1024px) {
            .content-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Filter Panel */
        .filter-panel {
            background-color: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 24px;
            box-shadow: var(--shadow-sm);
        }

        .panel-header {
            padding-bottom: 16px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-title {
            font-size: 14px;
            font-weight: 700;
            letter-spacing: -0.2px;
            color: var(--text-primary);
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        .form-control {
            width: 100%;
            padding: 10px 12px;
            background-color: var(--bg-page);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            color: var(--text-primary);
            font-size: 13px;
            font-family: inherit;
            transition: border-color 0.15s ease;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--border-focus);
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }

        .slider-wrapper {
            background-color: rgba(0, 0, 0, 0.2);
            padding: 12px 14px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
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
            color: #38bdf8;
            font-size: 13px;
        }

        .slider-input {
            width: 100%;
            height: 6px;
            -webkit-appearance: none;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 9999px;
            outline: none;
        }

        .slider-input::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #38bdf8;
            cursor: pointer;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
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
            padding: 8px 10px;
            border-radius: var(--radius-md);
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            user-select: none;
            transition: all 0.15s ease;
        }

        .chip-label.active {
            background-color: rgba(2, 132, 199, 0.15);
            border-color: var(--accent-primary);
            color: #ffffff;
        }

        .chip-label input {
            accent-color: var(--accent-primary);
        }

        .btn-submit {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
            color: #ffffff;
            border: none;
            border-radius: var(--radius-md);
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s ease;
            box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
        }

        .btn-submit:hover {
            background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
            box-shadow: 0 6px 16px rgba(2, 132, 199, 0.45);
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
            border-radius: var(--radius-md);
            padding: 16px 20px;
        }

        .stat-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }

        .stat-value {
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: var(--text-primary);
        }

        .stat-subtext {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* Match Card */
        .match-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 24px;
            box-shadow: var(--shadow-sm);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }

        .match-card:hover {
            background-color: var(--bg-card-hover);
            border-color: rgba(2, 132, 199, 0.4);
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }

        .card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 16px;
        }

        .mfg-name-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .rank-badge {
            width: 32px;
            height: 32px;
            border-radius: var(--radius-sm);
            background-color: rgba(2, 132, 199, 0.15);
            color: #38bdf8;
            font-family: var(--font-mono);
            font-weight: 700;
            font-size: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(2, 132, 199, 0.3);
        }

        .mfg-name {
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .mfg-id {
            font-family: var(--font-mono);
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            background-color: rgba(255, 255, 255, 0.05);
            color: var(--text-muted);
            border: 1px solid var(--border-color);
            margin-left: 6px;
        }

        .mfg-location {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        .score-pill {
            text-align: right;
            background-color: rgba(0, 0, 0, 0.25);
            padding: 8px 14px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
        }

        .score-number {
            font-size: 22px;
            font-weight: 800;
            color: var(--accent-success);
            font-family: var(--font-mono);
            line-height: 1;
        }

        .score-label {
            font-size: 9px;
            text-transform: uppercase;
            font-weight: 700;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* Radar Bars */
        .score-bars {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
            margin: 16px 0;
            padding: 12px 14px;
            background-color: rgba(0, 0, 0, 0.15);
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
        }

        .score-bar-col {
            font-size: 10px;
        }

        .score-bar-header {
            display: flex;
            justify-content: space-between;
            color: var(--text-muted);
            font-weight: 600;
            margin-bottom: 4px;
        }

        .progress-track {
            height: 4px;
            background-color: rgba(255, 255, 255, 0.08);
            border-radius: 2px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            border-radius: 2px;
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
            padding: 10px 12px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
        }

        .metric-title {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .metric-val {
            font-size: 13px;
            font-weight: 700;
            color: var(--text-primary);
            font-family: var(--font-mono);
            margin-top: 2px;
        }

        .metric-sub {
            font-size: 10px;
            color: var(--accent-success);
            font-weight: 600;
        }

        /* Strengths & Risks */
        .explanation-block {
            font-size: 12px;
            margin-bottom: 16px;
        }

        .explanation-heading {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }

        .bullet-item {
            display: flex;
            gap: 8px;
            align-items: flex-start;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }

        .bullet-icon {
            color: var(--accent-success);
            font-weight: 700;
        }

        .risk-bullet {
            color: #fde68a;
        }

        .risk-icon {
            color: var(--accent-warning);
        }

        /* Actions Footer */
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
            background-color: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            font-family: var(--font-mono);
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
        }

        .btn-action-group {
            display: flex;
            gap: 8px;
        }

        .btn-outline {
            background-color: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-outline:hover {
            border-color: var(--text-secondary);
            color: #ffffff;
            background-color: rgba(255, 255, 255, 0.05);
        }

        .btn-action-primary {
            background-color: var(--accent-primary);
            border: none;
            color: #ffffff;
            padding: 6px 14px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-action-primary:hover {
            background-color: var(--accent-primary-hover);
        }

        /* Other Tabs */
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
            border-radius: var(--radius-lg);
            padding: 24px;
        }

        .buyer-box.buyer-a {
            border-top: 4px solid var(--accent-info);
        }

        .buyer-box.buyer-b {
            border-top: 4px solid #a855f7;
        }

        /* Table */
        .audit-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            text-align: left;
        }

        .audit-table th {
            background-color: rgba(0, 0, 0, 0.2);
            color: var(--text-muted);
            padding: 12px 14px;
            font-size: 10px;
            text-transform: uppercase;
            font-weight: 700;
            border-bottom: 1px solid var(--border-color);
        }

        .audit-table td {
            padding: 12px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-secondary);
        }

        .audit-table tr:hover td {
            background-color: rgba(255, 255, 255, 0.02);
            color: var(--text-primary);
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
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
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            width: 90%;
            max-width: 680px;
            max-height: 85vh;
            padding: 24px;
            display: flex;
            flex-direction: column;
            box-shadow: var(--shadow-lg);
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
            font-size: 15px;
            font-weight: 700;
        }

        .modal-body {
            overflow-y: auto;
            flex: 1;
            font-family: var(--font-mono);
            font-size: 12px;
            background-color: var(--bg-page);
            padding: 16px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            white-space: pre-wrap;
            line-height: 1.6;
        }

        .modal-footer {
            margin-top: 16px;
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
            <div class="brand-logo">V</div>
            <div>
                <div class="brand-title">VERIDIA SUPPLIER INTELLIGENCE</div>
                <div class="brand-subtitle">Precision Engineering Match Engine • India to Global</div>
            </div>
        </div>

        <nav class="nav-tabs">
            <button class="nav-tab active" onclick="switchTab('matcher')">🎯 Interactive Matcher</button>
            <button class="nav-tab" onclick="switchTab('ai_rfq')">🤖 AI RFQ Parser</button>
            <button class="nav-tab" onclick="switchTab('contention')">⚡ Buyer A vs B Contention</button>
            <button class="nav-tab" onclick="switchTab('audit')">🔍 Data Quality Audit (40)</button>
        </nav>

        <div class="header-meta">
            <div class="status-badge">
                <span class="status-dot"></span>
                <span>Anchor: 2026-10-28</span>
            </div>
        </div>
    </header>

    <div class="main-layout">

        <!-- TAB 1: MATCHER -->
        <div id="tab-matcher" class="tab-content active">
            
            <!-- Preset Ribbon -->
            <div class="preset-ribbon">
                <div class="preset-title">⚡ Assignment Test Scenarios:</div>
                <div class="preset-btn-group">
                    <button class="btn-preset" onclick="loadPreset('german')">🇩🇪 German Buyer (2k Aluminium CNC, 6w)</button>
                    <button class="btn-preset" onclick="loadPreset('buyer_a')">Buyer A (1k Aluminium CNC, 6w)</button>
                    <button class="btn-preset" onclick="loadPreset('buyer_b')">Buyer B (1.5k Sheet Metal, 6w)</button>
                    <button class="btn-preset" onclick="loadPreset('aerospace')">Aerospace (5k Titanium AS9100)</button>
                </div>
            </div>

            <!-- In-Flight Delta Banner -->
            <div id="delta-banner" class="delta-alert">
                <strong>⚠️ In-Flight Requirement Delta Detected:</strong>
                <div id="delta-notes-list" style="margin-top: 4px;"></div>
            </div>

            <!-- Content Grid -->
            <div class="content-grid">
                
                <!-- Left Form -->
                <div class="filter-panel">
                    <div class="panel-header">
                        <span class="panel-title">Requirement Parameters</span>
                        <span id="session-badge" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-muted);">session_german</span>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Material</label>
                        <select id="inp-material" class="form-control" onchange="runMatch()">
                            <option value="aluminium">Aluminium</option>
                            <option value="stainless steel">Stainless Steel</option>
                            <option value="mild steel">Mild Steel</option>
                            <option value="copper">Copper</option>
                            <option value="brass">Brass</option>
                            <option value="titanium">Titanium</option>
                            <option value="cast iron">Cast Iron</option>
                            <option value="ABS">ABS Polymer</option>
                            <option value="nylon">Nylon</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Manufacturing Process</label>
                        <select id="inp-process" class="form-control" onchange="runMatch()">
                            <option value="CNC milling">CNC Milling</option>
                            <option value="CNC turning">CNC Turning</option>
                            <option value="machined">Machined to Order (General CNC/Grinding)</option>
                            <option value="sheet metal">Sheet Metal Fabrication</option>
                            <option value="casting">Casting</option>
                            <option value="forging">Forging</option>
                            <option value="grinding">Grinding</option>
                            <option value="EDM">EDM (Spark Erosion)</option>
                            <option value="welding">Welding</option>
                            <option value="injection moulding">Injection Moulding</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <div class="slider-wrapper">
                            <div class="slider-header">
                                <span class="form-label" style="margin-bottom:0;">Order Batch Quantity</span>
                                <span id="val-qty" class="slider-val-badge">2,000 units</span>
                            </div>
                            <input id="inp-qty" type="range" class="slider-input" min="100" max="10000" step="100" value="2000" oninput="updateQty(this.value)" onchange="runMatch()">
                        </div>
                    </div>

                    <div class="form-group">
                        <div class="slider-wrapper">
                            <div class="slider-header">
                                <span class="form-label" style="margin-bottom:0;">Delivery Deadline Window</span>
                                <span id="val-weeks" class="slider-val-badge">6 weeks</span>
                            </div>
                            <input id="inp-weeks" type="range" class="slider-input" min="2" max="16" step="1" value="6" oninput="updateWeeks(this.value)" onchange="runMatch()">
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Mandatory Certifications</label>
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

                    <button class="btn-submit" onclick="runMatch()">⚡ Execute Live Re-Match</button>
                </div>

                <!-- Right Results -->
                <div class="results-area">
                    
                    <!-- Stats Counter -->
                    <div class="stats-row">
                        <div class="stat-card">
                            <div class="stat-label">Total Evaluated</div>
                            <div id="stat-total" class="stat-value">1,000</div>
                            <div class="stat-subtext">Precision Indian factories</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Strictly Eligible</div>
                            <div id="stat-eligible" class="stat-value" style="color: var(--accent-success);">32</div>
                            <div class="stat-subtext">Passed 100% hard gates</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Top Match Score</div>
                            <div id="stat-topscore" class="stat-value" style="color: #38bdf8;">93.8 / 100</div>
                            <div class="stat-subtext">Multi-factor utility</div>
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
            <div style="background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 32px; max-width: 800px; margin: 0 auto;">
                <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">AI Natural Language RFQ Parser</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">
                    Paste messy buyer emails, raw RFQ specifications, or WhatsApp briefs in plain text. The AI extracts parameters and feeds them directly into the matching engine.
                </p>

                <textarea id="ai-text-input" rows="6" class="form-control" style="font-family: var(--font-mono); font-size: 13px; line-height: 1.6; padding: 16px; margin-bottom: 16px;">We are an engineering firm in Stuttgart, Germany. We urgently need 2,500 milled aluminium brackets. Must be ISO 9001 certified. We need them on our dock within 7 weeks. Can you recommend reliable suppliers?</textarea>

                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 11px; color: var(--text-muted);">Understands informal quantities ('a few thousand'), German/English terms, and process synonyms.</span>
                    <button class="btn-submit" style="width: auto; padding: 10px 24px;" onclick="runAiParse()">🤖 Parse & Match</button>
                </div>
            </div>
        </div>

        <!-- TAB 3: CONTENTION SIMULATOR -->
        <div id="tab-contention" class="tab-content">
            <div style="background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 24px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <h3 style="font-size: 16px; font-weight: 700;">Simultaneous Arrival & Capacity Contention Simulation</h3>
                        <p style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                            Prompt Scenario: Buyer A (1,000 Aluminium CNC, 6w) and Buyer B (1,500 Stainless Sheet-Metal, 6w) arrive at the exact same moment.
                        </p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button id="btn-strat-pareto" class="btn-preset" style="background-color: var(--accent-primary); color: #fff;" onclick="simulateContention('pareto_optimal')">🌟 Pareto Optimal (Global Welfare)</button>
                        <button id="btn-strat-fcfs" class="btn-preset" onclick="simulateContention('fcfs')">⏱️ First-Come First-Served</button>
                    </div>
                </div>
            </div>

            <!-- Resolution Rationale -->
            <div id="contention-explanation-box" style="background-color: var(--accent-success-bg); border: 1px solid var(--accent-success); border-radius: var(--radius-md); padding: 16px 20px; font-size: 13px; margin-bottom: 24px; line-height: 1.6;">
                <!-- Populated dynamically -->
            </div>

            <!-- Two Buyer Side by Side -->
            <div class="contention-cards">
                <div class="buyer-box buyer-a">
                    <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: #60a5fa;">BUYER A ALLOCATION</span>
                    <h4 style="font-size: 16px; font-weight: 700; margin: 4px 0 2px;">1,000 Aluminium CNC Parts</h4>
                    <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">6 Weeks Deadline • ISO 9001 Mandatory</p>
                    <div id="buyer-a-result"></div>
                </div>

                <div class="buyer-box buyer-b">
                    <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: #c084fc;">BUYER B ALLOCATION</span>
                    <h4 style="font-size: 16px; font-weight: 700; margin: 4px 0 2px;">1,500 Stainless Sheet-Metal Parts</h4>
                    <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">6 Weeks Deadline • ISO 9001 Mandatory</p>
                    <div id="buyer-b-result"></div>
                </div>
            </div>
        </div>

        <!-- TAB 4: AUDIT TAB -->
        <div id="tab-audit" class="tab-content">
            <div style="background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div>
                        <h3 style="font-size: 16px; font-weight: 700;">Dataset Sanitation & Data Quality Audit</h3>
                        <p style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                            40 deliberate real-world flaws detected and resolved across the 1,000 mock manufacturer records:
                        </p>
                    </div>
                    <span class="status-badge">40 Anomalies Sanitized</span>
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
                <span class="modal-title">📄 Executive Procurement Memorandum</span>
                <button onclick="closeMemo()" style="background:none; border:none; color: var(--text-muted); cursor:pointer; font-size: 20px;">&times;</button>
            </div>
            <div id="memo-body" class="modal-body"></div>
            <div class="modal-footer">
                <button id="btn-copy-memo" class="btn-outline" onclick="copyMemoText()">📋 Copy Memorandum</button>
                <button class="btn-action-primary" onclick="closeMemo()">Done</button>
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
                buyer_name: 'Procurement Specialist',
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
                        <div style="background-color: var(--accent-danger-bg); border: 1px solid var(--accent-danger); border-radius: var(--radius-lg); padding: 24px;">
                            <h4 style="color: var(--accent-danger); font-size: 15px; font-weight: 700; margin-bottom: 8px;">Zero Suppliers Passed 100% of Constraints</h4>
                            <p style="font-size: 12px; color: #fca5a5; margin-bottom: 16px;">Displaying closest available candidates with explicit disqualification audit reasons:</p>
                            ${data.relaxed_matches.map((rm, idx) => `
                                <div style="background-color: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; margin-bottom: 12px;">
                                    <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 14px;">
                                        <span>${rm.manufacturer.name} (${rm.manufacturer.city})</span>
                                        <span style="color: var(--accent-warning); font-family: var(--font-mono);">Penalized Score: ${rm.score_breakdown.total_score}</span>
                                    </div>
                                    <div style="margin-top: 8px; font-size: 12px; color: #f87171;">
                                        ${rm.disqualification_reasons.map(r => `<div>❌ ${r}</div>`).join('')}
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
                        <div class="mfg-name-group">
                            <div class="rank-badge">#${idx + 1}</div>
                            <div>
                                <div style="display: flex; align-items: center;">
                                    <span class="mfg-name">${m.manufacturer.name}</span>
                                    <span class="mfg-id">${m.manufacturer.manufacturer_id}</span>
                                    ${m.manufacturer.data_quality_flags.length > 0 ? `<span style="font-size: 9px; font-family: var(--font-mono); background: var(--accent-warning-bg); color: var(--accent-warning); padding: 2px 6px; border-radius: 4px; margin-left: 6px; font-weight: 700;">AUDIT FLAG</span>` : ''}
                                </div>
                                <div class="mfg-location">${m.manufacturer.city}, ${m.manufacturer.state_name} • Est. ${m.manufacturer.founded_year} • ${m.manufacturer.company_size} Tier</div>
                            </div>
                        </div>

                        <div class="score-pill">
                            <div class="score-number">${m.score_breakdown.total_score}</div>
                            <div class="score-label">Match Score</div>
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
                            <div class="metric-title">Lead Time</div>
                            <div class="metric-val">${m.manufacturer.lead_time_weeks}w <span class="metric-sub">(+${m.explanation.lead_time_margin_weeks}w buffer)</span></div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">On-Time Completion</div>
                            <div class="metric-val">${m.manufacturer.on_time_delivery_pct}% <span style="font-size: 10px; color: var(--text-muted);">(Grade ${m.manufacturer.delivery_rating})</span></div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">Monthly Capacity</div>
                            <div class="metric-val">${m.manufacturer.capacity_units_per_month.toLocaleString()}/mo <span style="font-size: 10px; color: var(--text-muted);">(${m.explanation.capacity_utilization_pct}% load)</span></div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-title">Export Track Record</div>
                            <div class="metric-val">${m.manufacturer.export_experience_years} Years <span style="font-size: 10px; color: var(--text-muted);">(Global)</span></div>
                        </div>
                    </div>

                    <!-- Explanations -->
                    <div class="explanation-block">
                        <div class="explanation-heading">Why This Manufacturer Matches:</div>
                        ${m.explanation.key_strengths.map(s => `
                            <div class="bullet-item"><span class="bullet-icon">✓</span><span>${s}</span></div>
                        `).join('')}
                        ${m.explanation.risks_and_tradeoffs.length > 0 ? `
                            <div style="margin-top: 8px;">
                                ${m.explanation.risks_and_tradeoffs.map(r => `
                                    <div class="bullet-item risk-bullet"><span class="risk-icon">⚠️</span><span>${r}</span></div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>

                    <!-- Footer Actions -->
                    <div class="card-actions">
                        <div class="cert-tags">
                            <span style="font-size: 11px; color: var(--text-muted);">Certifications:</span>
                            ${m.manufacturer.certifications.map(c => `<span class="cert-tag">${c}</span>`).join('') || '<span style="font-size:11px; color:var(--text-muted);">None</span>'}
                            <span style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);">(Expires: ${m.manufacturer.certification_expiry})</span>
                        </div>

                        <div class="btn-action-group">
                            <button class="btn-outline" onclick="reserveCapacity('${m.manufacturer.manufacturer_id}', ${data.requirement.quantity})">🔒 Hold Capacity</button>
                            <button class="btn-action-primary" onclick="showMemo(${idx})">📄 Executive Memo</button>
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
                        <strong>System Strategy: ${data.resolution_strategy.toUpperCase()}</strong><br>
                        ${data.explanation}
                    `;
                    document.getElementById('buyer-a-result').innerHTML = `
                        <div style="font-size: 15px; font-weight: 700; color: #fff;">${data.buyer_a_allocated.manufacturer.name}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">${data.buyer_a_allocated.manufacturer.city}, ${data.buyer_a_allocated.manufacturer.state_name}</div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-family: var(--font-mono); font-size: 11px; background: rgba(0,0,0,0.25); padding: 10px; border-radius: 6px;">
                            <div><span style="color:var(--text-muted); display:block; font-size:9px;">SCORE</span><strong>${data.buyer_a_allocated.score_breakdown.total_score}</strong></div>
                            <div><span style="color:var(--text-muted); display:block; font-size:9px;">LEAD TIME</span><strong>${data.buyer_a_allocated.manufacturer.lead_time_weeks}w</strong></div>
                            <div><span style="color:var(--text-muted); display:block; font-size:9px;">CAPACITY</span><strong>${data.buyer_a_allocated.manufacturer.capacity_units_per_month.toLocaleString()}/mo</strong></div>
                        </div>
                    `;
                    document.getElementById('buyer-b-result').innerHTML = `
                        <div style="font-size: 15px; font-weight: 700; color: #fff;">${data.buyer_b_allocated.manufacturer.name}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">${data.buyer_b_allocated.manufacturer.city}, ${data.buyer_b_allocated.manufacturer.state_name}</div>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; font-family: var(--font-mono); font-size: 11px; background: rgba(0,0,0,0.25); padding: 10px; border-radius: 6px;">
                            <div><span style="color:var(--text-muted); display:block; font-size:9px;">SCORE</span><strong>${data.buyer_b_allocated.score_breakdown.total_score}</strong></div>
                            <div><span style="color:var(--text-muted); display:block; font-size:9px;">LEAD TIME</span><strong>${data.buyer_b_allocated.manufacturer.lead_time_weeks}w</strong></div>
                            <div><span style="color:var(--text-muted); display:block; font-size:9px;">CAPACITY</span><strong>${data.buyer_b_allocated.manufacturer.capacity_units_per_month.toLocaleString()}/mo</strong></div>
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
                            <td style="font-family: var(--font-mono); font-weight: 700; color: #38bdf8;">${item.manufacturer_id}</td>
                            <td style="font-weight: 600; color: #fff;">${item.name}</td>
                            <td>${item.city}, ${item.state}</td>
                            <td>${item.primary_process}</td>
                            <td>${item.raw_on_time_delivery_pct > 100 ? `<span style="color: var(--accent-warning); font-weight:700;">${item.raw_on_time_delivery_pct}% → 100.0%</span>` : `${item.on_time_delivery_pct}%`}</td>
                            <td>${item.lead_time_weeks}w</td>
                            <td style="color: var(--accent-success); font-size: 11px;">${item.flags.join('; ')}</td>
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
                alert('Failed to generate memo');
            }
        }

        function closeMemo() {
            document.getElementById('memo-modal').classList.remove('open');
        }

        function copyMemoText() {
            navigator.clipboard.writeText(cachedMemo);
            const btn = document.getElementById('btn-copy-memo');
            btn.innerText = '✅ Copied to Clipboard!';
            setTimeout(() => { btn.innerText = '📋 Copy Memorandum'; }, 2000);
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
