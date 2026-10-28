# Veridia Precision Manufacturer Matching System
> High-precision supplier matching engine connecting international industrial buyers with precision engineering manufacturers across India.

Built for the **Product Engineer Assignment - Veridia**.

---

## 🚀 Key Highlights & Capabilities

- **Resilient Data Sanitation Pipeline**: Ingests the 1,000-row mock dataset (`veridia_csv.csv`), resolving duplicate manufacturer IDs into distinct surrogate facility keys, clamping physically impossible OTD percentages (>100%), and imputing missing lead times using process-level medians.
- **Two-Stage Deterministic Matching Core**: Hard compliance gatekeeper (process, material, MOQ/Max bounds, active status, valid certifications) followed by a 5-factor weighted utility scoring engine (Speed 30%, Quality 25%, Capacity 20%, Export 15%, Audit 10%).
- **Simultaneous Buyer Contention Resolution**: Implements global **Pareto-Optimal Allocation** to solve the Buyer A vs Buyer B arrival dilemma, preventing concurrent buyers from starving single-source factory capacities.
- **Contract-Grade Determinism**: Uses a fixed temporal evaluation anchor (`as_of_date = 2026-10-28`) ensuring bit-exact reproducibility for supply chain audits and verifying certificate validity through the production lead-time window.
- **Strategic AI Layer**: Natural language RFQ extraction (converts messy emails to structured specifications) and executive procurement memorandum generation, backed by a zero-dependency offline fallback.
- **Multi-Tenant Session & In-Flight Delta Tracking**: Real-time diffing when buyers adjust parameters midway, explaining the operational impact on eligible supplier pools.
- **Interactive Web Dashboard & Rich CLI**: Beautiful, zero-build-step Tailwind/Alpine dashboard and comprehensive command-line interface.

---

## 📁 Repository Structure

```
veridia-matcher/
├── data/
│   ├── veridia_csv.csv              # Provided mock dataset (1,000 manufacturers)
│   └── sanitized_manufacturers.csv  # Cleaned, deduplicated dataset with audit flags
├── src/
│   ├── __init__.py
│   ├── config.py                    # Constants, canonical synonym maps, scoring weights
│   ├── models.py                    # Pydantic schemas (BuyerRequirement, CleanedManufacturer, etc.)
│   ├── data_pipeline.py             # Data ingestion, duplicate resolver, OTD clamper, imputation
│   ├── matching_engine.py           # Hard filters, multi-factor scoring, explainability, delta notes
│   ├── allocation_manager.py        # Concurrency, capacity reservation locks, Buyer A/B contention
│   ├── ai_service.py                # NLP RFQ parser & executive pitch generator
│   ├── cli.py                       # Rich Command-Line Interface
│   └── app.py                       # FastAPI server & embedded procurement dashboard UI
├── tests/
│   ├── test_data_pipeline.py        # Tests for duplicate IDs, OTD clamping, NaN imputation
│   ├── test_matching_engine.py      # Tests for hard filters, determinism, scoring math
│   ├── test_allocation_manager.py  # Tests for Buyer A/B contention & capacity locks
│   └── test_ai_service.py           # Tests for NLP RFQ parsing & executive memos
├── DELIVERABLE_2_SHORT_NOTE.md      # The required 2-page architectural defense note
├── IDEA.md                          # Comprehensive problem deconstruction & master strategy
├── requirements.txt                 # Python dependencies
└── README.md                        # Documentation & quickstart guide
```

---

## ⚡ Quickstart Guide (< 2 Minutes)

### 1. Prerequisites & Installation
Ensure you have Python 3.11+ installed.

```bash
# Clone or navigate to the repository
cd veridia-matcher

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch the Interactive Web Dashboard
Start the local server and open your browser:

```bash
python -m src.app
```
Then navigate to: **`http://127.0.0.1:8000`**

#### What you can do in the Web Dashboard:
- 🎯 **Interactive Matcher**: Test 1-click presets (German Buyer, Buyer A, Buyer B), adjust batch sliders, view score breakdowns, and reserve factory capacity.
- 🤖 **AI RFQ Parser**: Paste freeform buyer emails in German or English; watch the AI extract structured specifications and find top matches.
- ⚡ **Buyer A vs B Contention**: Toggle between **Pareto Optimal** and **FCFS** allocation to see how the engine resolves capacity competition.
- 🔍 **Data Quality Audit**: Inspect the 40 cleaned anomalies in the dataset with before/after values and sanitation tags.

---

## 💻 Command-Line Interface (CLI) Usage

The tool includes a robust CLI for scripted queries, CI pipelines, and automated evaluations:

### 1. Match the German Industrial Buyer
```bash
python -m src.cli match --material aluminium --process machined --qty 2000 --weeks 6 --certs "ISO 9001" --destination "Germany" --memo
```

### 2. Simulate the Buyer A vs Buyer B Simultaneous Arrival Dilemma
```bash
python -m src.cli simulate-conflict --strategy pareto_optimal
```

### 3. Inspect Data Quality & Anomalies in `veridia_csv.csv`
```bash
python -m src.cli inspect-dirty-data
```

### 4. Parse Freeform Unstructured RFQ Text
```bash
python -m src.cli parse-rfq "We need 2500 milled aluminium parts with ISO 9001 in 6 weeks for our Stuttgart assembly plant"
```

---

## 🧪 Automated Test Suite

Run the full pytest suite (15 unit and integration tests covering data cleaning, capacity reservation, determinism, and AI parsing):

```bash
python -m pytest -v tests/
```

Expected output:
```
tests/test_ai_service.py::test_nlp_rfq_parsing_german_scenario PASSED
tests/test_ai_service.py::test_nlp_rfq_parsing_stainless_sheet_metal PASSED
tests/test_ai_service.py::test_executive_pitch_synthesis PASSED
tests/test_allocation_manager.py::test_two_buyer_contention_pareto_resolution PASSED
tests/test_allocation_manager.py::test_capacity_reservation_and_depletion PASSED
tests/test_data_pipeline.py::test_pipeline_ingestion PASSED
tests/test_data_pipeline.py::test_duplicate_id_resolution PASSED
tests/test_data_pipeline.py::test_otd_percentage_clamping PASSED
tests/test_data_pipeline.py::test_missing_lead_time_imputation PASSED
tests/test_data_pipeline.py::test_export_sanitized_csv PASSED
tests/test_matching_engine.py::test_german_buyer_scenario PASSED
tests/test_matching_engine.py::test_hard_gatekeeper_process_filtering PASSED
tests/test_matching_engine.py::test_order_quantity_moq_and_max PASSED
tests/test_matching_engine.py::test_matching_determinism PASSED
tests/test_matching_engine.py::test_in_flight_requirement_delta_tracking PASSED
============================== 15 passed in 3.09s ==============================
```

---

## 📊 Dataset Forensics (The 40 Anomalies Cleaned)

| Anomaly Identified | Occurrences | Sanitation Technique | Business Benefit |
| :--- | :--- | :--- | :--- |
| **Manufacturer ID Collisions** | 10 pairs (20 facilities) | Disambiguated into surrogate keys (`VM1092-FACILITY-1`, `VM1092-FACILITY-2`) | Eliminates key collisions without discarding real factory capacity |
| **OTD Outliers (> 100%)** | 10 records (up to 142.6%) | Clamped to 100.0%, reconciled with delivery rating, flagged for audit | Prevents algorithmic ranking distortion caused by data entry errors |
| **Missing Lead Times (`NaN`)** | 10 records | Imputed using process-level median lead times + unconfirmed confidence tag | Prevents crash on comparison operators and keeps suppliers discoverable |
| **Expired Certificates** | Dates starting Oct 2026 | Verified using deterministic temporal anchor (`as_of_date` + lead-time buffer) | Protects buyers from suppliers whose certs expire mid-production |

---

## 📄 Deliverable 2: Architectural Defense Note

Please refer to **[`DELIVERABLE_2_SHORT_NOTE.md`](DELIVERABLE_2_SHORT_NOTE.md)** for the complete 2-page engineering note addressing:
1. Architectural structure and target personas (International Procurement Managers & Veridia Supply Chain Leads).
2. What was intentionally excluded (dynamic price guessing, uninterpretable neural vector search, automated PO execution) and why.
3. Sceptical colleague defense (defending deterministic matching over LLM prompts, clamping vs dropping corrupted records, and fixed temporal anchors).
4. Walkthrough of the German Buyer and simultaneous Buyer A vs Buyer B contention scenarios.
5. Verification strategy and operational success metrics (Match Acceptance Rate, Lead Time Variance, Contention Collision Rate).
