# RingWatch Architecture

```mermaid
flowchart TD
    A[Razorpay Test Mode / Synthetic Events] --> B[Canonical Data + Cutoff]
    B --> C[Behavioral + Identity Features]
    B --> D[Account Relationship Graph]
    D --> E[Persisted Community Assignments]
    C --> F[V4 Ensemble]
    D --> F
    F --> G[Ranked Investigation Queue]
    G --> H[Account Investigation]
    H --> I[SHAP Attribution]
    H --> J[Ring / Community Context]
    H --> K[Evidence Gap Checks]
    H --> L[Timeline + Financial Exposure]
    I --> M[AI Investigator]
    J --> M
    K --> M
    L --> M
    M --> N[Deterministic Policy]
    N --> O[Bounded Recommendation]
    O --> P[Human Review / Approval]
    P --> Q[Audit Trail]

    R[Malformed Synthetic Batch] --> S[Validation]
    S --> T[Quarantine Invalid Rows]
    S --> U[Continue Valid Rows]
    T --> P
    T --> Q
    U --> Q
```

## Model boundary

- **Risk model:** V4 Ensemble (tuned LightGBM B + GNN).
- **Explainability:** SHAP for model attribution.
- **Investigator:** optional LLM-assisted evidence synthesis with deterministic fallback.
- **Policy:** deterministic and bounded.
- **Human:** required for consequential review actions.

## Community boundary

The Rings UI consumes persisted `community_id` assignments when available. This avoids silently replacing the offline community definition with a different client-side graph partition. Older graph artifacts without assignments use a connected-component fallback.
