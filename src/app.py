"""
Interactive Web Application & REST API for Veridia Manufacturer Matching System
FastAPI backend with embedded responsive Tailwind/Alpine/Chart.js procurement dashboard.
"""
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, Any
from datetime import date, datetime
import json
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
    title="Veridia Manufacturer Matching API",
    description="Precision engineering supplier matching engine with capacity contention resolution and explainable scoring.",
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
    """Matches a buyer requirement within an isolated session context."""
    try:
        response = allocator.execute_session_match(req)
        return response
    except Exception as e:
        logger.error(f"Error matching requirement: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/parse-and-match", response_model=SearchResponse)
def parse_and_match(payload: Dict[str, str] = Body(...)):
    """Parses natural language RFQ text and executes matching."""
    text = payload.get("text", "")
    session_id = payload.get("session_id", "nlp-session")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text field cannot be empty.")

    req = ai_service.parse_natural_language_rfq(text, session_id=session_id)
    response = allocator.execute_session_match(req)
    return response

@app.post("/api/simulate-contention", response_model=ContentionSimulationResponse)
def simulate_contention(req: ContentionSimulationRequest):
    """Simulates simultaneous arrival and capacity contention between two buyers."""
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
    """Places a temporary capacity reservation for a buyer session."""
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

@app.post("/api/release-reservation")
def release_reservation(payload: Dict[str, Any] = Body(...)):
    session_id = payload.get("session_id", "default")
    manufacturer_id = payload.get("manufacturer_id")
    allocator.release_reservation(session_id, manufacturer_id)
    return {"status": "released", "session_id": session_id}

@app.get("/api/audit-data")
def get_audit_data():
    """Returns all data quality anomalies detected and cleaned in the dataset."""
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
    """Generates an executive memo for a specific match result."""
    try:
        req_data = payload.get("requirement")
        match_data = payload.get("match")
        req = BuyerRequirement(**req_data)
        from src.models import MatchResult
        match = MatchResult(**match_data)
        pitch = ai_service.generate_executive_pitch(match, req)
        return {"pitch": pitch}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------
# Embedded Web Dashboard UI
# ---------------------------------------------------------

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Veridia - Precision Manufacturer Matching System</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
        code, pre { font-family: 'JetBrains Mono', monospace; }
        .score-gradient { background: linear-gradient(135deg, #059669 0%, #0d9488 100%); }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen" x-data="veridiaApp()" x-init="initApp()">

    <!-- Top Navigation Bar -->
    <header class="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-lg bg-emerald-500 flex items-center justify-center font-black text-slate-950 text-xl shadow-lg shadow-emerald-500/20">V</div>
                <div>
                    <span class="text-lg font-bold tracking-tight text-white">VERIDIA</span>
                    <span class="text-xs text-emerald-400 font-mono ml-2 px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800">Precision Match Engine</span>
                </div>
            </div>

            <!-- Tab Switcher -->
            <div class="flex space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800">
                <button @click="activeTab = 'finder'" :class="activeTab === 'finder' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-white'" class="px-4 py-1.5 text-xs rounded-lg transition-all">
                    🎯 Interactive Matcher
                </button>
                <button @click="activeTab = 'nlp'" :class="activeTab === 'nlp' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-white'" class="px-4 py-1.5 text-xs rounded-lg transition-all">
                    🤖 AI RFQ Parser
                </button>
                <button @click="activeTab = 'contention'" :class="activeTab === 'contention' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-white'" class="px-4 py-1.5 text-xs rounded-lg transition-all">
                    ⚡ Buyer A vs B Contention
                </button>
                <button @click="activeTab = 'audit'" :class="activeTab === 'audit' ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-white'" class="px-4 py-1.5 text-xs rounded-lg transition-all">
                    🔍 Data Quality Audit (40)
                </button>
            </div>

            <!-- Temporal Anchor & Status -->
            <div class="flex items-center space-x-3 text-xs text-slate-400">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>As-Of Date: <strong class="text-slate-200">2026-10-28</strong></span>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        <!-- TAB 1: INTERACTIVE MATCHER -->
        <div x-show="activeTab === 'finder'" class="space-y-6">
            
            <!-- Quick Presets -->
            <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800 flex items-center justify-between">
                <div class="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                    <span>⚡ Quick Test Scenarios:</span>
                </div>
                <div class="flex flex-wrap gap-2">
                    <button @click="loadPreset('german')" class="px-3 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-emerald-300 hover:border-emerald-500 transition-all">
                        🇩🇪 German Buyer (2,000 Aluminium CNC, 6w)
                    </button>
                    <button @click="loadPreset('buyer_a')" class="px-3 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-blue-300 hover:border-blue-500 transition-all">
                        Buyer A (1,000 Aluminium CNC, 6w)
                    </button>
                    <button @click="loadPreset('buyer_b')" class="px-3 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-purple-300 hover:border-purple-500 transition-all">
                        Buyer B (1,500 Stainless Sheet Metal, 6w)
                    </button>
                    <button @click="loadPreset('aerospace')" class="px-3 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-xs font-medium text-amber-300 hover:border-amber-500 transition-all">
                        Aerospace (5,000 Titanium AS9100, 10w)
                    </button>
                </div>
            </div>

            <!-- In-Flight Delta Notification Banner -->
            <template x-if="searchResponse && searchResponse.query_delta_notes && searchResponse.query_delta_notes.length > 0">
                <div class="p-4 rounded-xl bg-amber-950/50 border border-amber-800/80 text-amber-200 text-xs space-y-1">
                    <div class="font-bold flex items-center space-x-1">
                        <span>⚠️ In-Flight Requirement Change Detected:</span>
                    </div>
                    <template x-for="note in searchResponse.query_delta_notes" :key="note">
                        <p class="text-amber-300 pl-4">• <span x-text="note"></span></p>
                    </template>
                </div>
            </template>

            <!-- Main Form & Results Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                <!-- Left Input Controls (4 cols) -->
                <div class="lg:col-span-4 bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-5 h-fit">
                    <div class="border-b border-slate-800 pb-3">
                        <h2 class="text-sm font-bold text-white uppercase tracking-wider">Requirement Parameters</h2>
                        <p class="text-xs text-slate-400">Tweak parameters to trigger real-time re-matching</p>
                    </div>

                    <!-- Session Selector -->
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Buyer Session ID</label>
                        <select x-model="form.session_id" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-emerald-500">
                            <option value="session_german">🇩🇪 session_german (Germany Buyer)</option>
                            <option value="session_buyer_a">🅰️ session_buyer_a (Buyer A)</option>
                            <option value="session_buyer_b">🅱️ session_buyer_b (Buyer B)</option>
                            <option value="session_custom">👤 session_custom (New Session)</option>
                        </select>
                    </div>

                    <!-- Material -->
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Material</label>
                        <select x-model="form.material" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-emerald-500">
                            <option value="aluminium">Aluminium</option>
                            <option value="stainless steel">Stainless Steel</option>
                            <option value="mild steel">Mild Steel</option>
                            <option value="copper">Copper</option>
                            <option value="brass">Brass</option>
                            <option value="titanium">Titanium</option>
                            <option value="cast iron">Cast Iron</option>
                            <option value="ABS">ABS</option>
                            <option value="nylon">Nylon</option>
                        </select>
                    </div>

                    <!-- Process -->
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Manufacturing Process</label>
                        <select x-model="form.process" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-1 focus:ring-emerald-500">
                            <option value="CNC milling">CNC Milling</option>
                            <option value="CNC turning">CNC Turning</option>
                            <option value="machined">Machined to Order (CNC/Grinding)</option>
                            <option value="sheet metal">Sheet Metal Fabrication</option>
                            <option value="casting">Casting</option>
                            <option value="forging">Forging</option>
                            <option value="grinding">Grinding</option>
                            <option value="EDM">EDM (Spark Erosion)</option>
                            <option value="welding">Welding</option>
                            <option value="injection moulding">Injection Moulding</option>
                        </select>
                    </div>

                    <!-- Order Quantity -->
                    <div>
                        <div class="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                            <span>Batch Quantity</span>
                            <span class="text-emerald-400 font-mono" x-text="form.quantity.toLocaleString() + ' units'"></span>
                        </div>
                        <input type="range" min="100" max="10000" step="100" x-model.number="form.quantity" class="w-full accent-emerald-500">
                        <div class="flex justify-between text-[10px] text-slate-500">
                            <span>100</span>
                            <span>2,500</span>
                            <span>5,000</span>
                            <span>10,000</span>
                        </div>
                    </div>

                    <!-- Lead Time Window -->
                    <div>
                        <div class="flex justify-between text-xs font-semibold text-slate-300 mb-1">
                            <span>Delivery Window</span>
                            <span class="text-emerald-400 font-mono" x-text="form.timeline_weeks + ' weeks'"></span>
                        </div>
                        <input type="range" min="2" max="16" step="1" x-model.number="form.timeline_weeks" class="w-full accent-emerald-500">
                        <div class="flex justify-between text-[10px] text-slate-500">
                            <span>2w (Fast)</span>
                            <span>6w (Standard)</span>
                            <span>12w</span>
                            <span>16w</span>
                        </div>
                    </div>

                    <!-- Certifications -->
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Mandatory Certifications</label>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <label class="flex items-center space-x-2 bg-slate-900 p-2 rounded-lg border border-slate-800 cursor-pointer">
                                <input type="checkbox" value="ISO 9001" x-model="form.required_certifications" class="accent-emerald-500">
                                <span>ISO 9001</span>
                            </label>
                            <label class="flex items-center space-x-2 bg-slate-900 p-2 rounded-lg border border-slate-800 cursor-pointer">
                                <input type="checkbox" value="IATF 16949" x-model="form.required_certifications" class="accent-emerald-500">
                                <span>IATF 16949</span>
                            </label>
                            <label class="flex items-center space-x-2 bg-slate-900 p-2 rounded-lg border border-slate-800 cursor-pointer">
                                <input type="checkbox" value="AS9100" x-model="form.required_certifications" class="accent-emerald-500">
                                <span>AS9100</span>
                            </label>
                            <label class="flex items-center space-x-2 bg-slate-900 p-2 rounded-lg border border-slate-800 cursor-pointer">
                                <input type="checkbox" value="ISO 13485" x-model="form.required_certifications" class="accent-emerald-500">
                                <span>ISO 13485</span>
                            </label>
                        </div>
                    </div>

                    <!-- Destination Country -->
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 mb-1">Destination Country</label>
                        <input type="text" x-model="form.destination_country" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white">
                    </div>

                    <button @click="submitMatch()" :disabled="isLoading" class="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-600/20 transition-all flex items-center justify-center space-x-2">
                        <template x-if="isLoading">
                            <span>Processing...</span>
                        </template>
                        <template x-if="!isLoading">
                            <span>⚡ Find & Rank Manufacturers</span>
                        </template>
                    </button>
                </div>

                <!-- Right Match Results (8 cols) -->
                <div class="lg:col-span-8 space-y-6">
                    
                    <!-- Result Summary Stats -->
                    <template x-if="searchResponse">
                        <div class="grid grid-cols-3 gap-4">
                            <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                                <div class="text-[11px] text-slate-400 uppercase font-semibold">Total Evaluated</div>
                                <div class="text-2xl font-black text-white mt-1" x-text="searchResponse.total_manufacturers_evaluated"></div>
                                <div class="text-[10px] text-slate-500 mt-0.5">Indian suppliers evaluated</div>
                            </div>
                            <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                                <div class="text-[11px] text-slate-400 uppercase font-semibold">Eligible Suppliers</div>
                                <div class="text-2xl font-black text-emerald-400 mt-1" x-text="searchResponse.eligible_count"></div>
                                <div class="text-[10px] text-slate-500 mt-0.5">Passed all hard gates</div>
                            </div>
                            <div class="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                                <div class="text-[11px] text-slate-400 uppercase font-semibold">Top Match Score</div>
                                <div class="text-2xl font-black text-teal-400 mt-1" x-text="searchResponse.matches.length > 0 ? searchResponse.matches[0].score_breakdown.total_score + '/100' : 'N/A'"></div>
                                <div class="text-[10px] text-slate-500 mt-0.5">Multi-attribute utility</div>
                            </div>
                        </div>
                    </template>

                    <!-- Match Cards -->
                    <template x-if="searchResponse && searchResponse.matches.length > 0">
                        <div class="space-y-4">
                            <template x-for="(match, idx) in searchResponse.matches" :key="match.manufacturer.manufacturer_id">
                                <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all space-y-4">
                                    <div class="flex items-start justify-between">
                                        <div class="flex items-center space-x-3">
                                            <div class="w-8 h-8 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-300" x-text="'#' + (idx + 1)"></div>
                                            <div>
                                                <h3 class="text-base font-bold text-white flex items-center space-x-2">
                                                    <span x-text="match.manufacturer.name"></span>
                                                    <span class="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-slate-400 font-mono border border-slate-800" x-text="match.manufacturer.manufacturer_id"></span>
                                                </h3>
                                                <p class="text-xs text-slate-400" x-text="match.manufacturer.city + ', ' + match.manufacturer.state_name + ' • Founded ' + match.manufacturer.founded_year + ' • ' + match.manufacturer.company_size + ' Size'"></p>
                                            </div>
                                        </div>

                                        <!-- Big Total Score Badge -->
                                        <div class="text-right">
                                            <div class="text-2xl font-black text-emerald-400 font-mono" x-text="match.score_breakdown.total_score"></div>
                                            <div class="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Match Score</div>
                                        </div>
                                    </div>

                                    <!-- Score Breakdown Progress Bars -->
                                    <div class="grid grid-cols-5 gap-2 pt-2 border-t border-slate-900 text-[10px]">
                                        <div>
                                            <div class="flex justify-between text-slate-400 mb-1">
                                                <span>Speed (30%)</span>
                                                <span class="font-bold text-slate-200" x-text="match.score_breakdown.speed_score"></span>
                                            </div>
                                            <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-emerald-500 h-full" :style="'width: ' + match.score_breakdown.speed_score + '%'"></div>
                                            </div>
                                        </div>
                                        <div>
                                            <div class="flex justify-between text-slate-400 mb-1">
                                                <span>Quality (25%)</span>
                                                <span class="font-bold text-slate-200" x-text="match.score_breakdown.reliability_score"></span>
                                            </div>
                                            <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-teal-500 h-full" :style="'width: ' + match.score_breakdown.reliability_score + '%'"></div>
                                            </div>
                                        </div>
                                        <div>
                                            <div class="flex justify-between text-slate-400 mb-1">
                                                <span>Capacity (20%)</span>
                                                <span class="font-bold text-slate-200" x-text="match.score_breakdown.capacity_score"></span>
                                            </div>
                                            <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-blue-500 h-full" :style="'width: ' + match.score_breakdown.capacity_score + '%'"></div>
                                            </div>
                                        </div>
                                        <div>
                                            <div class="flex justify-between text-slate-400 mb-1">
                                                <span>Export (15%)</span>
                                                <span class="font-bold text-slate-200" x-text="match.score_breakdown.export_score"></span>
                                            </div>
                                            <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-indigo-500 h-full" :style="'width: ' + match.score_breakdown.export_score + '%'"></div>
                                            </div>
                                        </div>
                                        <div>
                                            <div class="flex justify-between text-slate-400 mb-1">
                                                <span>Audit (10%)</span>
                                                <span class="font-bold text-slate-200" x-text="match.score_breakdown.audit_score"></span>
                                            </div>
                                            <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-purple-500 h-full" :style="'width: ' + match.score_breakdown.audit_score + '%'"></div>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Operational Metrics Grid -->
                                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80 text-xs">
                                        <div>
                                            <span class="text-slate-400 block text-[10px]">Lead Time</span>
                                            <span class="font-bold text-white" x-text="match.manufacturer.lead_time_weeks + ' weeks'"></span>
                                            <span class="text-[10px] text-emerald-400 ml-1 font-mono" x-text="'(' + match.explanation.lead_time_margin_weeks + 'w buffer)'"></span>
                                        </div>
                                        <div>
                                            <span class="text-slate-400 block text-[10px]">OTD Performance</span>
                                            <span class="font-bold text-white" x-text="match.manufacturer.on_time_delivery_pct + '%'"></span>
                                            <span class="text-[10px] text-slate-400 ml-1" x-text="'(Rating ' + match.manufacturer.delivery_rating + ')'"></span>
                                        </div>
                                        <div>
                                            <span class="text-slate-400 block text-[10px]">Monthly Capacity</span>
                                            <span class="font-bold text-white" x-text="match.manufacturer.capacity_units_per_month.toLocaleString() + '/mo'"></span>
                                            <span class="text-[10px] text-slate-400 ml-1" x-text="'(' + match.explanation.capacity_utilization_pct + '% load)'"></span>
                                        </div>
                                        <div>
                                            <span class="text-slate-400 block text-[10px]">Export Track Record</span>
                                            <span class="font-bold text-white" x-text="match.manufacturer.export_experience_years + ' years'"></span>
                                        </div>
                                    </div>

                                    <!-- Explanations & Strengths -->
                                    <div class="space-y-1.5 text-xs">
                                        <div class="text-[11px] font-semibold text-slate-300">Why this manufacturer won:</div>
                                        <template x-for="str in match.explanation.key_strengths" :key="str">
                                            <div class="flex items-start space-x-2 text-slate-300">
                                                <span class="text-emerald-400 font-bold">✓</span>
                                                <span x-text="str"></span>
                                            </div>
                                        </template>

                                        <!-- Risks or Watch Items -->
                                        <template x-if="match.explanation.risks_and_tradeoffs.length > 0">
                                            <div class="pt-2">
                                                <template x-for="risk in match.explanation.risks_and_tradeoffs" :key="risk">
                                                    <div class="flex items-start space-x-2 text-amber-300 text-[11px]">
                                                        <span>⚠️</span>
                                                        <span x-text="risk"></span>
                                                    </div>
                                                </template>
                                            </div>
                                        </template>
                                    </div>

                                    <!-- Action Buttons -->
                                    <div class="flex items-center justify-between pt-2 border-t border-slate-900 text-xs">
                                        <div class="text-slate-400">
                                            Certifications: <span class="text-slate-200 font-medium" x-text="match.manufacturer.certifications.join(', ') || 'None'"></span>
                                            <span class="text-slate-500 font-mono ml-1" x-text="'(Expiry: ' + match.manufacturer.certification_expiry + ')'"></span>
                                        </div>
                                        <div class="flex space-x-2">
                                            <button @click="reserveCapacity(match.manufacturer.manufacturer_id, form.quantity)" class="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 hover:border-emerald-500 text-slate-200 text-xs rounded-lg transition-all">
                                                🔒 Soft-Reserve Capacity
                                            </button>
                                            <button @click="generateExecutiveMemo(match)" class="px-3 py-1.5 bg-emerald-700/40 hover:bg-emerald-600/60 border border-emerald-600 text-emerald-200 text-xs rounded-lg transition-all font-semibold">
                                                📄 Executive Memo
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </template>
                        </div>
                    </template>

                    <!-- Zero Matches Fallback (Relaxed Mode) -->
                    <template x-if="searchResponse && searchResponse.matches.length === 0 && searchResponse.relaxed_matches">
                        <div class="bg-red-950/20 border border-red-800 p-6 rounded-2xl space-y-4">
                            <div class="flex items-center space-x-3 text-red-400">
                                <span class="text-xl">⚠️</span>
                                <h3 class="text-sm font-bold uppercase tracking-wider">Zero Candidates Passed 100% of Strict Constraints</h3>
                            </div>
                            <p class="text-xs text-slate-300">
                                Showing closest available manufacturers below, highlighting the exact criteria that disqualified them:
                            </p>
                            <div class="space-y-3">
                                <template x-for="rm in searchResponse.relaxed_matches" :key="rm.manufacturer.manufacturer_id">
                                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs space-y-2">
                                        <div class="flex justify-between font-bold text-white">
                                            <span x-text="rm.manufacturer.name + ' (' + rm.manufacturer.city + ')'"></span>
                                            <span class="text-amber-400" x-text="'Penalized Score: ' + rm.score_breakdown.total_score"></span>
                                        </div>
                                        <div class="space-y-1 text-red-300">
                                            <template x-for="reason in rm.disqualification_reasons" :key="reason">
                                                <div class="flex items-center space-x-1.5">
                                                    <span>❌</span>
                                                    <span x-text="reason"></span>
                                                </div>
                                            </template>
                                        </div>
                                    </div>
                                </template>
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <!-- TAB 2: AI RFQ PARSER -->
        <div x-show="activeTab === 'nlp'" class="max-w-4xl mx-auto space-y-6">
            <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-4">
                <div>
                    <h2 class="text-base font-bold text-white">Natural Language Procurement RFQ Parser</h2>
                    <p class="text-xs text-slate-400 mt-1">Paste unstructured buyer emails or RFQ briefs in plain text. The AI service extracts specifications, maps canonical terms, and finds matches.</p>
                </div>

                <textarea x-model="nlpText" rows="5" class="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 text-xs text-slate-100 font-mono focus:ring-1 focus:ring-emerald-500" placeholder="e.g. We are an engineering firm in Stuttgart, Germany. We urgently need 2,500 milled aluminium brackets. Must be ISO 9001 certified. We need them on our dock within 7 weeks. Can you recommend reliable suppliers?"></textarea>

                <div class="flex justify-between items-center">
                    <span class="text-xs text-slate-500">Supports German/English terms, informal quantities ('a few thousand'), and colloquial processes ('machined').</span>
                    <button @click="submitNlp()" :disabled="isLoading" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-600/20 transition-all">
                        🤖 Extract Specifications & Match
                    </button>
                </div>
            </div>

            <!-- Parsed Parameters Preview -->
            <template x-if="searchResponse && activeTab === 'nlp'">
                <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-4">
                    <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400">Extracted Structured Schema:</h3>
                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                        <div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                            <span class="text-slate-400 block text-[10px]">Material</span>
                            <span class="font-bold text-white" x-text="searchResponse.requirement.material"></span>
                        </div>
                        <div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                            <span class="text-slate-400 block text-[10px]">Process</span>
                            <span class="font-bold text-white" x-text="searchResponse.requirement.process"></span>
                        </div>
                        <div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                            <span class="text-slate-400 block text-[10px]">Batch Quantity</span>
                            <span class="font-bold text-white" x-text="searchResponse.requirement.quantity.toLocaleString() + ' units'"></span>
                        </div>
                        <div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                            <span class="text-slate-400 block text-[10px]">Timeline</span>
                            <span class="font-bold text-white" x-text="searchResponse.requirement.timeline_weeks + ' weeks'"></span>
                        </div>
                    </div>
                </div>
            </template>
        </div>

        <!-- TAB 3: BUYER A VS BUYER B CONTENTION SIMULATOR -->
        <div x-show="activeTab === 'contention'" class="space-y-6">
            <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-4">
                <div class="flex items-center justify-between">
                    <div>
                        <h2 class="text-base font-bold text-white">Simultaneous Buyer Contention Resolution</h2>
                        <p class="text-xs text-slate-400 mt-1">Prompt Scenario: Buyer A (1,000 Aluminium CNC, 6w) and Buyer B (1,500 Stainless Sheet-Metal, 6w) arrive at the exact same moment.</p>
                    </div>
                    <div class="flex space-x-2">
                        <button @click="runContention('pareto_optimal')" :class="contentionStrategy === 'pareto_optimal' ? 'bg-emerald-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-700'" class="px-4 py-2 text-xs rounded-xl font-bold transition-all">
                            🌟 Pareto Optimal (Global Welfare)
                        </button>
                        <button @click="runContention('fcfs')" :class="contentionStrategy === 'fcfs' ? 'bg-emerald-600 text-white' : 'bg-slate-900 text-slate-400 border border-slate-700'" class="px-4 py-2 text-xs rounded-xl font-bold transition-all">
                            ⏱️ First-Come First-Served (FCFS)
                        </button>
                    </div>
                </div>
            </div>

            <template x-if="contentionResponse">
                <div class="space-y-6">
                    <!-- Operational Resolution Banner -->
                    <div class="p-6 rounded-2xl border text-xs space-y-2" :class="contentionResponse.conflict_detected ? 'bg-amber-950/40 border-amber-800 text-amber-200' : 'bg-emerald-950/40 border-emerald-800 text-emerald-200'">
                        <div class="font-bold text-sm uppercase flex items-center space-x-2">
                            <span>Strategy:</span>
                            <span class="font-mono" x-text="contentionResponse.resolution_strategy.toUpperCase()"></span>
                        </div>
                        <p class="leading-relaxed" x-text="contentionResponse.explanation"></p>
                    </div>

                    <!-- Side-by-Side Allocations -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        
                        <!-- Buyer A Card -->
                        <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-4">
                            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                                <div>
                                    <span class="text-xs font-bold text-blue-400 font-mono">BUYER A ALLOCATION</span>
                                    <h3 class="text-base font-bold text-white mt-1">1,000 Aluminium CNC Parts</h3>
                                    <p class="text-xs text-slate-400">Timeline: 6 weeks • ISO 9001</p>
                                </div>
                                <div class="text-right">
                                    <div class="text-2xl font-black text-blue-400 font-mono" x-text="contentionResponse.buyer_a_allocated.score_breakdown.total_score"></div>
                                    <span class="text-[10px] text-slate-500 uppercase font-bold">Match Score</span>
                                </div>
                            </div>
                            <div class="space-y-2 text-xs">
                                <div class="font-bold text-white" x-text="contentionResponse.buyer_a_allocated.manufacturer.name"></div>
                                <div class="text-slate-400" x-text="contentionResponse.buyer_a_allocated.manufacturer.city + ', ' + contentionResponse.buyer_a_allocated.manufacturer.state_name"></div>
                                <div class="grid grid-cols-3 gap-2 bg-slate-900 p-3 rounded-xl border border-slate-800 text-[11px]">
                                    <div>
                                        <span class="text-slate-500 block">Lead Time</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_a_allocated.manufacturer.lead_time_weeks + 'w'"></span>
                                    </div>
                                    <div>
                                        <span class="text-slate-500 block">OTD</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_a_allocated.manufacturer.on_time_delivery_pct + '%'"></span>
                                    </div>
                                    <div>
                                        <span class="text-slate-500 block">Monthly Cap</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_a_allocated.manufacturer.capacity_units_per_month.toLocaleString()"></span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Buyer B Card -->
                        <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-4">
                            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                                <div>
                                    <span class="text-xs font-bold text-purple-400 font-mono">BUYER B ALLOCATION</span>
                                    <h3 class="text-base font-bold text-white mt-1">1,500 Stainless Sheet-Metal Parts</h3>
                                    <p class="text-xs text-slate-400">Timeline: 6 weeks • ISO 9001</p>
                                </div>
                                <div class="text-right">
                                    <div class="text-2xl font-black text-purple-400 font-mono" x-text="contentionResponse.buyer_b_allocated.score_breakdown.total_score"></div>
                                    <span class="text-[10px] text-slate-500 uppercase font-bold">Match Score</span>
                                </div>
                            </div>
                            <div class="space-y-2 text-xs">
                                <div class="font-bold text-white" x-text="contentionResponse.buyer_b_allocated.manufacturer.name"></div>
                                <div class="text-slate-400" x-text="contentionResponse.buyer_b_allocated.manufacturer.city + ', ' + contentionResponse.buyer_b_allocated.manufacturer.state_name"></div>
                                <div class="grid grid-cols-3 gap-2 bg-slate-900 p-3 rounded-xl border border-slate-800 text-[11px]">
                                    <div>
                                        <span class="text-slate-500 block">Lead Time</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_b_allocated.manufacturer.lead_time_weeks + 'w'"></span>
                                    </div>
                                    <div>
                                        <span class="text-slate-500 block">OTD</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_b_allocated.manufacturer.on_time_delivery_pct + '%'"></span>
                                    </div>
                                    <div>
                                        <span class="text-slate-500 block">Monthly Cap</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_b_allocated.manufacturer.capacity_units_per_month.toLocaleString()"></span>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </template>
        </div>

        <!-- TAB 4: DATA QUALITY AUDIT -->
        <div x-show="activeTab === 'audit'" class="space-y-6">
            <div class="bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-4">
                <div class="flex justify-between items-center">
                    <div>
                        <h2 class="text-base font-bold text-white">Dataset Sanitation & Data Quality Audit</h2>
                        <p class="text-xs text-slate-400 mt-1">40 deliberate anomalies identified and sanitized across the 1,000 mock manufacturer records.</p>
                    </div>
                    <span class="text-xs font-mono px-3 py-1 bg-emerald-950 border border-emerald-800 text-emerald-400 rounded-lg">40 Anomalies Cleaned</span>
                </div>

                <!-- Table of Cleaned Records -->
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-900 text-slate-400 font-semibold uppercase text-[10px] border-b border-slate-800">
                            <tr>
                                <th class="p-3">Surrogate ID</th>
                                <th class="p-3">Manufacturer</th>
                                <th class="p-3">City / State</th>
                                <th class="p-3">Process</th>
                                <th class="p-3">OTD (Raw -> Clamped)</th>
                                <th class="p-3">Lead Time</th>
                                <th class="p-3">Sanitation Action</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-800/60 font-mono text-[11px]">
                            <template x-for="item in auditList" :key="item.manufacturer_id">
                                <tr class="hover:bg-slate-900/40">
                                    <td class="p-3 text-emerald-400 font-bold" x-text="item.manufacturer_id"></td>
                                    <td class="p-3 font-sans font-medium text-white" x-text="item.name"></td>
                                    <td class="p-3 font-sans text-slate-400" x-text="item.city + ', ' + item.state"></td>
                                    <td class="p-3 text-slate-300" x-text="item.primary_process"></td>
                                    <td class="p-3">
                                        <template x-if="item.raw_on_time_delivery_pct > 100">
                                            <span class="text-amber-400" x-text="item.raw_on_time_delivery_pct + '% -> 100.0%'"></span>
                                        </template>
                                        <template x-if="item.raw_on_time_delivery_pct <= 100">
                                            <span class="text-slate-400" x-text="item.on_time_delivery_pct + '%'"></span>
                                        </template>
                                    </td>
                                    <td class="p-3 text-slate-300" x-text="item.lead_time_weeks + 'w'"></td>
                                    <td class="p-3 font-sans text-[10px] text-emerald-300" x-text="item.flags.join('; ')"></td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

    </main>

    <!-- Executive Memo Modal -->
    <div x-show="memoModalOpen" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" style="display: none;">
        <div class="bg-slate-950 border border-slate-800 max-w-2xl w-full p-6 rounded-2xl space-y-4 max-h-[85vh] overflow-y-auto" @click.away="memoModalOpen = false">
            <div class="flex justify-between items-center border-b border-slate-800 pb-3">
                <h3 class="text-sm font-bold text-white uppercase tracking-wider">Executive Procurement Memorandum</h3>
                <button @click="memoModalOpen = false" class="text-slate-400 hover:text-white text-lg">&times;</button>
            </div>
            <div class="text-xs text-slate-300 whitespace-pre-line font-mono bg-slate-900 p-4 rounded-xl border border-slate-800 leading-relaxed" x-text="currentMemoText"></div>
            <div class="flex justify-end">
                <button @click="memoModalOpen = false" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl transition-all">Close Memorandum</button>
            </div>
        </div>
    </div>

    <!-- Alpine App Logic -->
    <script>
        function veridiaApp() {
            return {
                activeTab: 'finder',
                isLoading: false,
                memoModalOpen: false,
                currentMemoText: '',
                contentionStrategy: 'pareto_optimal',
                nlpText: 'Hi Veridia team, we are an engineering firm in Stuttgart, Germany. We urgently need 2,500 milled aluminium brackets. Must be ISO 9001 certified. We need them on our dock within 7 weeks. Can you recommend reliable suppliers?',
                form: {
                    session_id: 'session_german',
                    buyer_name: 'German Precision Buyer',
                    material: 'aluminium',
                    process: 'machined',
                    quantity: 2000,
                    timeline_weeks: 6,
                    required_certifications: ['ISO 9001'],
                    destination_country: 'Germany'
                },
                searchResponse: null,
                contentionResponse: null,
                auditList: [],

                async initApp() {
                    await this.submitMatch();
                    await this.loadAuditData();
                    await this.runContention('pareto_optimal');
                },

                loadPreset(type) {
                    if (type === 'german') {
                        this.form = {
                            session_id: 'session_german',
                            buyer_name: 'German Industrial Buyer',
                            material: 'aluminium',
                            process: 'machined',
                            quantity: 2000,
                            timeline_weeks: 6,
                            required_certifications: ['ISO 9001'],
                            destination_country: 'Germany'
                        };
                    } else if (type === 'buyer_a') {
                        this.form = {
                            session_id: 'session_buyer_a',
                            buyer_name: 'Buyer A (Prompt Scenario)',
                            material: 'aluminium',
                            process: 'CNC milling',
                            quantity: 1000,
                            timeline_weeks: 6,
                            required_certifications: ['ISO 9001'],
                            destination_country: 'Germany'
                        };
                    } else if (type === 'buyer_b') {
                        this.form = {
                            session_id: 'session_buyer_b',
                            buyer_name: 'Buyer B (Prompt Scenario)',
                            material: 'stainless steel',
                            process: 'sheet metal',
                            quantity: 1500,
                            timeline_weeks: 6,
                            required_certifications: ['ISO 9001'],
                            destination_country: 'Germany'
                        };
                    } else if (type === 'aerospace') {
                        this.form = {
                            session_id: 'session_aerospace',
                            buyer_name: 'Aerospace Systems Corp',
                            material: 'titanium',
                            process: 'CNC milling',
                            quantity: 5000,
                            timeline_weeks: 10,
                            required_certifications: ['AS9100'],
                            destination_country: 'USA'
                        };
                    }
                    this.submitMatch();
                },

                async submitMatch() {
                    this.isLoading = true;
                    try {
                        const res = await fetch('/api/match', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this.form)
                        });
                        if (res.ok) {
                            this.searchResponse = await res.json();
                        } else {
                            const err = await res.json();
                            alert('Match failed: ' + err.detail);
                        }
                    } catch (e) {
                        console.error(e);
                    } finally {
                        this.isLoading = false;
                    }
                },

                async submitNlp() {
                    this.isLoading = true;
                    try {
                        const res = await fetch('/api/parse-and-match', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ text: this.nlpText, session_id: 'nlp-session' })
                        });
                        if (res.ok) {
                            this.searchResponse = await res.json();
                            this.activeTab = 'finder';
                        }
                    } catch (e) {
                        console.error(e);
                    } finally {
                        this.isLoading = false;
                    }
                },

                async runContention(strategy) {
                    this.contentionStrategy = strategy;
                    const reqA = {
                        session_id: 'session_buyer_a',
                        buyer_name: 'Buyer A',
                        material: 'aluminium',
                        process: 'CNC',
                        quantity: 1000,
                        timeline_weeks: 6,
                        required_certifications: ['ISO 9001']
                    };
                    const reqB = {
                        session_id: 'session_buyer_b',
                        buyer_name: 'Buyer B',
                        material: 'stainless steel',
                        process: 'sheet metal',
                        quantity: 1500,
                        timeline_weeks: 6,
                        required_certifications: ['ISO 9001']
                    };

                    try {
                        const res = await fetch('/api/simulate-contention', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                buyer_a: reqA,
                                buyer_b: reqB,
                                resolution_strategy: strategy
                            })
                        });
                        if (res.ok) {
                            this.contentionResponse = await res.json();
                        }
                    } catch (e) {
                        console.error(e);
                    }
                },

                async loadAuditData() {
                    try {
                        const res = await fetch('/api/audit-data');
                        if (res.ok) {
                            const data = await res.json();
                            this.auditList = data.anomalies;
                        }
                    } catch (e) {
                        console.error(e);
                    }
                },

                async reserveCapacity(mfgId, qty) {
                    try {
                        const res = await fetch('/api/reserve', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                session_id: this.form.session_id,
                                manufacturer_id: mfgId,
                                units: qty
                            })
                        });
                        const data = await res.json();
                        alert(data.message + ' (Remaining capacity: ' + data.remaining_monthly_capacity.toLocaleString() + ' units)');
                        this.submitMatch();
                    } catch (e) {
                        alert('Reservation failed');
                    }
                },

                async generateExecutiveMemo(match) {
                    try {
                        const res = await fetch('/api/executive-pitch', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                requirement: this.form,
                                match: match
                            })
                        });
                        if (res.ok) {
                            const data = await res.json();
                            this.currentMemoText = data.pitch;
                            this.memoModalOpen = true;
                        }
                    } catch (e) {
                        alert('Failed to generate memo');
                    }
                }
            };
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serves the complete interactive procurement dashboard."""
    return HTMLResponse(content=HTML_DASHBOARD)

def start_server(host: str = "127.0.0.1", port: int = 8000):
    """Starts the uvicorn web server."""
    logger.info(f"Starting Veridia Matching Dashboard on http://{host}:{port}")
    uvicorn.run("src.app:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    start_server()
