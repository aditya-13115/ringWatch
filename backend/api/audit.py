from fastapi import APIRouter, Depends

from backend.schemas.audit import AuditResponse, AuditRecordResponse
from backend.services.audit_service import AuditService
from backend.dependencies import get_audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditResponse)
async def get_audit(
    audit_service: AuditService = Depends(get_audit_service),
):
    records = await audit_service.get_audit_log()
    return AuditResponse(records=[AuditRecordResponse(**r) for r in records])