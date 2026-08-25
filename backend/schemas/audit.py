from pydantic import BaseModel


class AuditRecordResponse(BaseModel):
    timestamp: str
    account_id: str
    model_version: str
    proba: float
    rank: int
    risk_tier: str
    top_k_flag: bool
    action_recommended: str
    case_report_generated: bool


class AuditResponse(BaseModel):
    records: list[AuditRecordResponse]