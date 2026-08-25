from fastapi import APIRouter, Depends

from backend.schemas.evidence import EvidenceStatusResponse
from backend.services.evidence_service import EvidenceService
from backend.dependencies import get_evidence_service

router = APIRouter(prefix="/accounts", tags=["evidence"])


@router.get("/{account_id}/evidence", response_model=EvidenceStatusResponse)
async def get_evidence(
    account_id: str,
    evidence_service: EvidenceService = Depends(get_evidence_service),
):
    evidence = await evidence_service.get_evidence_status(account_id)
    return EvidenceStatusResponse(
        account_id=evidence.account_id,
        has_dispute_at_cutoff=evidence.has_dispute_at_cutoff,
        fields=evidence.fields,
        missing_evidence_count=evidence.missing_evidence_count,
    )
