import pandas as pd

from backend.domain.evidence import EvidenceStatus
from backend.repositories.explainability_repository import ExplainabilityRepository


EVIDENCE_FIELDS = [
    "proof_of_service",
    "explanation_letter",
    "refund_confirmation",
    "access_activity_log",
    "refund_cancellation_policy",
    "terms_and_conditions",
]


class EvidenceService:
    def __init__(self, explainability_repo: ExplainabilityRepository):
        self.explainability_repo = explainability_repo

    async def get_evidence_status(self, account_id: str) -> EvidenceStatus:
        evidence_df = self.explainability_repo.get_evidence()
        row = evidence_df[evidence_df["account_id"] == account_id]

        if row.empty:
            return EvidenceStatus(
                account_id=account_id,
                has_dispute_at_cutoff=False,
                fields={field: "NO_DISPUTE_YET" for field in EVIDENCE_FIELDS},
                missing_evidence_count=None,
            )

        row = row.iloc[0]
        has_dispute = bool(row["has_dispute_at_cutoff"])
        fields = {}
        for field in EVIDENCE_FIELDS:
            if field in row:
                val = row[field]
                fields[field] = str(val) if pd.notna(val) else "MISSING"
            else:
                fields[field] = "NO_DISPUTE_YET"

        missing_count = None
        if has_dispute:
            missing_count = int(row["missing_evidence_count"]) if pd.notna(row["missing_evidence_count"]) else 0

        return EvidenceStatus(
            account_id=account_id,
            has_dispute_at_cutoff=has_dispute,
            fields=fields,
            missing_evidence_count=missing_count,
        )