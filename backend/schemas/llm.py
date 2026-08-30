from typing import List, Optional

from pydantic import BaseModel, Field


class InvestigationRequest(BaseModel):
    account_id: str


class FinancialExposure(BaseModel):
    gross_order_value: float = 0.0
    refund_amount: float = 0.0
    potential_exposure: float = 0.0


class InvestigationResponse(BaseModel):
    account_id: str

    source: str = Field(
        default="llm",
        description="llm or deterministic",
    )

    summary: str

    key_findings: List[str] = []
    evidence_gaps: List[str] = []
    uncertainties: List[str] = []

    confidence: str = "LOW"

    tool_calls: List[dict] = []

    financial_exposure: FinancialExposure = FinancialExposure()

    recommended_action: str

    action_source: str = "deterministic_policy"

    error: Optional[str] = None
