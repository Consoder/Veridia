"""
Interactive Web Application & REST API for Veridia Manufacturer Matching System
FastAPI backend with a world-class, enterprise-grade dark-mode procurement dashboard.
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
    description="Enterprise-grade precision engineering supplier matching engine.",
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
# World-Class Enterprise Procurement Dashboard UI
# ---------------------------------------------------------

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VERIDIA | Precision Engineering Supply Chain Intelligence</title>
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    },
                    colors: {
                        brand: {
                            50: '#ecfdf5',
                            500: '#10b981',
                            600: '#059669',
                            700: '#047857',
                            900: '#064e3b',
                            950: '#022c22'
                        },
                        obsidian: '#090a0f',
                        surface: '#0f111a',
                        card: '#141824',
                        border: 'rgba(255, 255, 255, 0.08)'
                    }
                }
            }
        }
    </script>
    <!-- Alpine.js -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        body {
            background-color: #090a0f;
            background-image: 
                radial-gradient(at 0% 0%, rgba(16, 185, 129, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(59, 130, 246, 0.06) 0px, transparent 50%),
                radial-gradient(at 50% 0%, rgba(139, 92, 246, 0.04) 0px, transparent 50%);
            background-attachment: fixed;
        }
        .glass-panel {
            background: rgba(20, 24, 36, 0.75);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.07);
        }
        .glass-card {
            background: rgba(20, 24, 36, 0.6);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.06);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .glass-card:hover {
            border-color: rgba(16, 185, 129, 0.35);
            box-shadow: 0 12px 32px -8px rgba(16, 185, 129, 0.12);
            transform: translateY(-2px);
        }
        /* Custom styled Range Inputs */
        input[type=range] {
            -webkit-appearance: none;
            background: rgba(255, 255, 255, 0.1);
            height: 6px;
            border-radius: 9999px;
        }
        input[type=range]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #10b981;
            cursor: pointer;
            box-shadow: 0 0 12px rgba(16, 185, 129, 0.6);
            border: 2px solid #ffffff;
            transition: transform 0.1s;
        }
        input[type=range]::-webkit-slider-thumb:hover {
            transform: scale(1.2);
        }
        .score-circle {
            transform: rotate(-90deg);
            transform-origin: 50% 50%;
        }
    </style>
</head>
<body class="text-slate-100 min-h-screen antialiased selection:bg-brand-500 selection:text-black" x-data="veridiaApp()" x-init="initApp()">

    <!-- Premium Top Navigation Bar -->
    <header class="border-b border-white/[0.08] bg-[#090a0f]/80 backdrop-blur-xl sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
            
            <!-- Brand Logo & Identity -->
            <div class="flex items-center space-x-4">
                <div class="relative flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 shadow-lg shadow-emerald-500/25 p-[1px]">
                    <div class="w-full h-full bg-[#090a0f] rounded-[11px] flex items-center justify-center font-black text-emerald-400 text-2xl tracking-tighter">
                        V
                    </div>
                </div>
                <div>
                    <div class="flex items-center space-x-2.5">
                        <span class="text-xl font-extrabold tracking-tight text-white font-sans">VERIDIA</span>
                        <span class="px-2 py-0.5 text-[10px] font-mono font-semibold tracking-wide uppercase bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">
                            Enterprise Engine v1.0
                        </span>
                    </div>
                    <p class="text-xs text-slate-400 tracking-tight font-medium">Precision Manufacturing Matchmaker • India to Global</p>
                </div>
            </div>

            <!-- Segmented Tab Navigation -->
            <nav class="flex items-center space-x-1 p-1.5 rounded-2xl bg-white/[0.03] border border-white/[0.06] backdrop-blur-md">
                <button @click="activeTab = 'finder'" :class="activeTab === 'finder' ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-600/25 font-semibold' : 'text-slate-400 hover:text-white hover:bg-white/[0.03]'" class="flex items-center space-x-2 px-4 py-2 text-xs rounded-xl transition-all">
                    <i data-lucide="crosshair" class="w-4 h-4"></i>
                    <span>Interactive Matcher</span>
                </button>
                <button @click="activeTab = 'nlp'" :class="activeTab === 'nlp' ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-600/25 font-semibold' : 'text-slate-400 hover:text-white hover:bg-white/[0.03]'" class="flex items-center space-x-2 px-4 py-2 text-xs rounded-xl transition-all">
                    <i data-lucide="sparkles" class="w-4 h-4 text-emerald-300"></i>
                    <span>AI RFQ Parser</span>
                </button>
                <button @click="activeTab = 'contention'" :class="activeTab === 'contention' ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-600/25 font-semibold' : 'text-slate-400 hover:text-white hover:bg-white/[0.03]'" class="flex items-center space-x-2 px-4 py-2 text-xs rounded-xl transition-all">
                    <i data-lucide="split" class="w-4 h-4"></i>
                    <span>Buyer A vs B Contention</span>
                </button>
                <button @click="activeTab = 'audit'" :class="activeTab === 'audit' ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-600/25 font-semibold' : 'text-slate-400 hover:text-white hover:bg-white/[0.03]'" class="flex items-center space-x-2 px-4 py-2 text-xs rounded-xl transition-all">
                    <i data-lucide="shield-alert" class="w-4 h-4"></i>
                    <span>Data Audit (40)</span>
                </button>
            </nav>

            <!-- Status Pill & Evaluation Anchor -->
            <div class="hidden md:flex items-center space-x-3 bg-white/[0.03] border border-white/[0.06] px-3.5 py-1.5 rounded-full text-xs font-mono">
                <span class="flex h-2 w-2 relative">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span class="text-slate-400">Anchor:</span>
                <span class="text-emerald-300 font-bold">2026-10-28</span>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        <!-- ================================================================= -->
        <!-- TAB 1: INTERACTIVE MATCHER -->
        <!-- ================================================================= -->
        <div x-show="activeTab === 'finder'" class="space-y-6">

            <!-- Quick Scenario Launchpad -->
            <div class="glass-panel p-5 rounded-3xl border border-white/[0.08] shadow-2xl">
                <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div class="flex items-center space-x-3">
                        <div class="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-emerald-400">
                            <i data-lucide="zap" class="w-5 h-5"></i>
                        </div>
                        <div>
                            <h3 class="text-sm font-bold text-white tracking-tight">Assignment Test Scenarios</h3>
                            <p class="text-xs text-slate-400">Instantly execute the primary test personas requested in the brief:</p>
                        </div>
                    </div>

                    <div class="flex flex-wrap gap-2.5">
                        <button @click="loadPreset('german')" class="px-4 py-2 bg-white/[0.04] hover:bg-emerald-500/10 border border-white/[0.08] hover:border-emerald-500/40 rounded-xl text-xs font-medium text-emerald-300 transition-all flex items-center space-x-2 group">
                            <span>🇩🇪 German Buyer (2k Aluminium CNC, 6w)</span>
                            <i data-lucide="arrow-right" class="w-3.5 h-3.5 text-slate-500 group-hover:translate-x-0.5 transition-transform"></i>
                        </button>
                        <button @click="loadPreset('buyer_a')" class="px-4 py-2 bg-white/[0.04] hover:bg-blue-500/10 border border-white/[0.08] hover:border-blue-500/40 rounded-xl text-xs font-medium text-blue-300 transition-all flex items-center space-x-2 group">
                            <span>Buyer A (1k Aluminium CNC, 6w)</span>
                            <i data-lucide="arrow-right" class="w-3.5 h-3.5 text-slate-500 group-hover:translate-x-0.5 transition-transform"></i>
                        </button>
                        <button @click="loadPreset('buyer_b')" class="px-4 py-2 bg-white/[0.04] hover:bg-purple-500/10 border border-white/[0.08] hover:border-purple-500/40 rounded-xl text-xs font-medium text-purple-300 transition-all flex items-center space-x-2 group">
                            <span>Buyer B (1.5k Sheet Metal, 6w)</span>
                            <i data-lucide="arrow-right" class="w-3.5 h-3.5 text-slate-500 group-hover:translate-x-0.5 transition-transform"></i>
                        </button>
                        <button @click="loadPreset('aerospace')" class="px-4 py-2 bg-white/[0.04] hover:bg-amber-500/10 border border-white/[0.08] hover:border-amber-500/40 rounded-xl text-xs font-medium text-amber-300 transition-all flex items-center space-x-2 group">
                            <span>Aerospace (5k Titanium AS9100)</span>
                            <i data-lucide="arrow-right" class="w-3.5 h-3.5 text-slate-500 group-hover:translate-x-0.5 transition-transform"></i>
                        </button>
                    </div>
                </div>
            </div>

            <!-- In-Flight Delta Alert Banner -->
            <template x-if="searchResponse && searchResponse.query_delta_notes && searchResponse.query_delta_notes.length > 0">
                <div class="glass-panel p-5 rounded-2xl border border-amber-500/30 bg-amber-500/[0.04] shadow-xl flex items-start space-x-4">
                    <div class="p-2 bg-amber-500/10 rounded-xl text-amber-400 mt-0.5">
                        <i data-lucide="refresh-cw" class="w-5 h-5"></i>
                    </div>
                    <div class="space-y-1.5 flex-1">
                        <div class="flex items-center space-x-2">
                            <span class="text-xs font-extrabold uppercase tracking-wider text-amber-400">In-Flight Requirement Delta Detected</span>
                            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">Live Recalculation</span>
                        </div>
                        <template x-for="note in searchResponse.query_delta_notes" :key="note">
                            <p class="text-xs text-amber-200/90 flex items-center space-x-2">
                                <span class="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block"></span>
                                <span x-text="note"></span>
                            </p>
                        </template>
                    </div>
                </div>
            </template>

            <!-- Main Layout: Left Controls, Right Results -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                
                <!-- Left Input Panel (4 Cols) -->
                <div class="lg:col-span-4 glass-panel p-6 rounded-3xl border border-white/[0.08] space-y-6 shadow-2xl">
                    <div class="flex items-center justify-between pb-4 border-b border-white/[0.08]">
                        <div class="flex items-center space-x-2.5">
                            <i data-lucide="sliders" class="w-4 h-4 text-emerald-400"></i>
                            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-300">Procurement Controls</h2>
                        </div>
                        <span class="text-[10px] font-mono text-slate-500 bg-white/[0.04] px-2 py-0.5 rounded border border-white/[0.06]" x-text="form.session_id"></span>
                    </div>

                    <!-- Material Selector -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold text-slate-300 tracking-wide">Target Material</label>
                        <div class="relative">
                            <select x-model="form.material" @change="submitMatch()" class="w-full bg-[#0d1017] border border-white/[0.1] rounded-xl px-4 py-3 text-xs text-white appearance-none focus:outline-none focus:border-emerald-500 font-medium">
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
                            <i data-lucide="chevron-down" class="w-4 h-4 text-slate-400 absolute right-3.5 top-3.5 pointer-events-none"></i>
                        </div>
                    </div>

                    <!-- Process Selector -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold text-slate-300 tracking-wide">Manufacturing Process</label>
                        <div class="relative">
                            <select x-model="form.process" @change="submitMatch()" class="w-full bg-[#0d1017] border border-white/[0.1] rounded-xl px-4 py-3 text-xs text-white appearance-none focus:outline-none focus:border-emerald-500 font-medium">
                                <option value="CNC milling">CNC Milling (3 & 5 Axis)</option>
                                <option value="CNC turning">CNC Turning (Lathe)</option>
                                <option value="machined">Machined to Order (General CNC/Grinding)</option>
                                <option value="sheet metal">Sheet Metal Fabrication / Stamping</option>
                                <option value="casting">Precision Casting</option>
                                <option value="forging">Hot & Cold Forging</option>
                                <option value="grinding">Precision Grinding</option>
                                <option value="EDM">Wire / Spark EDM</option>
                                <option value="welding">TIG / MIG Welding</option>
                                <option value="injection moulding">Injection Moulding</option>
                            </select>
                            <i data-lucide="chevron-down" class="w-4 h-4 text-slate-400 absolute right-3.5 top-3.5 pointer-events-none"></i>
                        </div>
                    </div>

                    <!-- Quantity Slider -->
                    <div class="space-y-2.5 bg-white/[0.02] p-4 rounded-2xl border border-white/[0.04]">
                        <div class="flex justify-between items-center text-xs">
                            <span class="font-bold text-slate-300">Batch Order Quantity</span>
                            <span class="font-mono text-emerald-400 font-extrabold text-sm bg-emerald-500/10 px-2.5 py-0.5 rounded-lg border border-emerald-500/20" x-text="form.quantity.toLocaleString() + ' units'"></span>
                        </div>
                        <input type="range" min="100" max="10000" step="100" x-model.number="form.quantity" @input="submitMatch()" class="w-full accent-emerald-500 cursor-pointer">
                        <div class="flex justify-between text-[10px] text-slate-500 font-mono">
                            <span>100</span>
                            <span>2,500</span>
                            <span>5,000</span>
                            <span>10,000</span>
                        </div>
                    </div>

                    <!-- Timeline Slider -->
                    <div class="space-y-2.5 bg-white/[0.02] p-4 rounded-2xl border border-white/[0.04]">
                        <div class="flex justify-between items-center text-xs">
                            <span class="font-bold text-slate-300">Delivery Deadline Window</span>
                            <span class="font-mono text-emerald-400 font-extrabold text-sm bg-emerald-500/10 px-2.5 py-0.5 rounded-lg border border-emerald-500/20" x-text="form.timeline_weeks + ' weeks'"></span>
                        </div>
                        <input type="range" min="2" max="16" step="1" x-model.number="form.timeline_weeks" @input="submitMatch()" class="w-full accent-emerald-500 cursor-pointer">
                        <div class="flex justify-between text-[10px] text-slate-500 font-mono">
                            <span>2w (Express)</span>
                            <span>6w (Standard)</span>
                            <span>12w</span>
                            <span>16w</span>
                        </div>
                    </div>

                    <!-- Certifications Selector -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold text-slate-300 tracking-wide">Mandatory Quality Certifications</label>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <label class="flex items-center space-x-2 bg-white/[0.03] hover:bg-white/[0.06] p-2.5 rounded-xl border border-white/[0.08] cursor-pointer transition-colors" :class="form.required_certifications.includes('ISO 9001') ? 'border-emerald-500/50 bg-emerald-500/[0.06]' : ''">
                                <input type="checkbox" value="ISO 9001" x-model="form.required_certifications" @change="submitMatch()" class="accent-emerald-500 rounded">
                                <span class="font-semibold text-slate-200">ISO 9001</span>
                            </label>
                            <label class="flex items-center space-x-2 bg-white/[0.03] hover:bg-white/[0.06] p-2.5 rounded-xl border border-white/[0.08] cursor-pointer transition-colors" :class="form.required_certifications.includes('IATF 16949') ? 'border-emerald-500/50 bg-emerald-500/[0.06]' : ''">
                                <input type="checkbox" value="IATF 16949" x-model="form.required_certifications" @change="submitMatch()" class="accent-emerald-500 rounded">
                                <span class="font-semibold text-slate-200">IATF 16949</span>
                            </label>
                            <label class="flex items-center space-x-2 bg-white/[0.03] hover:bg-white/[0.06] p-2.5 rounded-xl border border-white/[0.08] cursor-pointer transition-colors" :class="form.required_certifications.includes('AS9100') ? 'border-emerald-500/50 bg-emerald-500/[0.06]' : ''">
                                <input type="checkbox" value="AS9100" x-model="form.required_certifications" @change="submitMatch()" class="accent-emerald-500 rounded">
                                <span class="font-semibold text-slate-200">AS9100</span>
                            </label>
                            <label class="flex items-center space-x-2 bg-white/[0.03] hover:bg-white/[0.06] p-2.5 rounded-xl border border-white/[0.08] cursor-pointer transition-colors" :class="form.required_certifications.includes('ISO 13485') ? 'border-emerald-500/50 bg-emerald-500/[0.06]' : ''">
                                <input type="checkbox" value="ISO 13485" x-model="form.required_certifications" @change="submitMatch()" class="accent-emerald-500 rounded">
                                <span class="font-semibold text-slate-200">ISO 13485</span>
                            </label>
                        </div>
                    </div>

                    <!-- Destination Country -->
                    <div class="space-y-2">
                        <label class="block text-xs font-bold text-slate-300 tracking-wide">Destination Country</label>
                        <div class="relative">
                            <input type="text" x-model="form.destination_country" @change="submitMatch()" class="w-full bg-[#0d1017] border border-white/[0.1] rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500 font-medium">
                            <i data-lucide="globe" class="w-4 h-4 text-slate-500 absolute right-3.5 top-3 pointer-events-none"></i>
                        </div>
                    </div>

                    <button @click="submitMatch()" :disabled="isLoading" class="w-full py-3.5 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-extrabold text-xs rounded-xl shadow-lg shadow-emerald-500/25 transition-all flex items-center justify-center space-x-2">
                        <template x-if="isLoading">
                            <div class="flex items-center space-x-2">
                                <svg class="animate-spin h-4 w-4 text-slate-950" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
                                <span>Evaluating 1,000 Factories...</span>
                            </div>
                        </template>
                        <template x-if="!isLoading">
                            <div class="flex items-center space-x-2">
                                <i data-lucide="filter" class="w-4 h-4"></i>
                                <span>Re-Rank Manufacturers</span>
                            </div>
                        </template>
                    </button>
                </div>

                <!-- Right Match Results Panel (8 Cols) -->
                <div class="lg:col-span-8 space-y-6">

                    <!-- Metric Counters Bar -->
                    <template x-if="searchResponse">
                        <div class="grid grid-cols-3 gap-4">
                            <div class="glass-panel p-5 rounded-3xl border border-white/[0.08] relative overflow-hidden">
                                <div class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Universe Evaluated</div>
                                <div class="text-3xl font-extrabold text-white mt-1.5 font-sans" x-text="searchResponse.total_manufacturers_evaluated"></div>
                                <div class="text-xs text-slate-500 mt-1 flex items-center space-x-1">
                                    <i data-lucide="database" class="w-3.5 h-3.5"></i>
                                    <span>Precision Indian suppliers</span>
                                </div>
                            </div>
                            <div class="glass-panel p-5 rounded-3xl border border-white/[0.08] relative overflow-hidden">
                                <div class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Strictly Eligible</div>
                                <div class="text-3xl font-extrabold text-emerald-400 mt-1.5 font-sans" x-text="searchResponse.eligible_count"></div>
                                <div class="text-xs text-emerald-500/80 mt-1 flex items-center space-x-1">
                                    <i data-lucide="check-circle" class="w-3.5 h-3.5"></i>
                                    <span>Passed 100% hard gates</span>
                                </div>
                            </div>
                            <div class="glass-panel p-5 rounded-3xl border border-white/[0.08] relative overflow-hidden">
                                <div class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Top Match Score</div>
                                <div class="text-3xl font-extrabold text-teal-300 mt-1.5 font-sans" x-text="searchResponse.matches.length > 0 ? searchResponse.matches[0].score_breakdown.total_score + '/100' : 'N/A'"></div>
                                <div class="text-xs text-teal-500/80 mt-1 flex items-center space-x-1">
                                    <i data-lucide="award" class="w-3.5 h-3.5"></i>
                                    <span>Multi-attribute utility</span>
                                </div>
                            </div>
                        </div>
                    </template>

                    <!-- Manufacturer Cards List -->
                    <template x-if="searchResponse && searchResponse.matches.length > 0">
                        <div class="space-y-5">
                            <template x-for="(match, idx) in searchResponse.matches" :key="match.manufacturer.manufacturer_id">
                                <div class="glass-card p-6 rounded-3xl relative overflow-hidden group">
                                    
                                    <!-- Top Card Header: Rank, Name, Score Dial -->
                                    <div class="flex items-start justify-between gap-4">
                                        <div class="flex items-start space-x-4">
                                            <!-- Rank Badge -->
                                            <div class="w-10 h-10 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center font-mono font-bold text-sm text-emerald-400 group-hover:border-emerald-500/40 group-hover:bg-emerald-500/10 transition-colors" x-text="'#' + (idx + 1)"></div>
                                            
                                            <div>
                                                <div class="flex items-center space-x-2.5">
                                                    <h3 class="text-base font-bold text-white tracking-tight" x-text="match.manufacturer.name"></h3>
                                                    <span class="px-2 py-0.5 text-[10px] font-mono bg-white/[0.04] text-slate-400 rounded-lg border border-white/[0.06]" x-text="match.manufacturer.manufacturer_id"></span>
                                                    <!-- Data Quality Anomaly Tag if cleaned -->
                                                    <template x-if="match.manufacturer.data_quality_flags.length > 0">
                                                        <span class="px-2 py-0.5 text-[9px] font-mono uppercase bg-amber-500/10 text-amber-300 rounded border border-amber-500/20" title="Cleaned during automated data sanitation">Audit Flag</span>
                                                    </template>
                                                </div>
                                                <p class="text-xs text-slate-400 mt-1 flex items-center space-x-2">
                                                    <span x-text="match.manufacturer.city + ', ' + match.manufacturer.state_name"></span>
                                                    <span>•</span>
                                                    <span x-text="'Est. ' + match.manufacturer.founded_year"></span>
                                                    <span>•</span>
                                                    <span class="capitalize" x-text="match.manufacturer.company_size + ' Enterprise'"></span>
                                                </p>
                                            </div>
                                        </div>

                                        <!-- Circular Score Ring Visual -->
                                        <div class="flex items-center space-x-3 bg-white/[0.02] p-2 rounded-2xl border border-white/[0.06]">
                                            <div class="relative w-14 h-14 flex items-center justify-center">
                                                <svg class="w-14 h-14 score-circle" viewBox="0 0 36 36">
                                                    <path class="text-slate-800" stroke-width="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                                    <path class="text-emerald-400" stroke-dasharray="100, 100" :stroke-dashoffset="100 - match.score_breakdown.total_score" stroke-linecap="round" stroke-width="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                                </svg>
                                                <span class="absolute font-mono font-bold text-xs text-white" x-text="match.score_breakdown.total_score"></span>
                                            </div>
                                            <div class="pr-2 text-right">
                                                <span class="text-[9px] font-mono uppercase text-slate-500 font-bold block">Match Score</span>
                                                <span class="text-xs font-bold text-emerald-400 font-sans">Verified</span>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- 5-Factor Weighted Score Breakdown (Radar Progress Bars) -->
                                    <div class="grid grid-cols-5 gap-3 pt-4 border-t border-white/[0.06] text-[10px]">
                                        <div class="space-y-1">
                                            <div class="flex justify-between text-slate-400 font-medium">
                                                <span>Speed (30%)</span>
                                                <span class="font-mono text-white font-bold" x-text="match.score_breakdown.speed_score"></span>
                                            </div>
                                            <div class="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-emerald-400 h-full rounded-full" :style="'width: ' + match.score_breakdown.speed_score + '%'"></div>
                                            </div>
                                        </div>
                                        <div class="space-y-1">
                                            <div class="flex justify-between text-slate-400 font-medium">
                                                <span>Quality (25%)</span>
                                                <span class="font-mono text-white font-bold" x-text="match.score_breakdown.reliability_score"></span>
                                            </div>
                                            <div class="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-teal-400 h-full rounded-full" :style="'width: ' + match.score_breakdown.reliability_score + '%'"></div>
                                            </div>
                                        </div>
                                        <div class="space-y-1">
                                            <div class="flex justify-between text-slate-400 font-medium">
                                                <span>Capacity (20%)</span>
                                                <span class="font-mono text-white font-bold" x-text="match.score_breakdown.capacity_score"></span>
                                            </div>
                                            <div class="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-blue-400 h-full rounded-full" :style="'width: ' + match.score_breakdown.capacity_score + '%'"></div>
                                            </div>
                                        </div>
                                        <div class="space-y-1">
                                            <div class="flex justify-between text-slate-400 font-medium">
                                                <span>Export (15%)</span>
                                                <span class="font-mono text-white font-bold" x-text="match.score_breakdown.export_score"></span>
                                            </div>
                                            <div class="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-indigo-400 h-full rounded-full" :style="'width: ' + match.score_breakdown.export_score + '%'"></div>
                                            </div>
                                        </div>
                                        <div class="space-y-1">
                                            <div class="flex justify-between text-slate-400 font-medium">
                                                <span>Audit (10%)</span>
                                                <span class="font-mono text-white font-bold" x-text="match.score_breakdown.audit_score"></span>
                                            </div>
                                            <div class="w-full bg-white/[0.05] h-1.5 rounded-full overflow-hidden">
                                                <div class="bg-purple-400 h-full rounded-full" :style="'width: ' + match.score_breakdown.audit_score + '%'"></div>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Key Metrics Matrix -->
                                    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white/[0.02] p-3.5 rounded-2xl border border-white/[0.04] text-xs">
                                        <div>
                                            <span class="text-slate-500 text-[10px] uppercase font-mono block">Production Cycle</span>
                                            <div class="flex items-center space-x-1.5 mt-0.5">
                                                <span class="font-bold text-white font-mono" x-text="match.manufacturer.lead_time_weeks + ' weeks'"></span>
                                                <span class="text-[10px] text-emerald-400 font-mono" x-text="'(+' + match.explanation.lead_time_margin_weeks + 'w buffer)'"></span>
                                            </div>
                                        </div>
                                        <div>
                                            <span class="text-slate-500 text-[10px] uppercase font-mono block">On-Time Track Record</span>
                                            <div class="flex items-center space-x-1.5 mt-0.5">
                                                <span class="font-bold text-white font-mono" x-text="match.manufacturer.on_time_delivery_pct + '%'"></span>
                                                <span class="px-1.5 py-0.2 rounded text-[10px] font-bold" :class="match.manufacturer.delivery_rating === 'A' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-700 text-slate-300'" x-text="'Grade ' + match.manufacturer.delivery_rating"></span>
                                            </div>
                                        </div>
                                        <div>
                                            <span class="text-slate-500 text-[10px] uppercase font-mono block">Factory Capacity Fit</span>
                                            <div class="flex items-center space-x-1.5 mt-0.5">
                                                <span class="font-bold text-white font-mono" x-text="match.manufacturer.capacity_units_per_month.toLocaleString() + '/mo'"></span>
                                                <span class="text-[10px] text-slate-400 font-mono" x-text="'(' + match.explanation.capacity_utilization_pct + '% load)'"></span>
                                            </div>
                                        </div>
                                        <div>
                                            <span class="text-slate-500 text-[10px] uppercase font-mono block">Export Maturity</span>
                                            <div class="flex items-center space-x-1.5 mt-0.5">
                                                <span class="font-bold text-white font-mono" x-text="match.manufacturer.export_experience_years + ' Years'"></span>
                                                <span class="text-[10px] text-slate-400">Global</span>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Explanations & Key Decision Drivers -->
                                    <div class="space-y-2 text-xs">
                                        <div class="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold">Why This Manufacturer Won:</div>
                                        <div class="space-y-1.5">
                                            <template x-for="strength in match.explanation.key_strengths" :key="strength">
                                                <div class="flex items-start space-x-2 text-slate-300">
                                                    <i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0"></i>
                                                    <span x-text="strength"></span>
                                                </div>
                                            </template>
                                        </div>

                                        <!-- Risks or Operational Watch Items -->
                                        <template x-if="match.explanation.risks_and_tradeoffs.length > 0">
                                            <div class="pt-2 space-y-1">
                                                <template x-for="risk in match.explanation.risks_and_tradeoffs" :key="risk">
                                                    <div class="flex items-start space-x-2 text-amber-300/90 text-[11px]">
                                                        <i data-lucide="alert-triangle" class="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0"></i>
                                                        <span x-text="risk"></span>
                                                    </div>
                                                </template>
                                            </div>
                                        </template>
                                    </div>

                                    <!-- Card Actions Footer -->
                                    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-4 border-t border-white/[0.06] text-xs">
                                        <div class="flex flex-wrap items-center gap-2">
                                            <span class="text-slate-500 font-mono text-[10px] uppercase">Certifications:</span>
                                            <template x-for="cert in match.manufacturer.certifications" :key="cert">
                                                <span class="px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-300 border border-blue-500/20 font-mono text-[10px]" x-text="cert"></span>
                                            </template>
                                            <span class="text-slate-500 font-mono text-[10px]" x-text="'(Expires: ' + match.manufacturer.certification_expiry + ')'"></span>
                                        </div>

                                        <div class="flex items-center space-x-2.5 w-full sm:w-auto">
                                            <button @click="reserveCapacity(match.manufacturer.manufacturer_id, form.quantity)" class="flex-1 sm:flex-none px-4 py-2 bg-white/[0.04] hover:bg-emerald-500/10 border border-white/[0.08] hover:border-emerald-500/30 text-slate-200 text-xs rounded-xl font-semibold transition-all flex items-center justify-center space-x-1.5">
                                                <i data-lucide="lock" class="w-3.5 h-3.5 text-emerald-400"></i>
                                                <span>Soft-Reserve Capacity</span>
                                            </button>
                                            <button @click="generateExecutiveMemo(match)" class="flex-1 sm:flex-none px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs rounded-xl font-bold transition-all shadow-lg shadow-emerald-600/20 flex items-center justify-center space-x-1.5">
                                                <i data-lucide="file-text" class="w-3.5 h-3.5"></i>
                                                <span>Executive Memo</span>
                                            </button>
                                        </div>
                                    </div>

                                </div>
                            </template>
                        </div>
                    </template>

                    <!-- Zero Matches (Relaxed Search Mode) -->
                    <template x-if="searchResponse && searchResponse.matches.length === 0 && searchResponse.relaxed_matches">
                        <div class="glass-panel p-8 rounded-3xl border border-red-500/30 bg-red-500/[0.02] space-y-6">
                            <div class="flex items-center space-x-3 text-red-400">
                                <div class="p-2.5 bg-red-500/10 rounded-2xl border border-red-500/20">
                                    <i data-lucide="alert-octagon" class="w-6 h-6"></i>
                                </div>
                                <div>
                                    <h3 class="text-base font-bold text-white tracking-tight">Zero Suppliers Passed 100% of Constraints</h3>
                                    <p class="text-xs text-red-300">Displaying closest matching candidates with explicit disqualification audit reasons:</p>
                                </div>
                            </div>

                            <div class="space-y-4">
                                <template x-for="rm in searchResponse.relaxed_matches" :key="rm.manufacturer.manufacturer_id">
                                    <div class="glass-card p-5 rounded-2xl space-y-3">
                                        <div class="flex justify-between items-center">
                                            <div>
                                                <h4 class="font-bold text-white" x-text="rm.manufacturer.name + ' (' + rm.manufacturer.city + ')'"></h4>
                                                <span class="text-[10px] font-mono text-slate-400" x-text="rm.manufacturer.manufacturer_id"></span>
                                            </div>
                                            <span class="px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20 font-mono text-xs font-bold" x-text="'Penalized Score: ' + rm.score_breakdown.total_score"></span>
                                        </div>
                                        <div class="space-y-1.5 text-xs">
                                            <template x-for="reason in rm.disqualification_reasons" :key="reason">
                                                <div class="flex items-center space-x-2 text-red-300">
                                                    <i data-lucide="x-circle" class="w-3.5 h-3.5 text-red-400 flex-shrink-0"></i>
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

        <!-- ================================================================= -->
        <!-- TAB 2: AI RFQ PARSER -->
        <!-- ================================================================= -->
        <div x-show="activeTab === 'nlp'" class="max-w-4xl mx-auto space-y-6">
            <div class="glass-panel p-8 rounded-3xl border border-white/[0.08] shadow-2xl space-y-5">
                <div class="flex items-center space-x-3.5">
                    <div class="p-3 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl text-slate-950 shadow-lg shadow-emerald-500/20">
                        <i data-lucide="bot" class="w-6 h-6"></i>
                    </div>
                    <div>
                        <h2 class="text-lg font-bold text-white tracking-tight">AI Natural Language RFQ Parser</h2>
                        <p class="text-xs text-slate-400">Paste unstructured buyer emails, WhatsApp briefs, or procurement RFQs in plain text:</p>
                    </div>
                </div>

                <div class="relative">
                    <textarea x-model="nlpText" rows="6" class="w-full bg-[#0d1017] border border-white/[0.1] rounded-2xl p-5 text-xs text-slate-100 font-mono focus:outline-none focus:border-emerald-500 leading-relaxed shadow-inner" placeholder="Paste buyer requirement here..."></textarea>
                </div>

                <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-2">
                    <div class="text-[11px] text-slate-400 flex items-center space-x-1.5">
                        <i data-lucide="info" class="w-3.5 h-3.5 text-emerald-400"></i>
                        <span>Understands informal batches ('a few thousand'), German/English terms, and process synonyms.</span>
                    </div>

                    <button @click="submitNlp()" :disabled="isLoading" class="px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-extrabold text-xs rounded-xl shadow-lg shadow-emerald-500/25 transition-all flex items-center space-x-2">
                        <i data-lucide="sparkles" class="w-4 h-4"></i>
                        <span>Extract Specifications & Match</span>
                    </button>
                </div>
            </div>
        </div>

        <!-- ================================================================= -->
        <!-- TAB 3: BUYER A VS BUYER B CONTENTION SIMULATOR -->
        <!-- ================================================================= -->
        <div x-show="activeTab === 'contention'" class="space-y-6">
            
            <div class="glass-panel p-6 rounded-3xl border border-white/[0.08] shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                <div>
                    <div class="flex items-center space-x-2.5">
                        <i data-lucide="users" class="w-5 h-5 text-emerald-400"></i>
                        <h2 class="text-lg font-bold text-white tracking-tight">Simultaneous Buyer Contention Resolution</h2>
                    </div>
                    <p class="text-xs text-slate-400 mt-1 max-w-2xl">
                        <strong>Prompt Puzzle:</strong> Buyer A (1,000 Aluminium CNC, 6w) and Buyer B (1,500 Stainless Sheet-Metal, 6w) arrive at the exact same moment. Compare how allocation models prevent capacity choke:
                    </p>
                </div>

                <div class="flex items-center space-x-2 bg-white/[0.03] p-1.5 rounded-2xl border border-white/[0.06]">
                    <button @click="runContention('pareto_optimal')" :class="contentionStrategy === 'pareto_optimal' ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold shadow-lg shadow-emerald-600/20' : 'text-slate-400 hover:text-white'" class="px-4 py-2 text-xs rounded-xl transition-all flex items-center space-x-1.5">
                        <i data-lucide="award" class="w-3.5 h-3.5"></i>
                        <span>Pareto Optimal (Recommended)</span>
                    </button>
                    <button @click="runContention('fcfs')" :class="contentionStrategy === 'fcfs' ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold shadow-lg shadow-emerald-600/20' : 'text-slate-400 hover:text-white'" class="px-4 py-2 text-xs rounded-xl transition-all flex items-center space-x-1.5">
                        <i data-lucide="clock" class="w-3.5 h-3.5"></i>
                        <span>First-Come First-Served</span>
                    </button>
                </div>
            </div>

            <template x-if="contentionResponse">
                <div class="space-y-6">
                    
                    <!-- Strategic Explanation Card -->
                    <div class="glass-panel p-6 rounded-3xl border border-emerald-500/30 bg-emerald-500/[0.03] space-y-2">
                        <div class="flex items-center space-x-2">
                            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono uppercase font-bold tracking-wider bg-emerald-500/20 text-emerald-300" x-text="contentionResponse.resolution_strategy.toUpperCase()"></span>
                            <span class="text-xs font-bold text-white">System Optimization Rationale:</span>
                        </div>
                        <p class="text-xs text-slate-300 leading-relaxed font-sans" x-text="contentionResponse.explanation"></p>
                    </div>

                    <!-- Side-by-Side Allocation Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        
                        <!-- Buyer A Card -->
                        <div class="glass-card p-6 rounded-3xl space-y-5 border-l-4 border-l-blue-500">
                            <div class="flex justify-between items-start">
                                <div>
                                    <span class="px-2.5 py-0.5 rounded-md text-[10px] font-mono font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">BUYER A ALLOCATION</span>
                                    <h3 class="text-base font-bold text-white mt-1.5">1,000 Aluminium CNC Parts</h3>
                                    <p class="text-xs text-slate-400">Target Timeline: 6 weeks • ISO 9001 Mandatory</p>
                                </div>
                                <div class="text-right">
                                    <div class="text-2xl font-black text-blue-400 font-mono" x-text="contentionResponse.buyer_a_allocated.score_breakdown.total_score"></div>
                                    <span class="text-[9px] font-mono uppercase text-slate-500 font-bold">Utility Score</span>
                                </div>
                            </div>

                            <div class="bg-white/[0.02] p-4 rounded-2xl border border-white/[0.04] space-y-2 text-xs">
                                <div class="font-bold text-white text-sm" x-text="contentionResponse.buyer_a_allocated.manufacturer.name"></div>
                                <div class="text-slate-400 text-xs" x-text="contentionResponse.buyer_a_allocated.manufacturer.city + ', ' + contentionResponse.buyer_a_allocated.manufacturer.state_name"></div>
                                <div class="grid grid-cols-3 gap-2 pt-2 text-[11px] font-mono">
                                    <div>
                                        <span class="text-slate-500 block text-[9px]">Lead Time</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_a_allocated.manufacturer.lead_time_weeks + 'w'"></span>
                                    </div>
                                    <div>
                                        <span class="text-slate-500 block text-[9px]">OTD</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_a_allocated.manufacturer.on_time_delivery_pct + '%'"></span>
                                    </div>
                                    <div>
                                        <span class="text-slate-500 block text-[9px]">Monthly Cap</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_a_allocated.manufacturer.capacity_units_per_month.toLocaleString()"></span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Buyer B Card -->
                        <div class="glass-card p-6 rounded-3xl space-y-5 border-l-4 border-l-purple-500">
                            <div class="flex justify-between items-start">
                                <div>
                                    <span class="px-2.5 py-0.5 rounded-md text-[10px] font-mono font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">BUYER B ALLOCATION</span>
                                    <h3 class="text-base font-bold text-white mt-1.5">1,500 Stainless Sheet-Metal Parts</h3>
                                    <p class="text-xs text-slate-400">Target Timeline: 6 weeks • ISO 9001 Mandatory</p>
                                </div>
                                <div class="text-right">
                                    <div class="text-2xl font-black text-purple-400 font-mono" x-text="contentionResponse.buyer_b_allocated.score_breakdown.total_score"></div>
                                    <span class="text-[9px] font-mono uppercase text-slate-500 font-bold">Utility Score</span>
                                </div>
                            </div>

                            <div class="bg-white/[0.02] p-4 rounded-2xl border border-white/[0.04] space-y-2 text-xs">
                                <div class="font-bold text-white text-sm" x-text="contentionResponse.buyer_b_allocated.manufacturer.name"></div>
                                <div class="text-slate-400 text-xs" x-text="contentionResponse.buyer_b_allocated.manufacturer.city + ', ' + contentionResponse.buyer_b_allocated.manufacturer.state_name"></div>
                                <div class="grid grid-cols-3 gap-2 pt-2 text-[11px] font-mono">
                                    <div>
                                        <span class="text-slate-500 block text-[9px]">Lead Time</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_b_allocated.manufacturer.lead_time_weeks + 'w'"></span>
                                    </div>
                                    <div>
                                        <span class="text-slate-500 block text-[9px]">OTD</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_b_allocated.manufacturer.on_time_delivery_pct + '%'"></span>
                                    </div>
                                    <div>
                                        <span class="text-slate-500 block text-[9px]">Monthly Cap</span>
                                        <span class="font-bold text-white" x-text="contentionResponse.buyer_b_allocated.manufacturer.capacity_units_per_month.toLocaleString()"></span>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </template>
        </div>

        <!-- ================================================================= -->
        <!-- TAB 4: DATA QUALITY AUDIT (40 ANOMALIES) -->
        <!-- ================================================================= -->
        <div x-show="activeTab === 'audit'" class="space-y-6">
            <div class="glass-panel p-6 rounded-3xl border border-white/[0.08] shadow-2xl space-y-4">
                <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                        <h2 class="text-base font-bold text-white tracking-tight">Dataset Sanitation & Data Quality Audit</h2>
                        <p class="text-xs text-slate-400 mt-1">40 intentional flaws detected and resolved across the 1,000 mock manufacturer records:</p>
                    </div>
                    <span class="px-3.5 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-xs font-bold">
                        40 Cleaned Records (100% Retained)
                    </span>
                </div>

                <!-- Live Audit Table -->
                <div class="overflow-x-auto rounded-2xl border border-white/[0.06]">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-white/[0.03] text-slate-400 font-mono uppercase text-[10px] border-b border-white/[0.06]">
                            <tr>
                                <th class="p-3.5">Surrogate Facility ID</th>
                                <th class="p-3.5">Factory Name</th>
                                <th class="p-3.5">Location</th>
                                <th class="p-3.5">Process</th>
                                <th class="p-3.5">OTD Cleanse</th>
                                <th class="p-3.5">Lead Time</th>
                                <th class="p-3.5">Sanitation Action</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-white/[0.04] font-mono text-[11px]">
                            <template x-for="item in auditList" :key="item.manufacturer_id">
                                <tr class="hover:bg-white/[0.02] transition-colors">
                                    <td class="p-3.5 font-bold text-emerald-400" x-text="item.manufacturer_id"></td>
                                    <td class="p-3.5 font-sans font-medium text-white" x-text="item.name"></td>
                                    <td class="p-3.5 font-sans text-slate-400" x-text="item.city + ', ' + item.state"></td>
                                    <td class="p-3.5 text-slate-300" x-text="item.primary_process"></td>
                                    <td class="p-3.5">
                                        <template x-if="item.raw_on_time_delivery_pct > 100">
                                            <span class="text-amber-400 font-bold" x-text="item.raw_on_time_delivery_pct + '% -> 100.0%'"></span>
                                        </template>
                                        <template x-if="item.raw_on_time_delivery_pct <= 100">
                                            <span class="text-slate-400" x-text="item.on_time_delivery_pct + '%'"></span>
                                        </template>
                                    </td>
                                    <td class="p-3.5 text-slate-300" x-text="item.lead_time_weeks + 'w'"></td>
                                    <td class="p-3.5 font-sans text-[10px] text-emerald-300" x-text="item.flags.join('; ')"></td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

    </main>

    <!-- Executive Memo Modal -->
    <div x-show="memoModalOpen" class="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4" style="display: none;">
        <div class="glass-panel border border-white/[0.12] max-w-2xl w-full p-7 rounded-3xl space-y-5 max-h-[85vh] overflow-y-auto shadow-2xl" @click.away="memoModalOpen = false">
            <div class="flex justify-between items-center border-b border-white/[0.08] pb-4">
                <div class="flex items-center space-x-2.5">
                    <i data-lucide="file-text" class="w-5 h-5 text-emerald-400"></i>
                    <h3 class="text-sm font-bold text-white uppercase tracking-wider font-sans">Executive Procurement Memorandum</h3>
                </div>
                <button @click="memoModalOpen = false" class="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-white/[0.05]">
                    <i data-lucide="x" class="w-5 h-5"></i>
                </button>
            </div>
            
            <div class="text-xs text-slate-300 whitespace-pre-line font-mono bg-[#0d1017] p-5 rounded-2xl border border-white/[0.08] leading-relaxed select-text" x-text="currentMemoText"></div>
            
            <div class="flex justify-between items-center pt-2">
                <button @click="copyMemo()" class="px-4 py-2 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 text-xs rounded-xl font-medium transition-all flex items-center space-x-2">
                    <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                    <span x-text="copiedText ? 'Copied to Clipboard!' : 'Copy Memorandum'"></span>
                </button>
                <button @click="memoModalOpen = false" class="px-5 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 text-slate-950 font-extrabold text-xs rounded-xl transition-all">Done</button>
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
                copiedText: false,
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
                    setTimeout(() => { lucide.createIcons(); }, 100);
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
                            this.$nextTick(() => { lucide.createIcons(); });
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
                            this.$nextTick(() => { lucide.createIcons(); });
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
                            this.$nextTick(() => { lucide.createIcons(); });
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
                            this.$nextTick(() => { lucide.createIcons(); });
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
                            this.copiedText = false;
                            this.memoModalOpen = true;
                            this.$nextTick(() => { lucide.createIcons(); });
                        }
                    } catch (e) {
                        alert('Failed to generate memo');
                    }
                },

                copyMemo() {
                    navigator.clipboard.writeText(this.currentMemoText);
                    this.copiedText = true;
                    setTimeout(() => { this.copiedText = false; }, 2500);
                }
            };
        }
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
