from pydantic import BaseModel


class EvidenceStatusResponse(BaseModel):
    account_id: str
    has_dispute_at_cutoff: bool
    fields: dict[str, str]
    missing_evidence_count: int | None
