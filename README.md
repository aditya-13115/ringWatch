<div align="center">

<img src="frontend/public/favicon.svg" alt="RingWatch" width="96" />

# RingWatch

### Explainable Detection and Investigation of Coordinated Refund Abuse Rings

A defense-only risk investigation platform that combines behavioral signals, identity relationships, machine learning, graph analysis, SHAP explainability, evidence gaps, bounded actions, Razorpay Test Mode data, and audit trails.

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=flat-square)
![Vite](https://img.shields.io/badge/Vite-Build%20Tool-646CFF?style=flat-square)
![LightGBM](https://img.shields.io/badge/ML-LightGBM-green?style=flat-square)

</div>

---

## Razorpay Buildathon — Track 02: AI Risk Manager

**Project:** RingWatch  
**Loss class:** Coordinated post-delivery refund/return abuse  
**Mode:** Defense-only, human-in-the-loop

RingWatch is designed to answer a practical merchant question:

> **Which accounts should an investigator review before refund/return abuse becomes a larger loss, and what evidence supports that review?**

The system is intentionally not an autonomous punishment engine. Model output is a prioritization signal; consequential actions remain bounded and reviewable.

---

## What it solves

Single-account fraud scoring misses coordinated behavior. RingWatch combines account behavior with relationships between accounts that share strong identifiers such as devices, phones, payment instruments, addresses, IP prefixes, and rare coupons.

The investigation workflow is:

```text
Data / Razorpay Test Mode
        |
        v
Cutoff-safe feature preparation
        |
        +----------------------+
        |                      |
        v                      v
Behavioral + identity      Account graph
signals                    + communities
        |                      |
        +----------+-----------+
                   v
             V4 Ensemble
        LightGBM B + GNN
                   |
                   v
          Ranked investigation queue
                   |
          +--------+--------+---------+
          |                 |         |
          v                 v         v
        SHAP             Graph     Evidence
     explanation        context      gaps
          |                 |         |
          +--------+--------+---------+
                   |
                   v
            AI investigation
                   |
                   v
          Deterministic policy
                   |
                   v
       Bounded recommendation
                   |
                   v
              Audit trail
```

### AI judgment

The risk score is produced by the trained model. The investigator layer is used for evidence gathering and case synthesis, not as the primary fraud classifier. The final action remains controlled by deterministic policy and human review.

---

# Current operating model

The current production/demo scoring configuration is the **V4 Ensemble**:

```text
LightGBM B (tuned)
        +
GNN (FraudSAGE)
        |
        v
Average probability
        |
        v
Validation-selected threshold
        |
        v
Investigation queue
```

The tested operating threshold is **0.6831**.

LightGBM A (tuned) is retained for feature-sensitivity/ablation analysis. Graph analysis remains independently useful for investigation even where graph features are not the dominant predictive signal.

---

# Held-out evaluation

The final V4 evaluation uses a **4,499-account held-out test set**. The split keeps complete abuse rings together rather than allowing members of the same ring to leak across train/validation/test.

### V4 Ensemble test results

| Metric | Result |
|---|---:|
| Precision | **35.64%** |
| Recall | **48.21%** |
| F1 | **40.99%** |
| PR-AUC | **44.43%** |
| ROC-AUC | **84.06%** |
| False positives | **195** |
| False negatives | **116** |
| True positives | **108** |
| True negatives | **4,080** |
| Modeled intervention cost | **₹21.30 lakh** |

The cost model uses:

```text
False positive cost = ₹2,000
False negative cost = ₹15,000
```

The persisted rule baseline is:

| Metric | Rule baseline |
|---|---:|
| Precision | 5.52% |
| Recall | 22.47% |
| F1 | 8.86% |
| False positives | 5,767 |
| False negatives | 1,163 |
| Modeled intervention cost | ₹2.90 crore |

That corresponds to approximately **92.6% lower modeled intervention cost** for the V4 Ensemble than the current persisted rule baseline.

> These are measured synthetic-data results. RingWatch does not claim that synthetic performance transfers directly to production.

---

# Dataset

The final synthetic environment contains:

| Property | Value |
|---|---:|
| Accounts | 30,000 |
| Normal accounts | 28,500 |
| True ring members | 1,500 |
| Positive rate | 5% |
| Abuse rings | 140 |
| Orders | 70,027 |
| Refunds | 7,158 |
| Disputes | 570 |
| Ring orders | 4,352 |
| Hard-negative accounts | 4,500 |
| Hard-negative orders | 18,000 |

The generated environment includes several abuse families, including wardrobing, promotion/refund farming, friendly-fraud-like behavior, and subtle distributed patterns.

Validation checks include schema integrity, timestamps, foreign keys, graph structure, missing values, forbidden columns, cutoff boundaries, ground-truth isolation, and leakage checks.

Current validation results include:

```text
Foreign-key failures: 0
Duplicate IDs:        0
Timestamp violations: 0
```

---

# Feature engineering

Features are cutoff-aware: a prediction at time `T` can only use information that would have been available at `T`.

### Behavioral signals

Examples:

```text
total_orders
total_amount
avg_order_value
total_delivered_orders
orders_last_24h
orders_last_7d
orders_last_30d
refund_rate
return_rate
dispute_rate
discount_dependency_score
transaction_burst_score
refund_burst_score
account_creation_burst_score
```

### Identity / relationship signals

```text
distinct_devices
distinct_addresses
distinct_phones
distinct_payment_instruments
accounts_per_device
accounts_per_address
accounts_per_phone
accounts_per_instrument
shared_device_count
shared_address_count
shared_phone_count
shared_instrument_count
shared_ip_prefix_count
```

### Graph signals

```text
degree_centrality
eigenvector_centrality
triangle_count
clustering_coefficient
connected_component_size
shared_edge_count
shared_edge_weight_sum
community_id
community_size
community_return_rate
community_refund_rate
community_avg_order_value
```

---

# Ring / community investigation

RingWatch keeps persisted community assignments from the processed graph artifact and exposes the community ID on graph nodes. The Rings page uses those assignments when available and falls back to connected components only for older artifacts.

The UI supports:

- top **3 / 6 / 15** community highlighting
- selecting an individual community
- selected-ring emphasis in the graph
- highest-risk member navigation
- flagged-member count
- internal relationship count
- strongest configured relationship
- strongest-edge weight
- relationship-type filters
- account search
- zoom/reset controls

The selected-ring panel explicitly explains that relationship weights are evidence-prioritization heuristics, not proof of coordinated abuse.

---

# Strongest-edge explanation

For each investigated account, RingWatch surfaces the strongest configured relationship and the linked account when available.

Example:

```text
Strongest configured relationship
shared device

A025455 → A005374
weight 1.00

The weight is an evidence-prioritization heuristic,
not proof of abuse.
```

This keeps the graph explanation concrete without turning a heuristic relationship weight into a causal claim.

---

# Explainability

RingWatch uses SHAP for account-level model attribution.

```text
Model prediction
      |
      v
     SHAP
      |
      +----> Top contributing features
      |
      +----> Investigation explanation
```

The application explicitly treats SHAP as model attribution, not causal explanation.

---

# Feature ablation

A reproducible held-out feature-sensitivity benchmark is stored at:

```text
data/v4_realistic_30k/processed/model/feature_ablation_test.json
```

It uses the tuned LightGBM A component, keeps the same held-out accounts, replaces one feature at a time with its population median, and rescoreds the same model.

The benchmark is exposed through:

```text
GET /api/metrics/feature-ablation
```

The account investigation page also shows top-feature sensitivity for the selected account.

**Important:** feature ablation measures model sensitivity. It is not a causal claim and is not the V4 Ensemble's score.

To regenerate the global benchmark:

```powershell
uv run python -m generator.feature_ablation
```

---

# Evidence gaps

RingWatch uses Razorpay-aligned evidence names where applicable:

```text
proof_of_service
explanation_letter
refund_confirmation
access_activity_log
refund_cancellation_policy
terms_and_conditions
```

The system distinguishes:

```text
AVAILABLE
MISSING
NO_DISPUTE_YET
```

A missing evidence field is not presented as actionable when no dispute existed at the prediction cutoff.

---

# AI Investigator

The investigator is a bounded evidence-gathering layer.

```text
Account ID
   |
   v
Pre-execute guaranteed evidence tools
   |
   v
Evidence packet
   |
   v
LLM investigator (optional)
   |
   v
Structured investigation result
   |
   v
Deterministic action policy
   |
   v
Audit trail
```

Implemented investigation tools include:

| Tool | Source |
|---|---|
| `get_related_accounts` | Graph evidence |
| `get_shared_attributes` | Feature repository |
| `check_evidence_availability` | Evidence artifact |
| `calculate_financial_exposure` | Feature repository |
| `get_account_timeline` | Event repository |
| `get_merchant_policy` | Merchant policy map |

If an LLM is unavailable, RingWatch falls back to a deterministic investigation path rather than failing the case entirely.

---

# Bounded actions / defense-only behavior

RingWatch does not autonomously ban customers, seize funds, permanently block accounts, or automatically deny legitimate refunds.

The intended policy flow is:

```text
CRITICAL
  → priority human investigation
  → evidence review
  → temporary defensive controls where appropriate

HIGH
  → human review
  → evidence verification

MEDIUM
  → step-up verification / evidence collection

LOW
  → monitor / continue normal processing
```

The AI investigator is advisory. The deterministic policy layer remains the action authority.

---

# Audit trail

The audit UI records both prediction and investigation context.

In addition to the original decision fields, the API exposes auditability references including:

```text
input_data_hash
threshold_used
feature_snapshot
evidence_subgraph
human_decision
outcome
error_path
```

The `input_data_hash` is a stable SHA-256 reference of the recorded decision context; it is not a replacement for a production event-store hash.

Human decisions are explicitly shown as `NOT_RECORDED` when no real human decision has been entered, rather than being fabricated by the system.

---

# Razorpay integration

RingWatch includes a Test Mode Razorpay fetch path.

```text
Razorpay Test API
       |
       v
Original Test Mode payment records
       |
       v
Displayed unchanged in the demo
```

The failure demo is intentionally separated from the original-record display path. Synthetic malformed records are used to demonstrate quarantine behavior.

Current Razorpay mapping used by the project includes:

```text
order.created / order.paid       → order data
payment.captured                 → amount
refund.processed                 → refund information
dispute.created / updated        → dispute lifecycle
merchant metadata                → device/address relationship fields
```

Full live webhook ingestion is **not required for the Track 02 detector bar** and is not part of the current demo path.

---

# Failure / quarantine demo

The synthetic failure path demonstrates controlled degradation:

```text
Synthetic Razorpay-shaped batch
        |
        v
Controlled malformed rows
        |
        v
Validation
        |
   +----+----+
   |         |
   v         v
Quarantine  Valid rows
   |         |
   v         v
Human       Continue
review      processing
   \         /
    \       /
     v     v
       Audit
```

The original Razorpay Test Mode fetch path never injects faults into the returned records.

A backward-compatible `POST /api/failure-demo` alias is also retained for older demo scripts; the explicit endpoints are:

```text
POST /api/failure-demo/razorpay
POST /api/failure-demo/razorpay-synthetic
```

---

# Architecture

A standalone diagram is also available at [`docs/architecture.md`](docs/architecture.md).


### Backend

```text
FastAPI
  |
  +--> API routers
  |
  +--> Services
  |      |
  |      +--> queue / account / graph / evidence
  |      +--> investigator / actions / reports
  |      +--> audit / metrics / failure / address
  |
  +--> Repositories
  |      |
  |      +--> features
  |      +--> events
  |      +--> explainability artifacts
  |
  v
Processed V4 artifacts
```

### End-to-end risk flow

```text
Razorpay / synthetic records
          |
          v
Canonical account/event data
          |
          +------------------+
          |                  |
          v                  v
   Behavioral features   Relationship graph
          |                  |
          +--------+---------+
                   v
          V4 Ensemble scoring
                   |
                   v
         Investigation queue
                   |
        +----------+----------+
        |          |          |
        v          v          v
       SHAP      Graph      Evidence
        |          |          |
        +----------+----------+
                   |
                   v
            AI Investigator
                   |
                   v
         Deterministic Policy
                   |
                   v
          Human-review action
                   |
                   v
              Audit log
```

---

# Repository structure

```text
RingWatch/
├── backend/
│   ├── api/
│   ├── core/
│   ├── domain/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── tests/
│   └── main.py
│
├── data/
│   └── v4_realistic_30k/
│       ├── *.csv
│       └── processed/
│           ├── model/
│           └── explainability/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   └── pages/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── generator/
│   ├── feature_ablation.py
│   ├── features.py
│   ├── graph_features.py
│   ├── rings.py
│   ├── lightgbm.py
│   ├── lightgbm_tuned.py
│   ├── ensemble.py
│   └── validate.py
│
├── notebooks/
├── scripts/
├── pyproject.toml
├── README.md
└── razorpay_test_batch.json
```

---

# Setup

## Backend

From the repository root:

```powershell
uv sync
uv run uvicorn backend.main:app --reload
```

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

Expected:

```json
{
  "status": "ok",
  "service": "RingWatch API",
  "version": "1.0.0"
}
```

## Frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Default URL:

```text
http://localhost:5173
```

Optional backend override:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

# Production frontend build

The frontend now includes the complete Vite build configuration:

```text
frontend/index.html
frontend/package.json
frontend/vite.config.js
frontend/tailwind.config.js
frontend/postcss.config.js
```

Build with:

```powershell
cd frontend
npm install
npm run build
```

Preview with:

```powershell
npm run preview
```

The expected output directory is:

```text
frontend/dist/
```

**Build verification note:** the source was syntax-checked in this environment, but the npm registry was unavailable during dependency installation, so a real `vite build` could not be executed here. Run the command above on a normal networked checkout before submission.

---

# Testing

Backend API tests:

```powershell
uv run pytest -q backend/tests/test_api.py
```

The current test suite covers health/readiness, queue behavior, account details, graph endpoints, investigation behavior, audit access, and failure-demo compatibility.

The latest local run completed with:

```text
16 passed
```

The address-normalization file is a standalone diagnostic script rather than a pytest test module.

---

# Useful API endpoints

```text
GET  /health
GET  /ready
GET  /api/queue
GET  /api/accounts/{account_id}
GET  /api/accounts/{account_id}/graph
GET  /api/accounts/{account_id}/feature-ablation
POST /api/accounts/{account_id}/investigate
GET  /api/graph/overview
GET  /api/evidence/{account_id}
GET  /api/audit
GET  /api/metrics
GET  /api/metrics/feature-ablation
GET  /api/metrics/curves
POST /api/failure-demo/razorpay
POST /api/failure-demo/razorpay-synthetic
POST /api/address/normalize
```

---

# Five-minute demo script

The demo should be rehearsed as a single investigator workflow rather than a tour of every page.

### 0:00–0:40 — Problem

Explain that account-level scoring misses coordinated refund abuse and that RingWatch prioritizes relationships and evidence before a merchant loses more money.

### 0:40–1:20 — Detection

Open the dashboard and show the ranked queue. Open a high-risk account.

### 1:20–2:30 — Ring investigation

Show:

```text
risk score
→ selected community
→ graph relationships
→ strongest relationship
→ SHAP contributors
→ feature sensitivity
```

### 2:30–3:25 — Evidence + AI

Show the Razorpay-aligned evidence fields, run the investigator, and show the case report/tool trace.

### 3:25–4:00 — Bounded action

Show the recommendation and explicitly point out that the system does not autonomously ban/block the customer.

### 4:00–4:35 — Failure

Run the synthetic malformed-batch demo. Show quarantine, valid-row continuation, human-review routing, and audit logging.

### 4:35–5:00 — Metrics

Finish with the held-out precision/recall and the modeled cost comparison against the rule baseline.

---

# What broke and how it was recovered

The project has deliberately retained failure and integration lessons rather than presenting a perfect-looking prototype.

Examples include:

- frontend white-screen/runtime failures caused by missing imports and graph data-shape mismatches
- queue API contract mismatches between limits and total counts
- LLM dependency availability without an API key/package
- malformed external-style records requiring quarantine rather than silent processing
- stale investigation data requiring versioned local-storage handling

The current implementation keeps deterministic fallbacks where an optional LLM dependency is unavailable and quarantines malformed synthetic input before it can enter downstream processing.

---

# Limitations

1. **Synthetic data:** the reported model metrics are not production performance.
2. **Ring-aware, not future-time validated:** the current V4 headline evaluation should be described as a ring-aware held-out test, not as a future-time generalization result.
3. **Community IDs:** the UI uses the persisted community artifact; community quality therefore depends on graph construction quality.
4. **Relationship weights:** weights prioritize evidence and are not causal proof.
5. **Feature ablation:** median replacement measures model sensitivity, not causality.
6. **Razorpay integration:** the current demo uses Test Mode fetching; live webhook ingestion is not implemented.
7. **Human decisions:** the demo records audit context but does not fabricate a human approval decision.

---

# Submission-readiness checklist

```text
[x] Synthetic 30K dataset
[x] Cutoff-aware feature engineering
[x] Graph construction
[x] Rule baseline
[x] LightGBM A / B
[x] GNN
[x] V4 Ensemble selection
[x] Held-out precision / recall
[x] False-positive cost
[x] Ring/community visualization
[x] Ring-first selection/highlighting
[x] Strongest-edge explanation
[x] SHAP
[x] Held-out feature ablation
[x] Evidence gaps
[x] AI investigator
[x] Bounded actions
[x] Failure/quarantine path
[x] Razorpay Test Mode fetch/display
[x] Auditability fields
[x] Architecture documentation
[x] Judge-facing README
[x] Frontend build configuration
[x] Backend API tests
[ ] Networked npm install + final `npm run build` verification
[ ] Final 5-minute pitch recording/rehearsal
[ ] Public GitHub submission
```

---

# Design principles

### Human-in-the-loop

Model output is an investigation signal, not an automatic punishment.

### Explainability

A high score should lead to inspectable evidence, relationships, and model attribution.

### Leakage awareness

Features must only use information available at the prediction cutoff.

### Evidence before action

A score alone is not treated as sufficient evidence.

### Bounded actions

Recommendations remain defensive, reversible, and reviewable.

### Honest evaluation

More complex modeling is not automatically treated as better. The V4 Ensemble is the operating model because it produced the strongest tested combination in the current evaluation, while the graph remains valuable for investigation.

### Investigability over raw accuracy

The central product goal is:

```text
Detect
  ↓
Prioritize
  ↓
Explain
  ↓
Investigate
  ↓
Verify evidence
  ↓
Recommend a bounded action
  ↓
Record the decision
```

---

# License

Add the project's chosen license before publishing the repository publicly.

---

# Acknowledgements

RingWatch was developed as an end-to-end exploration of:

- synthetic fraud-ring generation
- temporal/cutoff-aware feature engineering
- heterogeneous relationship graphs
- gradient-boosted tree models
- graph neural networks
- SHAP explainability
- feature sensitivity analysis
- evidence-driven investigation
- human-in-the-loop decision workflows
- FastAPI application architecture
- React investigation interfaces
- Razorpay Test Mode integration
