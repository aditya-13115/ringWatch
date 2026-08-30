from pydantic import BaseModel


class AuditRecordResponse(BaseModel):
    timestamp: str
    account_id: str
    model_version: str
    proba: float | None = None
    rank: int
    risk_tier: str
    top_k_flag: bool
    action_recommended: str
    case_report_generated: bool

    # Optional investigation fields
    investigation_source: str | None = None
    tool_calls: str | None = None
    summary: str | None = None
    action_source: str | None = None
    error: str | None = None

    # Auditability fields. These are derived from the recorded decision context
    # and are intentionally references/snapshots, not causal claims.
    input_data_hash: str | None = None
    threshold_used: float | None = None
    feature_snapshot: str | None = None
    evidence_subgraph: str | None = None
    human_decision: str | None = None
    outcome: str | None = None
    error_path: str | None = None


class AuditResponse(BaseModel):
    records: list[AuditRecordResponse]
