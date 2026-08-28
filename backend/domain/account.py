from typing import Any
from dataclasses import dataclass


@dataclass
class AccountRisk:
    account_id: str
    rank: int
    proba: float
    risk_tier: str
    recommended_action: str


@dataclass
class AccountDetail:
    account_id: str
    rank: int
    model_score: float
    risk_tier: str
    recommended_action: str
    observed_facts: dict[str, Any]
    top_shap_features: list[dict[str, float]]
    graph_evidence: dict[str, Any]
    evidence_status: dict[str, Any]
    case_report_text: str