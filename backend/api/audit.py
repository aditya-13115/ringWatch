from fastapi import APIRouter, Depends, HTTPException

from backend.schemas.audit import AuditResponse, AuditRecordResponse
from backend.services.audit_service import AuditService

print("AUDIT SCHEMA:", AuditRecordResponse.model_fields["proba"])
from backend.dependencies import get_audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditResponse)
async def get_audit(
    audit_service: AuditService = Depends(get_audit_service),
):
    records = await audit_service.get_audit_log()

    cleaned_records = []

    for r in records:
        record = dict(r)

        # Some audit events, such as LLM investigations or
        # action events, do not have a model probability.
        # Keep those records valid with proba=None.
        if record.get("proba") is not None:
            try:
                record["proba"] = float(record["proba"])
            except (TypeError, ValueError):
                record["proba"] = None

        cleaned_records.append(AuditRecordResponse(**record))

    return AuditResponse(records=cleaned_records)


@router.delete("")
async def delete_audit(
    audit_service: AuditService = Depends(get_audit_service),
):
    """Clear the investigation audit log."""
    try:
        await audit_service.clear_audit_log()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
