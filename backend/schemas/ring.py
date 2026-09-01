from typing import Any
from pydantic import BaseModel, Field


class RingMember(BaseModel):
    account_id: str
    account_risk: float
    rank_in_ring: int


class RingSummary(BaseModel):
    candidate_id: str
    ring_score: float
    detected: bool
    risk_tier: str
    recommended_action: str
    member_count: int
    exposure: float
    mean_account_risk: float
    max_account_risk: float
    internal_edge_count: int
    strongest_edge_type: str | None = None
    strongest_edge_weight: float | None = None
    member_ids: list[str] = Field(default_factory=list)


class RingDetail(RingSummary):
    members: list[RingMember] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class RingListResponse(BaseModel):
    rings: list[RingSummary]
    total: int
    detected_count: int
    model: dict[str, Any] = Field(default_factory=dict)
