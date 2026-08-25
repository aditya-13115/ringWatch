from typing import Any

from pydantic import BaseModel


class AccountDetailResponse(BaseModel):
    account_id: str
    rank: int
    proba: float
    risk_tier: str
    recommended_action: str
    observed_facts: dict[str, Any]
    top_shap_features: list[dict[str, float]]
    graph_evidence: dict[str, Any]
    evidence_status: dict[str, Any]
    case_report_text: str