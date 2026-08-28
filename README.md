<div align="center">

<img src="frontend/public/favicon.svg" alt="RingWatch" width="96" />

# RingWatch

### Explainable Detection and Investigation of Coordinated Refund Abuse Rings

A defense-oriented fraud investigation platform combining behavioral signals, identity relationships, machine learning, graph analysis, SHAP explainability, evidence gaps, bounded actions, and audit trails.

<br />

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=flat-square)
![Vite](https://img.shields.io/badge/Vite-Build%20Tool-646CFF?style=flat-square)
![LightGBM](https://img.shields.io/badge/ML-LightGBM-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)

</div>

---

## Overview

RingWatch is an explainable, defense-only fraud investigation system designed to detect coordinated post-delivery refund and return abuse.

Instead of treating fraud detection as a simple binary classification problem, RingWatch is designed around the workflow an investigator actually needs:

```text
Data
  |
  v
Cutoff-safe Features
  |
  v
Behavioral + Identity Signals
  |
  v
LightGBM Model A
  |
  v
Ranked Investigation Queue
  |
  +-------------------+
  |                   |
  v                   v
SHAP Explanation     Graph Evidence
  |                   |
  +---------+---------+
            |
            v
       Evidence Gaps
            |
            v
       Case Report
            |
            v
     Bounded Action
            |
            v
        Audit Trail
```

The system is intentionally designed to support **human investigation rather than automatic punitive decisions**.

---

## Key Features

- Behavioral risk detection using LightGBM
- Identity and account relationship features
- Synthetic 30K-account investigation dataset
- Account-level investigation queue
- Risk tiers:
  - CRITICAL
  - HIGH
  - MEDIUM
  - LOW
- Risk scores displayed as percentages
- SHAP-based explanations
- Account relationship graphs
- Graph evidence and community information
- Evidence-gap detection
- Investigation case reports
- Bounded action recommendations
- Human review workflow
- Audit logging
- Failure/quarantine demonstration
- Address normalization workflow
- Model evaluation and metrics dashboard
- Leakage and data-quality validation
- Ring-aware evaluation
- Hard-negative accounts for more realistic evaluation

---

# Project Goals

RingWatch is designed around five major questions:

### 1. Why was this account flagged?

The model provides a ranked risk score and SHAP-based feature explanations.

### 2. What relationships does the account have?

The investigation layer exposes relationships through devices, addresses, phones, payment instruments, IP prefixes, and graph-derived evidence.

### 3. What evidence is actually available?

The evidence layer identifies missing or incomplete evidence rather than assuming that a suspicious model score is sufficient.

### 4. What should an investigator do?

The system provides bounded recommendations rather than irreversible automated enforcement.

### 5. What happened during the investigation?

Actions and investigation events can be represented through the audit trail.

---

# Current Modeling Decision

RingWatch contains two LightGBM models:

```text
Model A
Behavioral + Identity features

Model B
Behavioral + Identity + Graph features
```

The project currently uses **Model A as the operational model**.

Model B remains available for evaluation and comparison.

The reason is empirical: the behavioral and identity representation already provides extremely strong predictive performance on the validated synthetic dataset, while the tested graph-enhanced model did not provide sufficient incremental predictive value to justify making it the primary operational model.

The project therefore keeps graph analysis primarily as an **investigation and evidence mechanism**, rather than forcing graph features into the operational model.

---

# Dataset

RingWatch uses a synthetic relational dataset designed to model coordinated refund/return abuse.

The final dataset contains:

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

Validation results:

```text
Foreign-key failures: 0
Duplicate IDs:        0
Timestamp violations: 0
```

The project originally used a 1K dataset as a development/debug checkpoint before scaling to the final 30K dataset.

The 1K dataset is retained as development history and is not the final modeling dataset.

---

# Data Model

The raw dataset contains multiple relational entities:

```text
accounts
addresses
devices
disputes
orders
payment_instruments
phones
refunds
ring_ground_truth
```

These entities are used to construct behavioral and identity relationships.

The generator is responsible for creating the synthetic dataset and remains the source of truth for dataset generation.

---

# Feature Engineering

RingWatch uses cutoff-aware features.

A feature is not simply:

```text
return_rate
```

It is:

```text
return_rate as known at prediction time T
```

This distinction prevents future information from leaking into the model.

The feature pipeline includes:

### Behavioral features

Examples include:

```text
total_orders
total_amount
avg_order_value
total_delivered_orders
total_failed_orders
total_pending_orders
orders_last_24h
orders_last_7d
orders_last_30d
refund_rate
return_rate
dispute_rate
discount_dependency_score
transaction_burst_score
refund_burst_score
```

### Identity features

Examples include:

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

### Graph features

The graph pipeline produces additional structural information such as:

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
community_total_orders
```

---

# Machine Learning

RingWatch uses LightGBM for supervised classification.

## Model A

```text
Behavioral features
        +
Identity features
        |
        v
     LightGBM
        |
        v
Risk score
```

Model A is the current operational model.

## Model B

```text
Behavioral features
        +
Identity features
        +
Graph features
        |
        v
     LightGBM
```

Model B is retained for comparison and ablation analysis.

---

# Explainability

The explainability pipeline produces account-level investigation artifacts.

```text
Model Prediction
      |
      v
     SHAP
      |
      +-------------------+
      |                   |
      v                   v
Top Features        SHAP Summary
      |
      v
Investigator
```

Generated artifacts include:

```text
shap_values_test.csv
shap_summary.png
```

The SHAP layer helps answer:

> Which model features contributed most to this account's score?

The system does not treat SHAP explanations as causal explanations. They are model-attribution signals intended to support investigation.

---

# Investigation Layer

The investigation workflow combines multiple forms of evidence.

```text
                    Account
                       |
       +---------------+---------------+
       |               |               |
       v               v               v
   Model Score       SHAP           Graph
       |               |               |
       +---------------+---------------+
                       |
                       v
                Evidence Status
                       |
                       v
                  Case Report
                       |
                       v
                Bounded Action
                       |
                       v
                   Audit Log
```

This makes the application more than a model prediction dashboard.

---

# Risk Tiers

RingWatch exposes four operational risk tiers:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

Risk scores are displayed to users as percentages.

For example:

```text
0.8734
```

is presented as:

```text
87.34%
```

The frontend does not invent independent probability ranges to classify the account.

The risk tier and model score are treated as separate pieces of information.

---

# Bounded Actions

RingWatch is intentionally human-in-the-loop.

The system should not automatically:

```text
Ban an account
Block an account
Deny a legitimate refund
Seize funds
Automatically reject a customer
```

Instead, recommendations are designed to support investigation and controlled review.

Examples of the intended workflow include:

```text
CRITICAL
    |
    v
Priority human investigation
    +
Evidence review
    +
Temporary defensive controls where appropriate

HIGH
    |
    v
Human review
    +
Evidence verification

MEDIUM
    |
    v
Additional monitoring / evidence collection

LOW
    |
    v
Continue normal processing
```

The exact recommendation is generated by the bounded-action layer.

---

# Architecture

RingWatch follows a layered backend architecture.

```text
                    FastAPI
                       |
              +--------+--------+
              |                 |
            API Layer        Middleware
              |
              v
          Services
              |
       +------+------+
       |             |
       v             v
 Repositories      Domain
       |             |
       +------+------+
              |
              v
        Processed Data
```

## Backend layers

### API

HTTP endpoints and request/response handling.

```text
backend/api/
```

### Core

Application configuration, middleware, logging, exceptions, and concurrency utilities.

```text
backend/core/
```

### Domain

Domain-level models and concepts.

```text
backend/domain/
```

### Repositories

Access to processed datasets and explainability artifacts.

```text
backend/repositories/
```

### Schemas

Pydantic request/response models.

```text
backend/schemas/
```

### Services

Application/business logic.

```text
backend/services/
```

### Tests

Backend API and normalization tests.

```text
backend/tests/
```

---

# Frontend

The frontend is implemented using React and Vite.

```text
React
  |
  v
Pages
  |
  +-------------------------------+
  |               |               |
  v               v               v
Components       API Layer       Utilities
  |               |
  |               v
  |             FastAPI
  |
  v
Investigation UI
```

## Main pages

```text
Landing
Dashboard
Account Investigation
Human Review Queue
Rings
Metrics
Audit Log
Failure Demo
Address Normalization
About
Verification Workflow
```

## Main components

```text
ActionWorkflow
Badge
Card
ErrorBoundary
GraphView
Layout
LineChart
```

---

# Frontend API Layer

The frontend has dedicated API modules:

```text
frontend/src/api/

account.js
address.js
audit.js
client.js
failure.js
graph.js
metrics.js
queue.js
```

The API client uses:

```javascript
const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
```

This means the default backend address is:

```text
http://localhost:8000
```

A different backend URL can be configured through:

```text
frontend/.env
```

with:

```env
VITE_API_BASE_URL=http://localhost:8000
```

After changing the environment variable, restart the Vite development server.

---

# Repository Structure

```text
RingWatch/
│
├── backend/
│   ├── api/
│   ├── core/
│   ├── domain/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── tests/
│   ├── dependencies.py
│   └── main.py
│
├── data/
│   ├── v1_1k/
│   │   └── ...
│   │
│   └── v3_scaled_30k/
│       ├── accounts.csv
│       ├── addresses.csv
│       ├── devices.csv
│       ├── disputes.csv
│       ├── orders.csv
│       ├── payment_instruments.csv
│       ├── phones.csv
│       ├── refunds.csv
│       ├── ring_ground_truth.csv
│       │
│       └── processed/
│           ├── explainability/
│           ├── model/
│           ├── account_graph_edges.csv
│           ├── baseline_metrics.json
│           ├── communities.csv
│           ├── features_accounts.csv
│           ├── features_graph.csv
│           └── leakage reports
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── utils/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── generator/
│   ├── address_utils.py
│   ├── config.py
│   ├── entities.py
│   ├── features_config.py
│   ├── features.py
│   ├── generate_dataset.py
│   ├── graph_features.py
│   ├── ground_truth.py
│   ├── hard_negatives.py
│   ├── ids.py
│   ├── lightgbm.py
│   ├── normal_orders.py
│   ├── refunds_disputes.py
│   ├── ring_ablation.py
│   ├── rings.py
│   └── validate.py
│
├── notebooks/
│   ├── day6_7_lightgbm_evaluation.ipynb
│   ├── day8_9_explainability.ipynb
│   └── ringwatch_30k_model_investigation.ipynb
│
├── .env
├── example.env
├── .gitignore
├── .python-version
├── main.py
├── pyproject.toml
├── README.md
└── uv.lock
```

---

# Prerequisites

Install the following before running RingWatch:

- Python
- `uv`
- Node.js
- npm

The repository includes:

```text
.python-version
pyproject.toml
uv.lock
package.json
package-lock.json
```

so the Python and frontend environments can be reproduced from the repository configuration.

---

# Backend Setup

Open a terminal in the RingWatch project root.

```powershell
cd RingWatch
```

Install/synchronize the Python environment:

```powershell
uv sync
```

Then start FastAPI:

```powershell
uv run uvicorn backend.main:app --reload
```

The backend runs by default at:

```text
http://127.0.0.1:8000
```

Keep this terminal running.

---

# Frontend Setup

Open a second terminal.

```powershell
cd RingWatch/frontend
```

Install frontend dependencies:

```powershell
npm install
```

Start the Vite development server:

```powershell
npm run dev
```

The frontend runs by default at:

```text
http://localhost:5173
```

Open the URL in a browser.

Both servers need to remain running:

```text
Terminal 1
FastAPI
http://localhost:8000

Terminal 2
Vite
http://localhost:5173
```

---

# Quick Start

For a fresh checkout:

### Terminal 1

```powershell
cd RingWatch
uv sync
uv run uvicorn backend.main:app --reload
```

### Terminal 2

```powershell
cd RingWatch/frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

---

# Backend Health Check

Once the backend is running, verify it with:

```powershell
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "RingWatch API",
  "version": "1.0.0"
}
```

If the health endpoint works but the dashboard does not load, inspect the backend terminal first.

---

# API Endpoints

The backend exposes multiple investigation-oriented API groups.

```text
/api/accounts
/api/actions
/api/address
/api/audit
/api/evidence
/api/failure
/api/graph
/api/graph-overview
/api/health
/api/investigator
/api/metrics
/api/queue
/api/reports
/api/timeline
```

The most important operational endpoint is:

```text
GET /api/queue?limit=7
```

This provides the ranked investigation queue used by the dashboard.

---

# Queue Data Flow

The queue follows a clear separation between the data artifact, domain model, and API schema.

```text
bounded_actions_test.csv
          |
          | proba
          v
     QueueService
          |
          v
      AccountRisk
          |
          v
      QueueAccount
          |
          v
     QueueResponse
          |
          v
      /api/queue
          |
          v
       Dashboard
```

The API exposes:

```text
account_id
rank
proba
risk_tier
recommended_action
graph_links
evidence_gaps
```

---

# Processed Artifacts

The 30K processed dataset contains model and explainability artifacts.

## Model artifacts

```text
data/v3_scaled_30k/processed/model/

model_lgbm_A.pkl
model_lgbm_B.pkl
model_metrics.json
model_predictions_test.csv
model_leakage_report.txt
model_feature_importance.csv
model_a_feature_importance.csv
model_b_feature_importance.csv
ring_type_ablation.json
```

## Explainability artifacts

```text
data/v3_scaled_30k/processed/explainability/

bounded_actions_test.csv
case_reports_test.csv
evidence_gap_test.csv
graph_evidence_test.csv
investigation_audit_log.csv
shap_summary.png
shap_values_test.csv
graphs/
```

---

# Running the Notebooks

The repository contains three major notebooks:

```text
notebooks/day6_7_lightgbm_evaluation.ipynb
notebooks/day8_9_explainability.ipynb
notebooks/ringwatch_30k_model_investigation.ipynb
```

They represent different stages of the project.

## Day 6–7

Model evaluation:

```text
Feature preparation
       |
       v
Ring-aware split
       |
       v
LightGBM
       |
       +----------+
       |          |
       v          v
    Model A     Model B
       |          |
       +----------+
              |
              v
        Evaluation
```

## Day 8–9

Explainability and operational artifacts:

```text
Predictions
    |
    +--> SHAP
    |
    +--> Evidence gaps
    |
    +--> Graph evidence
    |
    +--> Case reports
    |
    +--> Bounded actions
    |
    +--> Investigation audit log
```

## Day 10–11

Application and investigation workflow:

```text
FastAPI
   +
React
   |
   v
Investigation Dashboard
```

---

# Data Generation

The `generator/` package is responsible for creating and validating the synthetic environment.

Important modules include:

```text
generate_dataset.py
entities.py
rings.py
features.py
graph_features.py
ground_truth.py
hard_negatives.py
lightgbm.py
validate.py
```

The generator is treated as the source of truth.

If a dataset-generation bug is found, the preferred workflow is:

```text
Fix generator
      |
      v
Regenerate dataset
      |
      v
Validate dataset
      |
      v
Regenerate downstream artifacts
```

rather than manually editing generated CSV files.

---

# Validation

Validation is an important part of the RingWatch pipeline.

The project checks:

```text
Schema
Timestamps
Foreign keys
Graph structure
Missing values
Forbidden columns
Cutoff boundaries
Ground-truth isolation
Feature leakage
```

The validated 30K dataset has:

```text
Foreign-key failures: 0
Duplicate IDs:        0
Timestamp violations: 0
```

The model pipeline also includes leakage reports and ring-aware evaluation.

---

# Testing

Backend tests are located at:

```text
backend/tests/
```

Current tests include:

```text
test_address_normalization.py
test_api.py
```

Run the test suite from the project root:

```powershell
uv run pytest
```

---

# Frontend Production Build

To create a production frontend build:

```powershell
cd frontend
npm run build
```

The generated build is placed in:

```text
frontend/dist/
```

To preview the production build locally:

```powershell
npm run preview
```

---

# Development Workflow

A typical development workflow is:

```text
1. Start backend
        |
        v
2. Start frontend
        |
        v
3. Open dashboard
        |
        v
4. Verify /health
        |
        v
5. Verify /api/queue
        |
        v
6. Test investigation workflow
        |
        v
7. Run backend tests
        |
        v
8. Build frontend
```

---

# Troubleshooting

## Dashboard shows "Failed to fetch"

First check that the backend is running:

```powershell
uv run uvicorn backend.main:app --reload
```

Then check:

```text
http://127.0.0.1:8000/health
```

If `/health` works, inspect:

```text
/api/queue
```

The frontend API client defaults to:

```text
http://localhost:8000
```

If the backend runs elsewhere, configure:

```env
VITE_API_BASE_URL=http://your-backend-host:port
```

and restart Vite.

---

## `/api/queue` returns 404

Verify that the FastAPI router is registered and that the frontend is calling:

```text
/api/queue
```

rather than:

```text
/queue
```

The intended API path is:

```text
GET /api/queue?limit=7
```

---

## `/api/queue` returns 500

Check the FastAPI terminal for the Python traceback.

The queue pipeline expects the processed action artifact to provide:

```text
account_id
rank
proba
risk_tier
recommended_action
```

The domain queue object and API response model must remain consistent.

---

# Design Principles

## 1. Human-in-the-loop

Model output is an investigation signal, not an automatic punishment.

## 2. Explainability

A high score should lead to an investigation workflow rather than a black-box decision.

## 3. Leakage awareness

Features must only use information available at the prediction cutoff.

## 4. Evidence before action

Model output alone is not treated as sufficient evidence.

## 5. Bounded actions

Recommendations should remain defensive, reversible, and reviewable.

## 6. Reproducibility

Generated data and processed artifacts should come from deterministic pipeline stages.

## 7. Honest evaluation

The project does not force graph features or more complex models into the final system simply because they are more sophisticated.

---

# Why LightGBM Instead of a GNN?

The project explored graph-based modeling.

The conclusion was not:

> GNNs are unnecessary for fraud detection.

The conclusion is specific to the current RingWatch dataset:

> Behavioral and identity features already contain enough predictive information for the current LightGBM system, and the tested graph-enhanced representation did not provide sufficient incremental value to justify introducing a GNN.

Therefore:

```text
LightGBM
    |
    +--> Model A
    |
    +--> Model B for comparison
```

is retained as the modeling path.

Graph analysis remains valuable for:

```text
Investigation
Relationship discovery
Community analysis
Evidence
Explainability
```

---

# Operational Model

The current production/demo path is:

```text
30K Dataset
     |
     v
Cutoff-safe Features
     |
     v
Behavioral + Identity Features
     |
     v
LightGBM Model A
     |
     v
Predictions
     |
     v
Investigation Queue
     |
     +-----------------------+
     |                       |
     v                       v
Risk Score              Risk Tier
     |                       |
     +-----------+-----------+
                 |
                 v
          Account Investigation
                 |
       +---------+---------+
       |         |         |
       v         v         v
      SHAP     Graph    Evidence
       |         |         |
       +---------+---------+
                 |
                 v
             Case Report
                 |
                 v
          Bounded Action
                 |
                 v
             Audit Log
```

---

# Security and Safety Considerations

RingWatch is intended as a defensive investigation system.

The application should not be used to automatically make irreversible decisions about customers based solely on model predictions.

A model score is a prioritization signal.

Investigation evidence, business rules, and human review should be considered before consequential actions.

---

# Current Project Status

```text
Dataset generation              Complete
30K dataset                     Complete
Data validation                 Complete
Behavioral features             Complete
Identity features               Complete
Graph construction              Complete
Graph features                  Complete
Rule baseline                   Complete
LightGBM evaluation             Complete
Model A                         Operational
Model B                         Evaluation / comparison
SHAP explainability             Complete
Evidence gaps                   Complete
Case reports                    Complete
Bounded actions                 Complete
Audit logging                   Complete
FastAPI backend                 Complete
React frontend                  Complete
Investigation dashboard         Complete
Failure demonstration          Complete
Address normalization           Complete
```

---

# Project Philosophy

RingWatch is not intended to be:

```text
"Give a model a dataset and display a fraud score."
```

The intended system is:

```text
Detect
  |
  v
Prioritize
  |
  v
Explain
  |
  v
Investigate
  |
  v
Verify Evidence
  |
  v
Recommend a Bounded Action
  |
  v
Record the Decision
```

The central design goal is therefore **investigability**, not merely prediction accuracy.

---

# License

Add the project's chosen license here before publishing the repository publicly.

For example:

```text
MIT License
```

if an MIT license is added to the repository.

---

# Acknowledgements

RingWatch was developed as an end-to-end exploration of:

- Synthetic fraud-ring generation
- Temporal feature engineering
- Graph-based relationship analysis
- Gradient-boosted tree models
- SHAP explainability
- Evidence-driven investigation
- Human-in-the-loop decision workflows
- FastAPI application architecture
- React investigation interfaces