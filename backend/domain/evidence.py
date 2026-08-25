from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EvidenceStatus:
    account_id: str
    has_dispute_at_cutoff: bool
    fields: dict[str, str]
    missing_evidence_count: Optional[int] = None
