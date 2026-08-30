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


class AuditResponse(BaseModel):
    records: list[AuditRecordResponse]
