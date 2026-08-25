from pydantic import BaseModel


class QueueAccount(BaseModel):
    rank: int
    account_id: str
    proba: float
    risk_tier: str
    recommended_action: str
    graph_links: int = 0
    evidence_gaps: int | None = None


class QueueResponse(BaseModel):
    accounts: list[QueueAccount]
    total: int
