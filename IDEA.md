# Veridia Product Engineer Assignment: Master Strategy & Architectural Blueprint
**Document:** `IDEA.md`  
**Role:** Product Engineer / Tech Lead  
**Target Submission:** Veridia Manufacturer Matching System  
**Dataset Reference:** `veridia_csv.csv` (1,000 Indian Precision Manufacturers)

---

## 1. Executive Summary & Assignment Deconstruction

### 1.1 The Business Objective
Veridia’s mission is to bridge international industrial buyers (e.g., German automotive/aerospace firms, European precision machinery makers) with precision engineering manufacturers across India.

Currently, matching a foreign buyer with an Indian factory is heavily manual, opaque, and fraught with friction:
- **Disparate data**: Capabilities, certifications, machine capacities, and quality ratings are fragmented across unstructured spreadsheets and audit notes.
- **High stakes**: Precision parts (aerospace, automotive, medical) have zero tolerance for quality slips. A manufacturer lacking valid ISO/IATF certificates or adequate lead time can cause catastrophic supply chain disruptions.
- **Dynamic demands**: International buyers frequently revise tolerances, order quantities, or required delivery windows mid-conversation.
- **Capacity competition**: When multiple global buyers arrive simultaneously, high-performing tier-1 factories quickly become bottlenecked.

### 1.2 What Veridia is Evaluating
The assignment prompt explicitly highlights three pillars:
1. **Judgement**: Reasoning through trade-offs, handling ambiguous or messy data, determining how to handle capacity contention between simultaneous buyers, and knowing what *not* to build.
2. **Craft**: Writing resilient, well-typed, fully tested, and cleanly architected production code that does not crash on malformed inputs or noisy data.
3. **Clarity**: Radical transparency. Any non-technical procurement manager or executive who has never seen the codebase should be able to get a recommendation and immediately understand **why** that manufacturer was selected over others.
4. **Deliberate AI Usage**: Using AI where it genuinely adds leverage (unstructured natural language RFQ parsing, human-readable match rationale synthesis) rather than blindly delegating core arithmetic and deterministic filtering to a hallucinating LLM.

---

## 2. In-Depth Dataset Forensics (`veridia_csv.csv`)

A deep automated scan of the 1,000-row dataset revealed several deliberate data quality challenges. The tool **must** handle these gracefully:

| Data Anomaly Found | Specific Examples in Dataset | Impact if Unhandled | Our Architectural Solution |
| :--- | :--- | :--- | :--- |
| **Manufacturer ID Collisions (Duplicates)** | 10 pairs (20 rows) share identical IDs (e.g., `VM1092` appears at row 91 as *Narmada Titan Machine Works* in Ahmedabad and row 999 as *Deccan Crest Castings* in Aurangabad; `VM1233`, `VM1254`, `VM1624`, etc.) | Key collisions, overwriting records in dictionaries/DBs, data corruption | Assign composite surrogate primary keys (`VM1092-1`, `VM1092-2`) and surface a multi-facility warning. |
| **Physically Impossible OTD Percentages** | 10 rows have `on_time_delivery_pct > 100%` (e.g., `VM1429` has **142.6%**, `VM1869` has **141.7%**, `VM1521` has **135.4%**) | Algorithmic skew, ranking distortion, buyer distrust | Data Hygiene Pipeline clamps/winsorizes values at 100.0% and reconciles against the discrete `delivery_rating` (A/B/C) with an audit flag. |
| **Missing Lead Time Values (NaN)** | 10 rows have `lead_time_weeks` and `lead_time_days` as `NaN` (e.g., `VM1150`, `VM1281`, `VM1438`) | Crash on comparison operators (`<`, `<=`) or silent drop of otherwise viable factories | Smart imputation based on median process lead time + explicit "Unconfirmed Lead Time" confidence penalty tag. |
| **Delimited Multi-Valued Fields** | `processes` (e.g. `sheet metal;CNC milling`), `materials` (e.g. `aluminium;copper;ABS`), `certifications` (e.g. `ISO 9001;IATF 16949`) | Inexact string matching failures | Normalized set-based tokenization with case-insensitive canonical vocabulary mapping (e.g. `machined` -> `CNC milling`/`CNC turning`). |
| **Certificate Expiration Horizon** | Expiry dates span from **2026-10-25** to **2029-06-18**. Some certificates have already expired relative to late 2026! | Non-deterministic results if using dynamic `datetime.now()` | Configurable fixed temporal anchor (`as_of_date`) + lead-time buffer checking (cert must remain valid *throughout* the delivery window). |

---

## 3. Core Scenarios & Problem Walkthroughs

### Scenario A: The German Industrial Buyer
- **Requirements**:
  - Material: `aluminium`
  - Process: `machined to order` (maps to CNC milling, CNC turning, precision grinding)
  - Volume: Batches of a few thousand over time (e.g. 2,000 units/batch)
  - Quality: ISO 9001 mandatory (IATF 16949 / AS9100 preferred)
  - Timeline: Strict lead time requirement (air/sea freight from India to Hamburg/Frankfurt adds 2–4 weeks; factory lead time must be lean).
- **Domain Considerations for German Buyers**:
  - German Mittelstand and Tier-1 automotive/aerospace manufacturers prioritize DIN/ISO compliance, tight dimensional repeatability, and documented export compliance (`export_experience_years`).
  - A manufacturer with 15+ years export experience and an 'A' delivery rating is far superior to a slightly cheaper micro-workshop with no international shipping track record.

---

### Scenario B: The "Two Simultaneous Buyers" Contention Dilemma
*The prompt states: Buyer A wants ~1,000 aluminium CNC parts with ISO 9001 in 6 weeks. Buyer B wants ~1,500 stainless sheet-metal parts with ISO 9001 in 6 weeks. Both reach you at the same time. Work out what happens next.*

#### What Actually Happens in the Factory?
1. **The Shared Resource Risk**:
   - High-performing factories in the dataset often do multiple processes (e.g., `VM1006` does *sheet metal* AND *CNC milling* with ISO 9001).
   - If Buyer A (1,000 units) and Buyer B (1,500 units) are matched independently, they may both select the same top factory.
   - If that factory only has `capacity_units_per_month: 1,500` (Low Tier), accepting both orders (2,500 units) causes immediate **capacity breach** (166% utilization), triggering massive delivery delays and quality compromises.
2. **The Temporal / Concurrency Problem**:
   - In real-world marketplaces, requests arrive concurrently over websockets/HTTP.
   - If treated in pure isolation, both buyers receive confirmation for the same factory capacity.
3. **Our Architectural Solution**:
   - **Session & Allocation Engine**:
     - **Mode 1: Interactive Soft-Reservation (Atomic Allocation)**: When Buyer A commits/views an allocation, that capacity is reserved for an expiration window (e.g., 15 minutes). Buyer B's real-time match engine immediately recalculates available capacity (`capacity_available = total_capacity - committed_capacity`).
     - **Mode 2: Global Multi-Buyer Optimizer (Pareto Optimal Matching)**:
       If both requests are processed in the same matching batch, the engine solves a **Bipartite Assignment Problem**:
       - Buyer A is assigned to Factory X (best CNC specialist).
       - Buyer B is assigned to Factory Y (best sheet-metal specialist).
       - This prevents a multi-process factory from being oversubscribed when specialized single-process alternatives exist with identical quality scores.
     - **Mode 3: Transparent Capacity Warning**: If both select the same supplier, the tool warns both buyers: *"Factory VM1006 has 1,500 monthly capacity. Buyer A takes 67%, leaving 33%. Buyer B requires 100%, causing a 3-week lead time overflow unless split or rescheduled."*

---

### Scenario C: The Timing & Certificate Expiry Dilemma
*The prompt states: "Certificates expire, so whether a manufacturer counts as valid depends on when you ask. Decide what date makes sense, and make sure the same request always gives the same answer."*

#### Why this is a subtle trap:
If a developer writes `datetime.date.today()`, running the code today, next month, or in CI/CD tests 6 months later produces different search results. That breaks test repeatability and deterministic audit trails.

#### Our Decision & Design:
1. **Deterministic Temporal Anchor (`as_of_date`)**:
   - The system defaults to a pinned evaluation baseline (e.g., `2026-10-28` or the dataset snapshot timestamp), but allows the user to specify any reference date.
   - For any given `(requirement, as_of_date)` tuple, the answer is **100% mathematically deterministic and reproducible**.
2. **Production Horizon Validity Check (Not just "valid today")**:
   - A certificate that expires next week is **invalid** for an order that takes 6 weeks to manufacture!
   - Our engine checks:
     $$\text{certification\_expiry} \ge \text{as\_of\_date} + \text{lead\_time\_days}$$
   - If a certificate expires during the scheduled production window, the supplier is flagged with a **"Certificate Expiry Risk"** penalty or filtered out if zero-tolerance mode is active.

---

### Scenario D: Multi-Buyer Concurrency & In-Flight Requirement Changes
*The prompt states: "Assume several buyers will use it at once, and that some of them will change their requirement partway through. It should still give answers someone can trust, including for inputs you did not expect."*

#### Architectural Solution:
1. **Stateless Core with Session Isolation**:
   - The matching engine itself is pure and functional (`match(dataset, criteria, session_context) -> MatchResult`).
   - Each buyer operates inside a distinct `SessionID` with immutable requirement state.
2. **Delta Recalculation & Diff Highlighting**:
   - When Buyer A changes batch size from `1,000` to `3,500`, the engine computes the delta and explicitly informs the user:
     - *"Changing quantity from 1,000 to 3,500 disqualified 14 micro-tier manufacturers whose max order quantity is below 3,500."*
     - *"Top match shifted from Factory VM1006 to Factory VM1018 due to higher monthly capacity tier."*
3. **Resilience to Unexpected / Malformed Inputs**:
   - Negative batch sizes ($\le 0$), typos in processes ("machinng", "aluminam"), 0-day lead times, unknown certifications.
   - Handled via Pydantic schema validation, fuzzy synonym normalization, and graceful fallback with descriptive error badges rather than application crashes (500 errors).

---

## 4. System Architecture & Components

```
                           +-----------------------------------------------+
                           |         USER INTERACTION CHANNELS             |
                           |  - Modern Interactive Web Dashboard (UI)     |
                           |  - CLI Interface for Automated CI / Pipelines|
                           |  - RESTful Engine API (FastAPI)               |
                           +-----------------------+-----------------------+
                                                   |
                                                   v
                           +-----------------------------------------------+
                           |       STRATEGIC AI ENHANCEMENT LAYER          |
                           |  1. Natural Language RFQ Parser (LLM)         |
                           |  2. Executive Match Rationale Explainer       |
                           |  3. Trade-off & Negotiation Recommender       |
                           +-----------------------+-----------------------+
                                                   |
                                                   v
                           +-----------------------------------------------+
                           |      CORE MATCHING & SCORING PIPELINE         |
                           |                                               |
                           |  [1] Ingestion & Sanitation (Deduplication,   |
                           |      OTD Clamping, NaN Imputation)            |
                           |  [2] Hard Eligibility Gatekeeper              |
                           |      (Process, Material, MOQ, Valid Cert)     |
                           |  [3] Multi-Factor Soft Scoring Engine         |
                           |      (Delivery, Capacity, Reliability, Exp)   |
                           |  [4] Transparent Score Breakdown Synthesizer  |
                           +-----------------------+-----------------------+
                                                   |
                                                   v
                           +-----------------------------------------------+
                           |      CONCURRENCY & CONTENTION MANAGER         |
                           |  - Thread-Safe Multi-Session Registry         |
                           |  - Factory Capacity Reservation & Lock        |
                           |  - Two-Buyer Contention Simulation & Warning  |
                           +-----------------------------------------------+
```

---

## 5. The Two-Stage Matching & Scoring Algorithm

The matching algorithm avoids "black-box" magic and implements a transparent, auditable two-stage model:

### Stage 1: Hard Eligibility Filters (Binary Gatekeeper)
A manufacturer is strictly disqualified if they fail any of these non-negotiable criteria:
1. **Process Capability**: Must possess at least one of the requested processes (e.g. `CNC milling`, `CNC turning`).
2. **Material Compatibility**: Must handle the specified material (e.g. `aluminium`).
3. **Order Quantity Feasibility**: Buyer's quantity must satisfy:
   $$\text{min\_order\_qty} \le \text{Order Quantity} \le \text{max\_order\_qty}$$
4. **Active Status**: Must have `status == 'active'`.
5. **Certified Quality Gate**: If an ISO/IATF certification is required, the manufacturer must hold it, and it must not be expired as of the production completion date.
6. **Lead Time Constraint**: Factory lead time (in weeks) must not exceed buyer's deadline.

*(Note: If zero manufacturers pass hard filters, the engine enters an intelligent **"Relaxed Constraint Search"** mode, showing the closest candidates and explicitly explaining what prevented a 100% match, e.g., "Matches material and process, but lead time is 7 weeks instead of 6".)*

---

### Stage 2: Soft Affinity Scoring Engine (0 to 100 Points)
For all eligible manufacturers, an objective multi-attribute utility score is calculated:

$$\text{Total Score} = w_{\text{speed}} \cdot S_{\text{speed}} + w_{\text{quality}} \cdot S_{\text{quality}} + w_{\text{capacity}} \cdot S_{\text{capacity}} + w_{\text{export}} \cdot S_{\text{export}} + w_{\text{audit}} \cdot S_{\text{audit}}$$

#### Default Calibrated Weights:
- **Delivery Speed & Lead Time Buffer ($w_{\text{speed}} = 30\%$)**:
  Rewards factories that can comfortably deliver ahead of deadline.
  $$S_{\text{speed}} = \text{clamp}\left(100 \times \left(1 - \frac{\text{lead\_time\_weeks}}{\text{buyer\_timeline\_weeks}}\right), 0, 100\right)$$
- **Quality & Delivery Reliability ($w_{\text{quality}} = 25\%$)**:
  Based on clamped on-time delivery percentage and historical delivery rating (Grade A = 100, B = 80, C = 50).
- **Capacity Utilization & Fit ($w_{\text{capacity}} = 20\%$)**:
  The "Goldilocks Zone": If an order represents 10%–35% of a factory's monthly capacity, it is ideal. If it represents >70%, the factory is at risk of choking; if <3%, the factory may de-prioritize the buyer.
- **Export Maturity ($w_{\text{export}} = 15\%$)**:
  Logarithmic scaling of `export_experience_years`. High value for international shipments to Germany.
- **Audit Recency ($w_{\text{audit}} = 10\%$)**:
  Factories audited within the last 6 months get higher confidence than factories whose audit was 18+ months ago.

---

### Stage 3: Explainability Engine ("Why You Got This")
For every recommended manufacturer, the system generates a transparent scorecard:
- **Match Score**: e.g., `92.4 / 100`
- **Breakdown Cards**:
  - *Lead Time*: "4 weeks (2 weeks ahead of your 6-week target) -> Score: 95/100"
  - *Quality*: "97.8% On-Time Delivery (Rating A), ISO 9001 valid until Nov 2028 -> Score: 98/100"
  - *Capacity Fit*: "Order of 1,000 units utilizes 13.3% of 7,500/mo capacity (Optimal tier) -> Score: 90/100"
  - *Export*: "12 years exporting to EU/US markets -> Score: 85/100"
- **Risk & Trade-Off Radar**:
  - *"Notice: Factory is located in Kolhapur; inland transit to Nhava Sheva port adds ~2 days."*

---

## 6. Where AI is Used (and Where It is Intentionally Not)

The assignment explicitly advises: *"Where it helps, use AI. We would rather see it used well in a few places than used everywhere."*

### Strategic AI Touchpoints:
1. **Unstructured RFQ Parser**:
   - Buyers don't enter clean dropdown forms; they paste emails or procurement RFQ snippets:
     > *"Hi Veridia team, we're an engineering firm in Stuttgart. We urgently need 2,500 milled aluminium brackets. Must be ISO 9001 certified. We need them on our dock within 7 weeks. Can you suggest reliable suppliers?"*
   - LLM extracts structured JSON:
     `{"material": "aluminium", "process": "CNC milling", "quantity": 2500, "certifications": ["ISO 9001"], "deadline_weeks": 7, "destination": "Germany"}`.
2. **Executive Match Rationale Generator**:
   - Synthesizes the quantitative scorecard into a succinct, executive-level pitch suitable for a German VP of Procurement.
3. **Trade-Off & Counterfactual Advisor**:
   - When constraints are too tight, AI suggests pragmatic trade-offs:
     *"If you increase lead time from 4 to 6 weeks, your pool of eligible ISO 9001 aluminium machinists expands from 2 to 19, including 3 Grade-A suppliers with 20+ years of export experience."*

### Where AI is Deliberately Excluded:
- **Disqualification & Math**: Disqualifying a supplier for missing a required ISO certificate or calculating remaining machine capacity is done via deterministic, unit-tested Python code. Delegating arithmetic or compliance rules to an LLM creates hallucination risks, non-determinism, and audit failures.

---

## 7. Deliverable 2 Blueprint (The 2-Page Short Note)

The short note will be structured as follows:

1. **Who is it for?**
   - Built for two distinct user groups:
     1. **International Procurement Officers**: Need fast, trustworthy, explainable shortlists without learning Indian regional manufacturing landscapes.
     2. **Veridia Supply Chain Operations Team**: Need visibility into factory capacity, concurrent buyer conflicts, and audit data hygiene.
2. **What did we leave out, and why?**
   - **Dynamic Price / Cost Estimation**: Left out because quoting part prices without 3D CAD/STEP file geometry and machining cycle time analysis is guessing. Giving a fake quote destroys credibility.
   - **Deep Neural Embedding Search**: Left out because vector distance is uninterpretable to a procurement auditor. A rule-based + multi-attribute utility model is 100% explainable.
   - **Automated Purchase Order Execution**: Left out because high-precision engineering contracts require legal NDA, technical drawings review, and sample validation before PO release.
3. **Defense to a Sceptical Colleague**:
   - *Why clamp OTD > 100% instead of dropping the rows?* Dropping 10 manufacturers cuts legitimate production capacity. The discrepancy stems from data pipeline logging errors, while other fields (certifications, audits, order ranges) remain valid.
   - *Why anchor the date deterministically?* To ensure contract-grade reproducibility.
4. **How do we know it works? (Verification & KPIs)**:
   - **Match Acceptance Rate (% of suggested shortlists that lead to an RFQ)**.
   - **Delivery Variance (Difference between predicted lead time and actual arrival)**.
   - **Contention Resolution Rate (Zero double-booking of manufacturer capacity)**.

---

## 8. Technology Stack & Project Structure

- **Core Language**: Python 3.11+
- **Data Validation & Schemas**: `pydantic` v2 (strict type enforcement, boundary validation)
- **Data Engine**: `pandas` / clean vectorized Python math
- **AI Integration**: Standard OpenAI / Google Gemini API client or mockable LLM service layer with fallback rule parser
- **Interactive UI**: Clean, responsive Streamlit dashboard or lightweight FastAPI + Tailwind HTML UI with live sliders, side-by-side Buyer comparison, and transparent scorecards
- **Testing**: `pytest` (100% test coverage for data cleaning, filter rules, capacity contention, and determinism)

### Recommended Repository Layout:
```
veridia-matcher/
├── data/
│   ├── veridia_csv.csv              # Raw mock dataset (1,000 rows)
│   └── sanitized_manufacturers.csv  # Cleaned, deduplicated dataset
├── src/
│   ├── __init__.py
│   ├── config.py                    # Constants, default weights, temporal anchor
│   ├── data_pipeline.py             # Ingestion, deduplication, OTD clamping, NaN imputation
│   ├── models.py                    # Pydantic schemas (BuyerRequirement, Manufacturer, MatchResult)
│   ├── matching_engine.py           # Hard filters, multi-factor scoring, explainability
│   ├── allocation_manager.py        # Concurrency, capacity reservation, Buyer A/B contention
│   ├── ai_service.py                # NLP RFQ parser, executive justification generator
│   └── app.py                       # Interactive Web Dashboard (FastAPI / Streamlit)
├── tests/
│   ├── test_data_pipeline.py        # Tests for dirty data, duplicates, OTD > 100, NaNs
│   ├── test_matching_engine.py      # Tests for hard filters, scoring math, determinism
│   ├── test_concurrency.py          # Tests for Buyer A & B contention and capacity locks
│   └── test_ai_service.py           # Schema extraction and fallback tests
├── docs/
│   ├── DELIVERABLE_2_SHORT_NOTE.md  # The required 2-page architectural defense note
│   └── ARCHITECTURE.md              # Detailed technical design & decision log
├── IDEA.md                          # This master strategy file
├── requirements.txt
└── README.md                        # Quickstart instructions (<5 minutes to run)
```

---

## 9. Immediate Execution Plan (Step-by-Step)

1. **Step 1: Project Setup**: Create the project folder structure in `C:\Users\Kartik\.gemini\antigravity\scratch\veridia-matcher`, copy `veridia_csv.csv`, and set up `requirements.txt`.
2. **Step 2: Data Sanitation Pipeline**: Write `data_pipeline.py` with rigorous Pydantic models, duplicate resolver, OTD winsorization, and NaN imputation.
3. **Step 3: Core Matching & Scoring Engine**: Implement `matching_engine.py` with deterministic filters, weighted multi-factor scoring, and explainability breakdown.
4. **Step 5: Multi-Buyer Concurrency & Contention Engine**: Implement `allocation_manager.py` handling simultaneous Buyer A & Buyer B requests with capacity tracking and contention alerts.
5. **Step 6: AI Integration**: Implement `ai_service.py` for natural language RFQ extraction and executive match reasoning.
6. **Step 7: Interactive Dashboard / UI**: Build an intuitive UI allowing non-technical evaluators to test Buyer A, Buyer B, custom RFQ prompts, and view live capacity meters and scorecards.
7. **Step 8: Automated Pytest Suite**: Create comprehensive tests verifying edge cases, dirty data resilience, and deterministic repeatability.
8. **Step 9: Deliverable 2 Short Note**: Write `DELIVERABLE_2_SHORT_NOTE.md` covering all evaluator criteria.
