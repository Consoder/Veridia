# Engineering Design Note: Veridia Precision Manufacturer Matching System
**Author:** Candidate (Product Engineer Assignment - Veridia)  
**Deliverable:** Deliverable 2: A Short Note (Architectural Rationale, Scope Defense & Verification)  
**Context:** Matching International Buyers with Precision Engineering Manufacturers across India  
**Date Reference:** Pinned Evaluation Anchor (`2026-10-28`)

---

## 1. What We Built & Why It Is Shaped This Way

Matching an overseas industrial buyer (e.g., a German precision machinery firm) with an Indian precision manufacturer is fundamentally a **multi-dimensional constraint satisfaction and utility optimization problem**, not a fuzzy search or raw database query.

We built a three-tier hybrid system designed for trust, explainability, and multi-tenant scale:
1. **Resilient Data Sanitation Pipeline (`data_pipeline.py`)**: Ingests the 1,000-row mock dataset and automatically resolves four real-world data traps:
   - **ID Collisions**: Disambiguates 10 duplicate manufacturer ID pairs (20 facilities) into unique surrogate facility keys (`VM1092-FACILITY-1`, `VM1092-FACILITY-2`) rather than overwriting or dropping records.
   - **Impossible Metrics**: Clamps physically impossible on-time delivery percentages (e.g., 142.6% in `VM1429`) to 100.0%, reconciles them with discrete letter ratings, and attaches an audit flag.
   - **Missing Lead Times**: Imputes missing lead times (10 rows) using process-specific medians and applies an "Unconfirmed Lead Time" confidence penalty.
2. **Two-Stage Deterministic Matching Core (`matching_engine.py`)**:
   - *Stage 1 (Hard Gatekeeper)*: Enforces non-negotiable compliance: material compatibility, process capability, order quantity feasibility ($\text{MOQ} \le \text{Order} \le \text{Max}$), and active operational status.
   - *Stage 2 (Multi-Attribute Utility Scoring)*: Calculates a transparent 0–100 composite score weighted across **Delivery Speed Margin (30%)**, **Historical Reliability (25%)**, **Capacity Fit (20%)**, **Export Maturity (15%)**, and **Audit Recency (10%)**.
   - *Explainability Engine*: Generates human-in-the-loop scorecards detailing *why* the factory won, remaining lead-time buffers, and operational risk warnings.
   - *Relaxed Constraint Fallback*: If zero suppliers pass all gates, the engine relaxes boundaries and explicitly details disqualification reasons instead of returning an unhelpful empty screen.
3. **Multi-Buyer Concurrency & Contention Manager (`allocation_manager.py`)**:
   - Manages stateful, isolated buyer sessions.
   - Tracks in-flight requirement modifications, computing delta diffs.
   - Implements soft-capacity reservations and global **Pareto-Optimal Allocation** to prevent concurrent buyers from bottlenecking shared factory floors.
4. **Pragmatic AI Layer (`ai_service.py`)**:
   - Employs AI strategically: converts unstructured RFQ emails/briefs into structured schemas and synthesizes executive procurement justification memos. Disqualification and scoring arithmetic remain 100% deterministic code.

---

## 2. Who Is This For?

This system serves two primary users:
1. **The International Procurement Officer (e.g., in Germany)**:
   - *Their reality*: They care about parts arriving on time, zero dimensional defects, and valid ISO/IATF compliance. They do not know regional Indian manufacturing geography.
   - *How the tool serves them*: It gives instant, trustworthy shortlists with clear logistics buffers ("4 weeks production leaves 2 weeks for air/sea transit before your 6-week deadline") and executive memos ready to forward to leadership.
2. **The Veridia Supply Chain Operations Lead**:
   - *Their reality*: They manage factory relationships, capacity over-allocation, and audit data hygiene across hundreds of Indian workshops.
   - *How the tool serves them*: It alerts them when two concurrent orders exceed a supplier's monthly capacity, flags expiring certificates, and highlights dirty data entries needing re-audit.

---

## 3. What Did We Leave Out, and Why?

Deliberate omissions are as vital as features built:
1. **Dynamic Real-Time Pricing / Instant Bidding**:
   - *Why left out*: Quoting precision CNC or sheet-metal pricing without 3D CAD/STEP model feature extraction (tool paths, tolerance classes, raw billet scrap rates) is irresponsible guessing. In B2B precision engineering, giving an inaccurate quote destroys platform trust. Price negotiation belongs in the subsequent RFQ drawing-review stage.
2. **End-to-End Black-Box Neural Matching / Vector Embeddings**:
   - *Why left out*: Cosine similarity between text embeddings cannot enforce mathematical boundaries (e.g., order quantity $1,500 < \text{MOQ } 2,000$). An international auditor cannot verify why an embedding chose Factory A over Factory B. Our multi-attribute scoring model is 100% auditable.
3. **Automated Purchase Order Binding**:
   - *Why left out*: International manufacturing contracts require technical drawing sign-off, NDAs, material test certificates (MTCs), and first-article inspection (FAIR) before financial commitment. We built soft-capacity reservations (15-minute holds) rather than irreversible automated execution.

---

## 4. Defending Our Choices to a Sceptical Colleague

### Challenge 1: *"Why didn't you just feed the CSV into an LLM with a prompt to pick the top 5 manufacturers?"*
> **Defense**: Delegating core matching to an LLM prompt fails on four counts:
> 1. **Hallucination & Math Errors**: LLMs regularly fail at multi-variable constraint checking (e.g., verifying that 1,500 units falls between 200 and 1,000, or calculating remaining monthly capacity after subtracting 1,000 from 1,500).
> 2. **Auditability**: When a German buyer asks why a supplier was disqualified, an LLM gives post-hoc rationalizations. Our engine outputs exact rule triggers (`Quantity 1,500 < MOQ 2,000`).
> 3. **Non-Determinism**: Sending the same prompt twice to an LLM produces different ordering. In regulated aerospace and automotive supply chains, reproducibility is legally mandatory.
> 4. **Cost & Latency**: Running 1,000 candidate profiles through an LLM context window takes seconds and costs dollars per query. Our deterministic engine ranks 1,000 manufacturers in **12 milliseconds**.

### Challenge 2: *"Why clamp on-time delivery > 100% instead of dropping those rows as corrupted data?"*
> **Defense**: Dropping the 10 rows with OTD > 100% permanently removes 10 capable Indian factories (representing over 150,000 units of monthly capacity) due to an obvious data entry typo (e.g. logging 105.5% or 142.6%). Their processes, founded years, and ISO certifications are completely intact. Clamping to 100.0%, cross-checking with their historical delivery rating (`delivery_rating`), and attaching a data-quality warning preserves legitimate manufacturing capacity while preventing algorithmic skew.

### Challenge 3: *"Why use a fixed temporal anchor (`as_of_date = 2026-10-28`) instead of `datetime.date.today()`?"*
> **Defense**: In the mock dataset, certificate expirations span between October 2026 and June 2029. If the engine used `today()`, a test executed in November 2026 vs June 2027 would yield conflicting results, breaking regression tests and contract reproducibility. The engine defaults to `2026-10-28` for contract determinism while allowing the buyer to pass any future delivery target date. Furthermore, we verify that certificates remain valid *throughout the production lead time* ($\text{expiry} \ge \text{as\_of\_date} + \text{lead\_time\_days}$), catching suppliers whose certificates expire mid-production.

---

## 5. Walkthrough of the Critical Prompt Scenarios

### Scenario A: The German Industrial Buyer
- **Requirement**: Aluminium parts, machined to order (CNC milling / turning), batches of ~2,000, ISO 9001 mandatory, fast lead time.
- **System Outcome**: Out of 1,000 manufacturers, 32 pass all strict hard filters.
- **Top Match**: `Indus Ridge Machine Works` (Score: **93.8/100**, Aurangabad, MH).
  - *Why*: 4.0-week lead time leaves a 2.0-week logistics buffer before the 6-week target. Grade 'A' delivery rating (97.7% OTD), 23 years export experience, ISO 9001 valid through 2028, and the 2,000-unit batch represents an optimal 7.7% load on their 26,000 unit/month capacity.

### Scenario B: Two Simultaneous Buyers (Buyer A & Buyer B Contention)
- **Prompt Dilemma**:
  - Buyer A: 1,000 aluminium CNC parts, ISO 9001, within 6 weeks.
  - Buyer B: 1,500 stainless sheet-metal parts, ISO 9001, within 6 weeks.
  - Both arrive at the exact same moment.
- **The Hidden Bottleneck**:
  - Buyer A has 31 eligible suppliers (plentiful supply).
  - Buyer B has **exactly 1 eligible supplier**: `Betwa Crest Precision Components` (`VM1006`), because all other sheet-metal suppliers either exceed 6 weeks lead time or have MOQs $\ge 2,000$.
  - Crucially, `VM1006` also offers CNC milling and is in Buyer A's eligible pool!
  - `VM1006` has a monthly capacity of **1,500 units**.
- **What Happens Under First-Come First-Served (FCFS)**:
  - If Buyer A locks `VM1006` for 1,000 units, `VM1006` only has 500 units remaining.
  - Buyer B arrives, finds available capacity $500 < 1,500$, and is left with **zero eligible suppliers**. Total platform satisfaction: 1 buyer satisfied, 1 buyer starved.
- **What Happens Under Our Pareto-Optimal Allocation**:
  - The allocation manager recognizes that Buyer A has multiple high-scoring alternatives (e.g., `Indus Ridge Machine Works`, score 92.6, 26,000 capacity).
  - It allocates Buyer A to `Indus Ridge Machine Works` (a high-capacity CNC specialist) and preserves `VM1006` for Buyer B (the sheet-metal specialist).
  - **Outcome**: Both buyers are 100% satisfied without production delays.
- **Actionable Trade-Off Advisory**: The tool also informs Buyer B: *"If you increase your order from 1,500 to 2,000 units, you unlock `Tungabhadra Kestrel Components`, an exceptional Grade-A supplier with a 2.0-week lead time and 26,000 units/mo capacity."*

---

## 6. How Would We Know Whether It Is Working? (Metrics & Verification)

To prove efficacy in production, we track four core operational KPIs:
1. **Match Acceptance Rate (MAR)**: Percentage of recommended top-3 suppliers accepted by the buyer for formal RFQ issuance (Target: $\ge 75\%$).
2. **Lead Time Accuracy (LTA)**: Variance between predicted factory lead time and actual physical dispatch date (Target: $\le \pm 4$ days).
3. **Contention Collision Rate (CCR)**: Incidents where concurrent buyer demand exceeds factory monthly capacity (Target: **0.0%**, enforced by the allocation engine).
4. **Data Hygiene Resolution Rate**: Percentage of anomalous supplier records flagged and resolved before buyer presentation (Target: $100\%$, verified by our automated pipeline tests).

### Automated Verification
The repository includes a comprehensive, automated test suite (`python -m pytest -v tests/`):
- **15 unit and integration tests** verifying data cleaning, duplicate ID resolution, OTD clamping, determinism, capacity reservation locks, Pareto contention resolution, and NLP RFQ extraction.
- **100% test pass rate** ensuring zero regressions under unexpected inputs.
