from fastapi import APIRouter, Depends

from backend.schemas.report import CaseReportResponse
from backend.services.report_service import ReportService
from backend.dependencies import get_report_service

router = APIRouter(prefix="/accounts", tags=["reports"])


@router.get("/{account_id}/report", response_model=CaseReportResponse)
async def get_report(
    account_id: str,
    report_service: ReportService = Depends(get_report_service),
):
    report_text = await report_service.get_case_report(account_id)
    return CaseReportResponse(account_id=account_id, case_report_text=report_text)
