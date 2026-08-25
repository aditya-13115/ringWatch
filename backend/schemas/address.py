from pydantic import BaseModel


class AddressNormalizeRequest(BaseModel):
    raw_address: str


class AddressNormalizeResponse(BaseModel):
    raw_address: str
    normalized_address: str | None
    candidate_address_id: str | None
    confidence: float
    requires_human_review: bool
