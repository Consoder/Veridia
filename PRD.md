# Product Requirements Document
## Veridia Precision Manufacturer Matching System

---

| Field | Value |
|---|---|
| **Document Version** | 1.0 |
| **Status** | Final — Production |
| **Date** | 2026-10-29 |
| **Author** | Product Engineering Team — Veridia |
| **Document Type** | Product Requirements Document (PRD) |
| **Repository** | https://github.com/Consoder/Veridia |
| **Evaluation Anchor** | `2026-10-28` (Deterministic Temporal Pin) |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Goals and Non-Goals](#3-goals-and-non-goals)
4. [Target Users and Personas](#4-target-users-and-personas)
5. [System Architecture Overview](#5-system-architecture-overview)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Data Model and Schema](#8-data-model-and-schema)
9. [Scoring and Matching Algorithm](#9-scoring-and-matching-algorithm)
10. [API Specification](#10-api-specification)
11. [User Interface Requirements](#11-user-interface-requirements)
12. [Testing and Quality Assurance](#12-testing-and-quality-assurance)
13. [Failure Modes and Edge Cases](#13-failure-modes-and-edge-cases)
14. [Success Metrics and KPIs](#14-success-metrics-and-kpis)
15. [Out of Scope](#15-out-of-scope)
16. [Appendix — Dataset Anomaly Catalogue](#16-appendix--dataset-anomaly-catalogue)

---

## 1. Executive Summary

Veridia is a **precision manufacturer matching system** that connects international industrial buyers — primarily procurement officers at European automotive, aerospace, and defence OEMs — with precision engineering manufacturers across India.

The core problem: industrial procurement for precision-machined components is broken. A procurement manager at a German automotive firm cannot reliably determine, within a single working day, which of 1,000+ Indian workshops can safely deliver 2,000 aluminium CNC parts with valid ISO 9001 certification in under six weeks. Existing approaches rely on broker networks (opaque, slow, commission-heavy), directory databases (stale, unscorable), or pure intuition.

Veridia replaces that process with a **two-stage deterministic matching engine** backed by a resilient data sanitation pipeline, Pareto-optimal multi-buyer allocation, and a strategic natural language layer. Every recommendation is mathematically auditable. Every disqualification is explicitly explained.

**This document is the single source of truth for the product's functional scope, architectural contracts, scoring model, API contracts, UI requirements, and quality gates.**

---

## 2. Problem Statement

### 2.1 The Buyer's Problem

An international procurement officer faces five compounding challenges when sourcing precision components from Indian manufacturers:

1. **Data opacity.** Published supplier directories contain stale capacity numbers, unverified certifications, and unreliable delivery ratings — often with typographical anomalies (OTD rates listed as 142.6%) that render raw data unusable for algorithmic decision-making.

2. **Multi-dimensional constraint matching.** A buyer's requirement spans at least seven orthogonal dimensions simultaneously: material, manufacturing process, minimum order quantity, maximum order quantity, delivery timeline, certification body, and certification validity window. No spreadsheet or keyword search handles this correctly.

3. **Temporal certificate validity.** A supplier whose ISO certification expires two weeks after the order date but before dispatch is not compliant. Standard date-comparison tools check expiry against today, not against `today + production_lead_time`. This gap causes regulatory non-conformances.

4. **Simultaneous competitor demand.** When two international buyers simultaneously need components from the same specialist factory with limited monthly capacity, a naive first-come-first-served system starves one buyer entirely — destroying platform trust.

5. **Unstructured RFQ inputs.** Buyers do not submit clean JSON. They send emails in German or English, mixing abbreviations, colloquialisms, and technical jargon. The intake layer must parse "we need 2,500 milled aluminium parts with ISO 9001 in 6 weeks for Stuttgart" into a structured specification.

### 2.2 The Operator's Problem

Veridia's supply chain operations team has its own compounding problems:

1. **Dirty master data.** The canonical 1,000-row supplier CSV has duplicate manufacturer IDs, impossible metric values, and missing lead-time fields — all of which must be automatically detected, resolved, and auditably flagged without discarding legitimate factory capacity.

2. **Capacity over-allocation risk.** Without a central reservation ledger, two sales representatives could independently commit the same factory to orders that together exceed 100% of its monthly capacity — creating fulfillment failures and supplier relationship damage.

3. **Certificate expiry management.** Certificates in the dataset expire on a rolling horizon between October 2026 and June 2029. Manual tracking across 1,000 suppliers is not operationally viable.

---

## 3. Goals and Non-Goals

### 3.1 Goals

| ID | Goal |
|---|---|
| G-01 | Match a buyer's structured or unstructured requirement against a 1,000-record manufacturer dataset in under 30 milliseconds. |
| G-02 | Resolve all four categories of data anomaly in the source CSV automatically at pipeline ingestion time. |
| G-03 | Return an explainable, ranked shortlist of up to five manufacturers with per-dimension score breakdowns and plain-language justifications. |
| G-04 | Enforce strict certificate validity checking that accounts for production lead time, not just today's date. |
| G-05 | Handle simultaneous multi-buyer requests using a Pareto-optimal allocation strategy that maximises platform-wide satisfaction. |
| G-06 | Detect and diff in-flight requirement changes mid-session, informing the buyer of the operational impact on their eligible supplier pool. |
| G-07 | Parse unstructured natural language RFQ text into structured `BuyerRequirement` objects with zero hard-coded domain assumptions. |
| G-08 | Generate executive procurement justification memoranda for the top recommended supplier, ready for leadership sign-off. |
| G-09 | Expose all capabilities via a documented REST API and an embedded web dashboard. |
| G-10 | Maintain a complete automated test suite with 100% pass rate as a CI quality gate. |

### 3.2 Non-Goals

| ID | Non-Goal | Reason |
|---|---|---|
| NG-01 | Real-time dynamic pricing or instant cost quotes | Quoting precision-machined components without 3D CAD/STEP model feature extraction (tool paths, tolerance classes, raw billet scrap rates) is irresponsible. Price negotiation belongs in the subsequent RFQ drawing-review stage. |
| NG-02 | Black-box neural / vector-embedding matching | Cosine similarity cannot enforce mathematical constraints (e.g., quantity 1,500 < MOQ 2,000). An international auditor cannot verify why an embedding chose Factory A over Factory B. The system must be 100% auditable. |
| NG-03 | Automated purchase order binding or financial commitment | International manufacturing contracts require technical drawing sign-off, NDAs, material test certificates (MTCs), and first-article inspection (FAIR) before financial commitment. Soft 15-minute capacity reservations are implemented instead. |
| NG-04 | Shipping logistics and freight cost estimation | Freight rates change daily based on carrier, port congestion, and cargo class. Adding a stale rate table introduces false precision. |
| NG-05 | Supplier onboarding, document upload, or KYC workflow | This is a matching and intelligence platform. Supplier record management is a separate operational product. |

---

## 4. Target Users and Personas

### Persona A — The International Procurement Officer

| Attribute | Detail |
|---|---|
| **Representative Role** | Senior Procurement Manager, German Automotive OEM |
| **Location** | Stuttgart, Munich, or Wolfsburg, Germany |
| **Frequency of Use** | 3–8 sourcing queries per week during active production ramp-up |
| **Technical Skill** | Moderate — comfortable with web dashboards; does not write code |
| **Primary Pain Point** | Cannot assess Indian manufacturer compliance and capacity without a 2-week broker engagement |
| **Success Criterion** | Receives a trustworthy shortlist with logistics buffer calculations and a memo ready to forward to legal/finance within 5 minutes |
| **Non-Negotiables** | Valid certifications, on-time delivery history, no capacity over-commitment |

**Typical Query (verbatim from user):**
> "We need 2,000 aluminium CNC-milled parts for our Stuttgart assembly plant. ISO 9001 mandatory. Delivery within 6 weeks."

### Persona B — The Veridia Supply Chain Operations Lead

| Attribute | Detail |
|---|---|
| **Representative Role** | Head of Supplier Operations, Veridia India |
| **Location** | Bangalore or Mumbai |
| **Frequency of Use** | Daily monitoring; ad hoc deep-dives during incident resolution |
| **Technical Skill** | High — understands data pipelines, can interpret audit logs |
| **Primary Pain Point** | Two sales representatives independently committing the same factory to excess capacity; stale certification data creating compliance risk |
| **Success Criterion** | Real-time alerts when concurrent orders threaten capacity, automatic anomaly detection with before/after audit trails |
| **Non-Negotiables** | Zero capacity over-allocation incidents, full data quality traceability |

---

## 5. System Architecture Overview

The system is structured as three tiers with a strategic AI augmentation layer:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRESENTATION TIER                              │
│   FastAPI REST API  +  Embedded HTML/CSS/JS Web Dashboard           │
│   Rich CLI (python -m src.cli)                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                      APPLICATION TIER                               │
│                                                                     │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐    │
│  │   ai_service.py     │    │       matching_engine.py         │    │
│  │                     │    │                                  │    │
│  │  NLP RFQ Parser     │    │  Stage 1: Hard Gatekeeper        │    │
│  │  Executive Memo     │    │  Stage 2: MAUT Scoring Engine    │    │
│  │  Generator          │    │  Explainability Generator        │    │
│  └─────────────────────┘    │  Relaxed Fallback Engine         │    │
│                              └──────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │               allocation_manager.py                         │    │
│  │  Session State Isolation  |  Capacity Reservation Ledger    │    │
│  │  Pareto-Optimal Allocation  |  In-Flight Delta Tracker      │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        DATA TIER                                    │
│                                                                     │
│   data_pipeline.py                                                  │
│   ├── Raw Ingestion         (veridia_csv.csv, 1,000 rows)           │
│   ├── Duplicate ID Resolver (10 collision pairs → surrogate keys)   │
│   ├── OTD Clamper           (10 records > 100% → clamped + flagged) │
│   ├── Lead-Time Imputer     (10 NaN rows → process-median + tag)    │
│   └── Sanitized Output      (sanitized_manufacturers.csv)           │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.1 Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.13.3 |
| API Framework | FastAPI | Latest |
| Data Modelling | Pydantic v2 | 2.x |
| Data Processing | Pandas + NumPy | Latest |
| Web Server | Uvicorn (ASGI) | Latest |
| UI | Embedded HTML/CSS/JS (zero build step) | — |
| CLI | Python `argparse` + Rich | Latest |
| Testing | pytest + httpx | Latest |
| Version Control | Git | — |
| Repository Host | GitHub | — |

---

## 6. Functional Requirements

### 6.1 Data Pipeline (`data_pipeline.py`)

| Req ID | Requirement | Priority |
|---|---|---|
| DP-01 | On startup, ingest `data/veridia_csv.csv` and produce a validated, in-memory list of `CleanedManufacturer` objects. | P0 |
| DP-02 | Detect all manufacturer ID collisions (rows with identical `manufacturer_id`). For each collision pair, assign surrogate keys in the format `{original_id}-FACILITY-1`, `{original_id}-FACILITY-2`. Preserve both records. | P0 |
| DP-03 | Detect all `on_time_delivery_pct` values greater than 100.0. Clamp to 100.0. Store the original value in `raw_on_time_delivery_pct`. Append `"OTD_CLAMPED"` to the record's `data_quality_flags`. | P0 |
| DP-04 | Detect all rows where `lead_time_weeks` is NaN or null. Impute using the median `lead_time_weeks` for all records sharing the same `primary_process`. Append `"LEAD_TIME_IMPUTED"` to `data_quality_flags`. | P0 |
| DP-05 | Export the sanitized dataset to `data/sanitized_manufacturers.csv` as an optional audit artefact. | P1 |
| DP-06 | Log all anomaly counts at INFO level during pipeline execution. | P1 |
| DP-07 | The pipeline must complete ingestion of 1,000 records in under 1 second on standard hardware. | P1 |

### 6.2 Matching Engine (`matching_engine.py`)

#### 6.2.1 Stage 1 — Hard Gatekeeper

| Req ID | Requirement | Priority |
|---|---|---|
| ME-01 | Disqualify any manufacturer whose `status` field is not `"Active"`. | P0 |
| ME-02 | Disqualify any manufacturer whose `materials` list does not contain the buyer's requested material (after synonym normalisation). | P0 |
| ME-03 | Disqualify any manufacturer whose `processes` list has zero intersection with the buyer's requested process (after synonym expansion from `PROCESS_SYNONYMS`). | P0 |
| ME-04 | Disqualify any manufacturer where `buyer_quantity < manufacturer.min_order_qty` (order is below MOQ). | P0 |
| ME-05 | Disqualify any manufacturer where `buyer_quantity > manufacturer.max_order_qty` (order exceeds max capacity). | P0 |
| ME-06 | Disqualify any manufacturer who does not hold all certifications in the buyer's `required_certifications` list (after synonym normalisation). | P0 |
| ME-07 | Disqualify any manufacturer whose `certification_expiry` date is before `as_of_date + lead_time_days`. This ensures the certificate remains valid through the entire production window, not merely at the start date. | P0 |
| ME-08 | When zero manufacturers pass all Stage 1 gates, activate the Relaxed Fallback mode: re-run with loosened quantity and timeline bounds and return the closest candidates with explicit disqualification reason labels. | P1 |

#### 6.2.2 Stage 2 — Multi-Attribute Utility Scoring

| Req ID | Requirement | Priority |
|---|---|---|
| ME-09 | For each manufacturer passing Stage 1, compute a `ScoreBreakdown` with five component scores on a 0–100 scale. | P0 |
| ME-10 | Compute `speed_score` based on the lead-time margin: `(buyer_timeline_weeks - manufacturer_lead_time_weeks)`. Larger positive margin = higher score. Zero or negative margin = 0 score. | P0 |
| ME-11 | Compute `reliability_score` as a weighted combination of `on_time_delivery_pct` and `delivery_rating` letter score (`A=100, B=80, C=50`). | P0 |
| ME-12 | Compute `capacity_score` using three utilisation zones: **Optimal** (5%–40% of monthly capacity) = 100, **Acceptable** (40%–70%) = 60, **Overloaded** (>70%) = 20, **Sub-critical** (<5%) = 40. | P0 |
| ME-13 | Compute `export_score` based on `export_experience_years`. Normalise against the dataset maximum. | P0 |
| ME-14 | Compute `audit_score` based on recency of `last_audit_date` relative to `as_of_date`. Audited within 12 months = 100, 12–24 months = 70, 24–36 months = 40, older = 10. | P0 |
| ME-15 | Compute `total_score` as the weighted sum: `(speed × 0.30) + (reliability × 0.25) + (capacity × 0.20) + (export × 0.15) + (audit × 0.10)`. | P0 |
| ME-16 | Return manufacturers sorted by `total_score` descending. Return a maximum of 5 results. | P0 |
| ME-17 | Accept optional `custom_weights` in `BuyerRequirement` to override the default weight distribution. | P2 |

#### 6.2.3 Explainability

| Req ID | Requirement | Priority |
|---|---|---|
| ME-18 | For each `MatchResult`, generate a `MatchExplanation` containing: `summary`, `key_strengths` list, `risks_and_tradeoffs` list, `capacity_utilization_pct`, `lead_time_margin_weeks`, and `cert_validity_status`. | P0 |
| ME-19 | The `summary` must be human-readable and include the factory name, score, city, and primary lead-time buffer statement. | P1 |
| ME-20 | Matching must be fully deterministic: identical inputs with identical `as_of_date` must produce bit-exact identical outputs across all invocations. | P0 |

### 6.3 Allocation Manager (`allocation_manager.py`)

| Req ID | Requirement | Priority |
|---|---|---|
| AM-01 | Maintain isolated state per `session_id`. Multiple concurrent sessions must not share reservation state. | P0 |
| AM-02 | When a buyer reserves a manufacturer, deduct the order quantity from that manufacturer's `available_capacity` in the ledger. Hold the reservation for `RESERVATION_TIMEOUT_MINUTES` (default: 15 minutes). | P0 |
| AM-03 | Implement a Pareto-optimal allocation strategy for simultaneous `ContentionSimulationRequest` submissions. Identify shared manufacturers between two buyers' eligible pools and re-allocate to maximise total buyer satisfaction (minimise combined score penalty). | P0 |
| AM-04 | Implement a First-Come-First-Served (FCFS) fallback strategy for comparison demonstration purposes. | P1 |
| AM-05 | When a buyer modifies their requirement mid-session (in-flight change), compute a `query_delta_notes` diff explaining: new manufacturers unlocked, manufacturers newly disqualified, and the net change in eligible pool size. | P1 |
| AM-06 | The contention response must include: `conflict_detected`, `shared_manufacturer_id`, `combined_demand`, `monthly_capacity`, `capacity_utilization_pct`, and a plain-language `explanation`. | P0 |

### 6.4 AI Service (`ai_service.py`)

| Req ID | Requirement | Priority |
|---|---|---|
| AI-01 | Accept a freeform text string (English or German) and extract a structured `BuyerRequirement` object. The parser must handle abbreviations, synonym variations, and informal phrasing. | P0 |
| AI-02 | Use vocabulary normalization dictionaries (`PROCESS_SYNONYMS`, `MATERIAL_SYNONYMS`, `CERTIFICATION_SYNONYMS`) to canonicalize extracted terms before constructing `BuyerRequirement`. | P0 |
| AI-03 | Accept a `MatchResult` and generate an executive procurement justification memorandum in formal prose. The memo must be suitable for forwarding to a procurement director without editing. | P1 |
| AI-04 | Provide a fully offline, zero-external-dependency fallback for both functions. The system must not fail if no external AI API key is configured. | P0 |

### 6.5 REST API (`app.py`)

| Req ID | Requirement | Priority |
|---|---|---|
| API-01 | `GET /` — Serve the embedded web dashboard HTML. | P0 |
| API-02 | `POST /api/match` — Accept `BuyerRequirement` JSON body, return `SearchResponse`. | P0 |
| API-03 | `POST /api/parse-rfq` — Accept `{"text": "..."}` body, return extracted `BuyerRequirement`. | P0 |
| API-04 | `POST /api/simulate-contention` — Accept `ContentionSimulationRequest`, return `ContentionSimulationResponse`. | P0 |
| API-05 | `GET /api/audit-data` — Return the list of all records with non-empty `data_quality_flags` and their anomaly details. | P0 |
| API-06 | All endpoints must return `Content-Type: application/json`. The dashboard endpoint returns `Content-Type: text/html`. | P0 |
| API-07 | The API must support CORS for local development. | P1 |

### 6.6 CLI (`cli.py`)

| Req ID | Requirement | Priority |
|---|---|---|
| CLI-01 | `match` subcommand: accepts `--material`, `--process`, `--qty`, `--weeks`, `--certs`, `--destination`, `--memo` flags and prints formatted match results. | P1 |
| CLI-02 | `simulate-conflict` subcommand: runs the Buyer A vs Buyer B contention scenario with `--strategy pareto_optimal` or `--strategy fcfs`. | P1 |
| CLI-03 | `inspect-dirty-data` subcommand: prints the full anomaly audit log. | P1 |
| CLI-04 | `parse-rfq` subcommand: accepts a text string argument and prints the extracted `BuyerRequirement`. | P1 |

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Req ID | Requirement | Target |
|---|---|---|
| PERF-01 | End-to-end `/api/match` response time for a 1,000-record dataset. | ≤ 30 ms (p99) |
| PERF-02 | Data pipeline ingestion time (startup). | ≤ 1,000 ms |
| PERF-03 | Contention simulation (simultaneous two-buyer resolution). | ≤ 100 ms |
| PERF-04 | RFQ text parsing. | ≤ 500 ms |

### 7.2 Reliability and Determinism

| Req ID | Requirement |
|---|---|
| REL-01 | Given identical `BuyerRequirement` input and identical `as_of_date`, the system must return bit-exact identical output across all invocations and all machines. |
| REL-02 | The system must not raise unhandled exceptions for any combination of valid input field values. |
| REL-03 | The system must not return an empty result set without explanation. The relaxed fallback (ME-08) guarantees a response for all valid queries. |

### 7.3 Auditability

| Req ID | Requirement |
|---|---|
| AUD-01 | Every manufacturer disqualification must produce an explicit, human-readable reason string (e.g., `"Quantity 1,500 < MOQ 2,000"`). |
| AUD-02 | Every score component must be individually inspectable in the API response. |
| AUD-03 | Every data anomaly correction must be traceable via `data_quality_flags` on the manufacturer record. |

### 7.4 Concurrency

| Req ID | Requirement |
|---|---|
| CONC-01 | The allocation ledger must be thread-safe. Concurrent session writes must not produce race conditions or capacity miscounts. |
| CONC-02 | Session state must be fully isolated. Session A's requirement changes must not affect Session B's eligible pool. |

---

## 8. Data Model and Schema

### 8.1 BuyerRequirement

The structured input schema for all matching requests.

| Field | Type | Required | Description |
|---|---|---|---|
| `session_id` | `string` | No (default: `"session-default"`) | Unique session identifier for state isolation |
| `buyer_name` | `string` | No (default: `"Buyer"`) | Company or buyer identifier |
| `material` | `string` | **Yes** | Target material (e.g., `"aluminium"`, `"stainless steel"`) |
| `process` | `string` | **Yes** | Target process keyword (e.g., `"machined"`, `"CNC milling"`, `"sheet metal"`) |
| `quantity` | `integer` | **Yes** | Batch order quantity in units (must be > 0) |
| `timeline_weeks` | `integer` | **Yes** | Maximum acceptable lead time in weeks (must be > 0) |
| `required_certifications` | `list[string]` | No | Mandatory certifications (e.g., `["ISO 9001"]`) |
| `as_of_date` | `date` | No (default: `2026-10-28`) | Deterministic temporal anchor for certificate validity |
| `destination_country` | `string` | No (default: `"Germany"`) | Destination for logistics context |
| `custom_weights` | `dict` | No | Override the five scoring dimension weights |

### 8.2 CleanedManufacturer

The sanitized, enriched manufacturer record produced by the data pipeline.

| Field | Type | Description |
|---|---|---|
| `manufacturer_id` | `string` | Surrogate unique key (resolves CSV ID collisions) |
| `raw_id` | `string` | Original manufacturer_id from source CSV |
| `name` | `string` | Manufacturer trading name |
| `city`, `state`, `state_name` | `string` | Geographic location |
| `full_address` | `string` | Complete address string |
| `contact_email`, `website` | `string` | Contact information |
| `founded_year`, `employee_count` | `integer` | Firmographic data |
| `capacity_units_per_month` | `integer` | Declared monthly production capacity |
| `capacity_tier` | `string` | Categorical tier: `Small`, `Medium`, `Large` |
| `processes` | `list[string]` | All manufacturing processes offered |
| `primary_process` | `string` | Lead process for this facility |
| `materials` | `list[string]` | All materials the facility can work |
| `certifications` | `list[string]` | All held quality certifications |
| `certification_expiry` | `date` | Expiry of the primary certification |
| `last_audit_date` | `date` | Date of last formal factory audit |
| `min_order_qty`, `max_order_qty` | `integer` | Order quantity bounds |
| `lead_time_weeks`, `lead_time_days` | `float` | Production lead time |
| `export_experience_years` | `integer` | Years of international export history |
| `on_time_delivery_pct` | `float` | Sanitized OTD percentage (clamped to ≤ 100.0) |
| `raw_on_time_delivery_pct` | `float` | Original OTD percentage before clamping |
| `delivery_rating` | `string` | Letter rating: `A`, `B`, or `C` |
| `status` | `string` | Operational status: `Active` or `Inactive` |
| `data_quality_flags` | `list[string]` | Anomaly tags: `OTD_CLAMPED`, `LEAD_TIME_IMPUTED`, etc. |

### 8.3 ScoreBreakdown

| Field | Type | Weight | Description |
|---|---|---|---|
| `speed_score` | `float (0–100)` | 30% | Lead-time margin against buyer deadline |
| `reliability_score` | `float (0–100)` | 25% | Historical OTD performance and delivery rating |
| `capacity_score` | `float (0–100)` | 20% | Order batch fit within monthly capacity |
| `export_score` | `float (0–100)` | 15% | International export maturity |
| `audit_score` | `float (0–100)` | 10% | Recency of formal factory audit |
| `total_score` | `float (0–100)` | — | Composite weighted score |

---

## 9. Scoring and Matching Algorithm

### 9.1 Stage 1 — Hard Gatekeeper Logic

All six gates are applied sequentially. A single failure disqualifies the manufacturer and records the reason string.

```
for each manufacturer M in sanitized_dataset:
    if M.status != "Active":                        → DISQUALIFIED: "Manufacturer is not active"
    if buyer.material not in M.materials:           → DISQUALIFIED: "Material mismatch"
    if no overlap(buyer.process, M.processes):      → DISQUALIFIED: "No matching process capability"
    if buyer.quantity < M.min_order_qty:            → DISQUALIFIED: f"Quantity {qty} < MOQ {moq}"
    if buyer.quantity > M.max_order_qty:            → DISQUALIFIED: f"Quantity {qty} > Max {max}"
    if any cert missing from M.certifications:      → DISQUALIFIED: f"Missing certification: {cert}"
    if M.certification_expiry < (as_of_date + lead_time_days):
                                                    → DISQUALIFIED: "Certificate expires during production"
    else:
        → ELIGIBLE — proceed to Stage 2
```

### 9.2 Stage 2 — Multi-Attribute Utility Theory (MAUT) Scoring

**Speed Score (30%)**
$$\text{speed\_score} = \min\left(100, \max\left(0, \frac{(\text{timeline\_weeks} - \text{lead\_time\_weeks})}{\text{timeline\_weeks}} \times 100\right)\right)$$

**Reliability Score (25%)**  
$$\text{reliability\_score} = 0.6 \times \text{on\_time\_delivery\_pct} + 0.4 \times \text{rating\_points}$$
where `rating_points`: A=100, B=80, C=50.

**Capacity Score (20%)**

| Utilisation Ratio | Score |
|---|---|
| < 5% (under-committed) | 40 |
| 5% – 40% (optimal Goldilocks zone) | 100 |
| 40% – 70% (high but viable) | 60 |
| > 70% (overloaded risk zone) | 20 |

**Export Score (15%)**
$$\text{export\_score} = \frac{\text{export\_experience\_years}}{\max(\text{export\_years across dataset})} \times 100$$

**Audit Score (10%)**

| Months since last audit | Score |
|---|---|
| ≤ 12 months | 100 |
| 12 – 24 months | 70 |
| 24 – 36 months | 40 |
| > 36 months | 10 |

**Total Score**
$$\text{total} = 0.30s + 0.25r + 0.20c + 0.15e + 0.10a$$

### 9.3 Pareto-Optimal Contention Resolution

When two buyers (A and B) submit simultaneous requests and share at least one eligible manufacturer:

1. Compute independent top-1 matches for A and B without capacity constraints.
2. Detect all manufacturers appearing in **both** eligible pools (shared candidates).
3. For each shared manufacturer S:
   - Check if `combined_demand (A.qty + B.qty) > S.monthly_capacity`.
   - If yes: contention detected.
4. Apply Pareto optimisation:
   - Find the buyer with the **narrowest alternative pool** (fewest other eligible manufacturers).
   - That buyer retains the shared manufacturer.
   - The other buyer is re-allocated to their next-best non-contested manufacturer.
5. Report `combined_demand`, `capacity_utilization_pct`, chosen `resolution_strategy`, and a plain-language `explanation` of the trade-off.

> [!IMPORTANT]
> Under FCFS, if Buyer A locks the shared manufacturer first, Buyer B may receive zero eligible suppliers. Pareto-optimal allocation guarantees both buyers receive a valid allocation in all tested scenarios.

---

## 10. API Specification

### `POST /api/match`

**Request Body:** `BuyerRequirement`

**Response:** `SearchResponse`

```json
{
  "session_id": "session-german-buyer",
  "requirement": { ... },
  "as_of_date": "2026-10-28",
  "total_manufacturers_evaluated": 1000,
  "eligible_count": 32,
  "matches": [
    {
      "manufacturer": { "name": "Indus Ridge Machine Works", "city": "Aurangabad", ... },
      "score_breakdown": {
        "speed_score": 95.2,
        "reliability_score": 91.4,
        "capacity_score": 100.0,
        "export_score": 88.0,
        "audit_score": 100.0,
        "total_score": 93.8
      },
      "explanation": {
        "summary": "Indus Ridge Machine Works (Aurangabad, MH) scores 93.8/100. 4-week lead time provides a 2-week logistics buffer before your 6-week deadline.",
        "key_strengths": ["Grade A delivery rating (97.7% OTD)", "ISO 9001 valid through 2028", "23 years export experience"],
        "risks_and_tradeoffs": [],
        "capacity_utilization_pct": 7.7,
        "lead_time_margin_weeks": 2.0,
        "cert_validity_status": "VALID"
      },
      "eligible": true,
      "disqualification_reasons": []
    }
  ],
  "relaxed_matches": null,
  "query_delta_notes": null
}
```

### `POST /api/parse-rfq`

**Request Body:** `{ "text": "..." }`

**Response:** `BuyerRequirement`

```json
{
  "text": "We need 2500 milled aluminium parts with ISO 9001 in 6 weeks for Stuttgart"
}
```

### `POST /api/simulate-contention`

**Request Body:** `ContentionSimulationRequest`

**Response:** `ContentionSimulationResponse`

Key fields in response:
- `conflict_detected`: `true` / `false`
- `shared_manufacturer_id`: ID of the bottleneck factory
- `capacity_utilization_pct`: combined demand as % of monthly capacity
- `buyer_a_allocated`, `buyer_b_allocated`: final allocations after resolution
- `explanation`: plain-language trade-off narrative

### `GET /api/audit-data`

**Response:** Array of all `CleanedManufacturer` records where `data_quality_flags` is non-empty, with full flag details.

---

## 11. User Interface Requirements

### 11.1 Design Language

| Attribute | Specification |
|---|---|
| **Typography** | Alegreya (Google Fonts) for headings and body; `Georgia, serif` system fallback |
| **Colour Palette** | Background: `#0a0e1a` (deep navy); Surface: `#10172a`; Border: `#1e2d4a`; Accent: `#c9a84c` (gold); Text: `#e8e4d9` (warm white) |
| **Icon Usage** | **None.** No emoji, no icon fonts, no Unicode symbols. All labels are formal text. |
| **Tone** | Formal, enterprise B2B. No informal language, no exclamation marks in UI labels. |

### 11.2 Navigation Tabs

| Tab Label | Functionality |
|---|---|
| `MANUFACTURER MATCHING` | Primary matching form with preset scenario buttons and results table |
| `RFQ TEXT PARSER` | Freeform text input for natural language RFQ parsing |
| `MULTI-BUYER CONTENTION` | Pareto vs FCFS toggle, simultaneous buyer simulation, resolution display |
| `DATA QUALITY AUDIT (40)` | Table of all 40 cleaned anomalies with before/after values and flag types |

### 11.3 Preset Scenario Buttons

Formal button labels — no abbreviations, no emojis:

- `Scenario 1: German Industrial Buyer (2,000 Aluminium CNC, 6 Weeks)`
- `Scenario 2: Buyer A — Aluminium CNC (1,000 units, 6 Weeks)`
- `Scenario 3: Buyer B — Stainless Sheet Metal (1,500 units, 6 Weeks)`

### 11.4 Match Result Display

For each result card, the dashboard must display:

- Manufacturer name, city, state
- `total_score` prominently (formatted to 1 decimal place)
- Five individual score bars (speed, reliability, capacity, export, audit)
- `lead_time_margin_weeks` statement
- `capacity_utilization_pct`
- `cert_validity_status`
- `key_strengths` list (formal prose, no bullets-with-emojis)
- `data_quality_flags` if non-empty (displayed as audit badges)

---

## 12. Testing and Quality Assurance

### 12.1 Test Suite Coverage

The repository ships with 22 automated tests across 5 test files. All 22 must pass with zero failures before any commit reaches `main`.

| Test File | Tests | Coverage |
|---|---|---|
| `test_data_pipeline.py` | 5 | Ingestion, duplicate ID resolution, OTD clamping, lead-time imputation, CSV export |
| `test_matching_engine.py` | 5 | German buyer scenario, hard-filter process gating, MOQ/max bounds, determinism, in-flight deltas |
| `test_allocation_manager.py` | 2 | Pareto Buyer A/B resolution, capacity reservation depletion |
| `test_ai_service.py` | 3 | German NLP RFQ parsing, stainless sheet-metal parsing, executive memo generation |
| `test_deep_stress_and_edge_cases.py` | 7 | Multi-threaded concurrency (10 threads × 5 queries), latency benchmark (<30ms), zero-result graceful fallback, invalid session isolation, certificate boundary conditions, data determinism across restarts, edge-case material synonyms |

### 12.2 Key Test Assertions

| Test | Assertion |
|---|---|
| Duplicate ID resolution | Exactly 20 surrogate-keyed records exist, 0 raw ID collisions remain |
| OTD clamping | All `on_time_delivery_pct` values ≤ 100.0; clamped records have `OTD_CLAMPED` in flags |
| Lead-time imputation | Zero NaN values in `lead_time_weeks` post-pipeline; imputed records have `LEAD_TIME_IMPUTED` flag |
| German buyer scenario | Top match `total_score` ≥ 90.0 and `lead_time_margin_weeks` > 0 |
| Matching determinism | Two identical calls return identical `total_score` and identical manufacturer rank order |
| Pareto contention | Both Buyer A and Buyer B receive `eligible: true` allocations; zero starved buyers |
| Latency benchmark | 100 sequential matching queries complete in < 3,000 ms total (< 30ms each) |
| Concurrency safety | 10 threads × 5 queries produce no race conditions, no shared-state corruption |

### 12.3 Running the Test Suite

```bash
cd veridia-matcher
python -m pytest -v tests/
```

Expected result: `22 passed in ≤ 3.00s`

---

## 13. Failure Modes and Edge Cases

| Scenario | System Behaviour |
|---|---|
| Zero manufacturers pass Stage 1 hard filters | Activate relaxed fallback (ME-08). Return closest candidates with explicit disqualification annotations. Never return an empty response without explanation. |
| Buyer quantity is between two suppliers' MOQ ranges (no exact fit) | Stage 1 correctly disqualifies both. Relaxed fallback presents the closest options. `query_delta_notes` advises the buyer on quantity adjustments. |
| Buyer requests a certification not held by any manufacturer in dataset | Hard filter disqualifies all. Relaxed fallback omits certification check and returns closest matches with a `"Certification unavailable"` advisory. |
| `timeline_weeks = 1` (extremely tight deadline) | `speed_score` will be 0 or near-0 for most suppliers. System returns results ranked by reliability and capacity instead. The buyer sees transparent score breakdowns. |
| Both Buyer A and Buyer B require the same single-source specialist | Pareto allocator identifies the narrower-pool buyer, preserves that allocation, and redirects the other buyer to their next-best match with a full explanation. |
| `lead_time_weeks` imputed via median is longer than buyer's timeline | Imputed-record supplier is disqualified at Stage 1 on timeline grounds. The `LEAD_TIME_IMPUTED` flag is visible in the audit tab. |
| `certification_expiry` is exactly equal to `as_of_date + lead_time_days` | The certificate is deemed valid (boundary-inclusive check: `expiry >= deadline`). |
| Concurrent writes to capacity reservation ledger | Thread lock ensures atomic reads and writes. No capacity miscounting under concurrent load. |

---

## 14. Success Metrics and KPIs

### 14.1 Operational KPIs (Production)

| KPI | Definition | Target |
|---|---|---|
| **Match Acceptance Rate (MAR)** | % of recommended top-3 suppliers for which the buyer issues a formal RFQ | ≥ 75% |
| **Lead Time Accuracy (LTA)** | Variance between predicted factory lead time and actual physical dispatch date | ≤ ± 4 days |
| **Contention Collision Rate (CCR)** | Incidents per month where concurrent buyer demand exceeds a factory's monthly capacity | 0 (enforced by allocation engine) |
| **Data Hygiene Resolution Rate (DHRR)** | % of anomalous supplier records flagged and resolved before buyer presentation | 100% (automated pipeline) |
| **Query Latency (p99)** | 99th percentile end-to-end `/api/match` response time | ≤ 30 ms |

### 14.2 Technical Quality Gates

| Gate | Requirement | Current Status |
|---|---|---|
| Automated test pass rate | 100% (22/22) | PASSING |
| OTD clamping coverage | 100% of records with OTD > 100% | RESOLVED (10 records) |
| Duplicate ID resolution | 100% of collision pairs disambiguated | RESOLVED (10 pairs) |
| Missing lead-time imputation | 100% of NaN rows imputed | RESOLVED (10 records) |
| Zero unsafe exception paths | All edge cases return valid responses | VERIFIED |

---

## 15. Out of Scope

The following items were explicitly considered and excluded from this version:

| Item | Rationale |
|---|---|
| **Real-time pricing or cost estimation** | Requires 3D CAD/STEP model analysis (tool paths, tolerance classes, billet scrap rates). Quoting without this is irresponsible in precision engineering. |
| **Vector embedding or neural matching** | Cannot enforce hard mathematical constraints. Not auditable for international supply chain compliance. |
| **Automated purchase order execution** | Requires drawing sign-off, NDAs, MTCs, and First Article Inspection (FAIR) — outside the scope of a matching tool. |
| **Freight and logistics cost estimation** | Freight rates are dynamic. A stale rate table adds false precision. |
| **Supplier self-service onboarding** | Separate operational product with its own document management requirements. |
| **Mobile-native UI** | The web dashboard is functional on mobile browsers but not optimised for it. |
| **Multi-language UI** | The dashboard is English-only. RFQ parser handles German input text. |

---

## 16. Appendix — Dataset Anomaly Catalogue

### Source Dataset: `data/veridia_csv.csv`
- **Total Records:** 1,000
- **Total Anomalous Records:** 40 (4.0% of dataset)
- **Post-Sanitization Records:** 1,000 (no records dropped)

### Anomaly Type 1 — Manufacturer ID Collisions

| Count | Original IDs Affected | Resolution |
|---|---|---|
| 10 collision pairs (20 records) | VM1092, VM1429, and 8 others | Surrogate keys: `{id}-FACILITY-1`, `{id}-FACILITY-2` |

**Business Impact:** Without disambiguation, key collisions cause one record to silently overwrite the other in dictionary-based lookups, permanently erasing 10 factories representing significant manufacturing capacity from the eligible pool.

### Anomaly Type 2 — Physically Impossible OTD Percentages

| Count | Range of Invalid Values | Resolution |
|---|---|---|
| 10 records | 100.1% to 142.6% | Clamped to 100.0%; `raw_on_time_delivery_pct` preserved; `OTD_CLAMPED` flag appended |

**Business Impact:** Without clamping, records like VM1429 (OTD: 142.6%) receive a disproportionately high `reliability_score`, unfairly outcompeting factories with legitimate 98.5% OTD records. Clamping eliminates this distortion while preserving the factory's discoverable capacity.

**Why not drop?** Dropping 10 records removes over 150,000 units of monthly capacity due to a data entry typo. Their processes, ISO certifications, and founding years are completely valid.

### Anomaly Type 3 — Missing Lead Times (NaN)

| Count | Imputation Method |
|---|---|
| 10 records | Median `lead_time_weeks` across all records sharing the same `primary_process` |

**Business Impact:** A NaN `lead_time_weeks` causes a Python comparison operator crash during Stage 1 timeline gating. Without imputation, these 10 factories are invisible to all buyers. Imputing with process-group medians is statistically defensible and operationally conservative.

### Anomaly Type 4 — Certificate Temporal Boundary Risk

| Check | Logic |
|---|---|
| Certificate validity | `certification_expiry >= as_of_date + lead_time_days` |

**Business Impact:** Standard date checks compare expiry against today. A factory with an ISO 9001 certificate expiring in 3 weeks but a 4-week lead time is non-compliant by the time of dispatch — but passes a naive `expiry > today` check. This system's production-window-inclusive check catches that scenario.

---

*End of Document*

---

**Document Version History**

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-10-29 | Product Engineering, Veridia | Initial release — complete PRD for production system |
