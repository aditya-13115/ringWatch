from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AddressComponents(BaseModel):
    """
    Structured representation of an address.

    The current RingWatch address store is CSV-backed, so these fields
    are derived in memory from canonical_address records.
    """

    model_config = ConfigDict(extra="ignore")

    house_no: Optional[str] = None
    building: Optional[str] = None
    street: Optional[str] = None
    area: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None

    @field_validator("pincode", mode="before")
    @classmethod
    def normalize_pincode(cls, value):
        if value is None or value == "":
            return value

        text = str(value).strip()

        # Handle pandas-style numeric values such as 560034.0
        if text.endswith(".0") and text[:-2].isdigit():
            text = text[:-2]

        return text


class AddressExtractRequest(BaseModel):
    raw_address: str = Field(
        min_length=3,
        max_length=2000,
    )


class AddressVerifyRequest(BaseModel):
    raw_address: Optional[str] = Field(
        default=None,
        max_length=2000,
    )
    components: AddressComponents


class AddressNormalizeRequest(BaseModel):
    """
    Backward-compatible combined endpoint.

    Existing clients can continue sending:
        {
            "raw_address": "...",
            "components": {...}
        }
    """

    raw_address: str = Field(
        min_length=3,
        max_length=2000,
    )
    components: Optional[AddressComponents] = None


class AddressMatch(BaseModel):
    address_id: str
    canonical_address: str
    score: float = Field(
        ge=0.0,
        le=1.0,
    )
    matched_fields: dict[str, float] = Field(
        default_factory=dict
    )
    exact_fields: list[str] = Field(
        default_factory=list
    )


class AddressExtractResponse(BaseModel):
    raw_address: str
    components: AddressComponents
    extraction_source: str


class AddressVerifyResponse(BaseModel):
    raw_address: Optional[str]
    normalized_address: Optional[str]
    candidate_address_id: Optional[str]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    requires_human_review: bool

    components: AddressComponents

    matches: list[AddressMatch] = Field(
        default_factory=list
    )

    candidate_count: int = 0

    matching_strategy: str = "structured"

    review_reasons: list[str] = Field(
        default_factory=list
    )


class AddressNormalizeResponse(AddressVerifyResponse):
    pass