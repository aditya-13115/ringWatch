from pydantic import BaseModel, Field
from typing import List, Optional


class InvestigationRequest(BaseModel):
    account_id: str


class InvestigationResponse(BaseModel):
    account_id: str
    source: str = Field(default="llm", description="llm or deterministic")
    summary: str
    key_findings: List[str] = []
    evidence_gaps: List[str] = []
    uncertainties: List[str] = []
    confidence: str = "LOW"
    tool_calls: List[dict] = []
    recommended_action: str
    action_source: str = "deterministic_policy"
    error: Optional[str] = None
