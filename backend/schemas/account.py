from typing import Any

from pydantic import BaseModel


class ShapFeature(BaseModel):
    feature: str
    shap_value: float


class AccountDetailResponse(BaseModel):
    account_id: str

    # Investigation queue position
    rank: int
    rank_total: int

    # Model information
    model_version: str
    proba: float

    risk_tier: str
    recommended_action: str

    observed_facts: dict[str, Any]
    top_shap_features: list[ShapFeature]

    graph_evidence: dict[str, Any]
    evidence_status: dict[str, Any]

    case_report_text: str
