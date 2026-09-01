# RingWatch

RingWatch is a defense-oriented investigation prototype for coordinated post-delivery refund and return abuse. It uses synthetic commerce data to identify suspicious account relationships, rank account and ring candidates, and present the evidence an investigator would need before recommending a bounded action.

The project is designed as an investigation layer: the model output prioritizes review. It does not automatically block customers, deny refunds, seize funds or make a final fraud determination.

## What is in this repository

RingWatch has two offline model layers and an artifact-backed application.

1. An account-risk layer builds cutoff-aware behavioral, identity and graph features, then evaluates LightGBM and GraphSAGE models. The current account-level operating artifact is the V4 ensemble of tuned LightGBM B and GraphSAGE.
2. A ring-candidate layer starts from high-risk accounts and strong account relationships, aggregates candidate-level evidence, and scores the resulting candidate groups with a LightGBM model.
3. A FastAPI service reads the generated data, saved scores, model artifacts and explainability outputs. A React/Vite frontend provides the dashboard and investigation views.

The project uses an offline synthetic dataset. The application reads persisted artifacts at runtime; it does not retrain models or recompute features in response to an API request.

## Repository layout

```text
RingWatch/
├── backend/              FastAPI routers, services, schemas and repositories
├── generator/            Synthetic generation, feature, graph and model pipelines
├── data/v4_realistic_30k/
│   ├── *.csv             Synthetic source tables
│   └── processed/        Features, graph, explanations and model artifacts
├── frontend/             React and Vite application
├── docs/architecture.md  Implemented architecture and runtime boundaries
├── scripts/              Razorpay-shaped batch helper
├── pyproject.toml        Python dependencies and pytest configuration
└── uv.lock               Locked Python environment
```

Older `v1_1k` and `v3_scaled_30k` directories are retained experiment artifacts. The application configuration points to `v4_realistic_30k`.

## Data and feature pipeline

`generator/realistic_engine.py` generates V4 source tables for accounts, devices, addresses, phones, payment instruments, orders, refunds and disputes. It also creates private synthetic ring ground truth for evaluation.

`generator/features.py` derives cutoff-aware account features, including:

- order, delivery, return, refund and dispute rates
- 24-hour, 7-day and 30-day activity windows
- transaction, refund and account-creation burst signals
- account reuse and diversity signals for devices, addresses, phones and instruments

`generator/graph_features.py` creates a weighted account projection from shared identifiers, derives graph statistics, runs Louvain community detection and writes the account graph and community assignments.

The relationship types used by the graph are:

| Relationship | Weight |
|---|---:|
| Shared device | 1.0 |
| Shared payment instrument | 1.0 |
| Shared phone | 1.0 |
| Shared address | 0.7 |
| Shared IP prefix | 0.3 |
| Shared rare coupon | 0.2 |

These weights are evidence-prioritization heuristics. They are not proof that accounts are controlled by the same person or that abuse occurred.

## Models

### Account-level risk models

The account pipeline is implemented in:

- `generator/lightgbm.py`: baseline LightGBM A/B training and evaluation
- `generator/lightgbm_tuned.py`: Optuna-tuned LightGBM variants
- `generator/gnn_model.py`: GraphSAGE training on the account graph
- `generator/ensemble.py`: tuned LightGBM B plus GraphSAGE ensemble

Saved account-model artifacts are used for the dashboard queue, account investigation information, account-graph context, metrics and explanations.

### Ring-candidate model

`generator/ring_model.py` implements a distinct ring-level candidate pipeline:

1. Score accounts using the saved tuned LightGBM B account model.
2. Build connected candidate groups around high-risk accounts over strong graph relationships.
3. Aggregate account risk, graph structure, transaction behavior, refunds, community context and exposure into one candidate feature row.
4. Train and evaluate a LightGBM ring-candidate model.
5. Save `ring_candidates.csv`, ring predictions, metrics, feature importance and the serialized model under `data/v4_realistic_30k/processed/model/`.

Synthetic ground-truth ring identifiers are used to construct labels and grouped train/validation/test splits. They are excluded from the ring-model feature set and are not returned by the ring API.

## Investigation application

The backend serves stored artifacts through FastAPI. Its primary responsibilities are:

- ranked account queue and account detail assembly
- graph and community evidence for an account or graph overview
- saved SHAP explanations, evidence gaps, reports and timelines
- deterministic bounded action recommendations
- optional Groq-assisted investigation summaries with a deterministic fallback
- audit-log and metrics presentation
- ring-candidate summaries and details
- address normalization and a separate failure/quarantine demonstration

The frontend includes dashboard, account investigation, network/ring exploration, metrics, audit log, live-operations, failure-demo and address-normalization views.

The human-review and verification pages are currently presentation workflows. Their buttons do not submit or persist reviewer decisions.

## API

Start the API on port 8000, then use these endpoints:

```text
GET  /health
GET  /ready

GET  /api/queue
GET  /api/accounts/{account_id}
GET  /api/accounts/{account_id}/graph
GET  /api/accounts/{account_id}/timeline
GET  /api/accounts/{account_id}/feature-ablation
POST /api/accounts/{account_id}/investigate

GET  /api/graph/overview
GET  /api/rings
GET  /api/rings/{candidate_id}

GET  /api/metrics
GET  /api/metrics/curves
GET  /api/metrics/feature-ablation
GET  /api/audit
DELETE /api/audit

POST /api/address/normalize
POST /api/failure-demo/razorpay
POST /api/failure-demo/razorpay-synthetic
```

`/api/rings` accepts `limit` and `detected_only` query parameters. It returns saved or model-scored ring candidates, their member count, exposure, strongest internal relationship, priority tier and recommended bounded action.

## Setup

### Prerequisites

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm

### Backend

From the repository root:

```powershell
uv sync
uv run uvicorn backend.main:app --reload
```

Confirm startup:

```powershell
curl http://127.0.0.1:8000/health
```

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The default frontend URL is `http://localhost:5173`. It calls `http://localhost:8000` unless `VITE_API_BASE_URL` is set.

To create a production build:

```powershell
cd frontend
npm run build
npm run preview
```

## Regenerating the offline artifacts

The generation pipeline writes into the configured V4 dataset directory. Run steps in this order when rebuilding the dataset and models:

```powershell
uv run python -m generator.generate_dataset
uv run python -m generator.features
uv run python -m generator.graph_features
uv run python -m generator.lightgbm
uv run python -m generator.lightgbm_tuned
uv run python -m generator.gnn_model
uv run python -m generator.ensemble
uv run python -m generator.ring_model
uv run python -m generator.feature_ablation
```

The scripts write their artifacts below `data/v4_realistic_30k/processed/`. Re-run the API after generating artifacts so its cached readers use the updated files.

## Testing

Run the API tests from the repository root:

```powershell
uv run pytest -q backend/tests/test_api.py
```

The address-normalization test file is a manual diagnostic script rather than a pytest test module.

## Razorpay and failure-demo boundary

The project includes a Razorpay Test Mode fetch path and a deterministic malformed-batch demo. The synthetic path validates records, quarantines malformed rows and reports the outcome. The Test Mode path displays fetched records without injecting faults.

Neither path is live model ingestion. It does not currently persist incoming events, rebuild graph relationships, recompute cutoff-aware features or change account/ring scores. A production integration would need signed webhook verification, idempotent event storage, canonical event mapping, background feature/graph updates and versioned rescoring.

## Evaluation and limitations

- All data, ring membership and reported metrics are synthetic. They must not be presented as production performance.
- Account and ring evaluation keep synthetic rings grouped across splits, but this is not a future-time production validation.
- The GraphSAGE model is evaluated on the persisted graph, so its setting should be described as graph-based offline evaluation rather than proof of generalization to new production rings.
- SHAP provides model attribution, not a causal explanation.
- Feature ablation uses held-out median replacement for sensitivity analysis and is not causal evidence.
- The FastAPI service is artifact-backed. It is not an online feature store, streaming scorer or live webhook processor.
- The optional LLM investigator drafts a structured evidence summary; the deterministic policy chooses the recommendation.
- Audit entries preserve demonstration context, but reviewer approval/rejection is not yet implemented as a durable workflow.

## Architecture

The implementation diagram, component boundaries and current Razorpay limitation are documented in [docs/architecture.md](docs/architecture.md).

## Safe demo framing

Describe RingWatch as an offline synthetic-data investigation prototype that combines account-risk signals, relationship evidence and a ring-candidate layer. Describe scores as prioritization signals for human review, not automated fraud decisions.
