from pydantic import BaseModel


class InvestigationRequest(BaseModel):
    account_id: str


class InvestigationResponse(BaseModel):
    account_id: str
    source: str  # "llm" or "deterministic"
    summary: str
    key_findings: list[str]
    evidence_gaps: list[str]
    uncertainties: list[str]
    tool_calls: list[dict]
    recommended_action: str
    action_source: str
