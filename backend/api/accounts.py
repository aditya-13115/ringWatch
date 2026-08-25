from fastapi import APIRouter, Depends, HTTPException

from backend.schemas.account import AccountDetailResponse
from backend.services.account_service import AccountService
from backend.dependencies import get_account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/{account_id}", response_model=AccountDetailResponse)
async def get_account(
    account_id: str,
    account_service: AccountService = Depends(get_account_service),
):
    try:
        detail = await account_service.get_account_detail(account_id)
        return AccountDetailResponse(
            account_id=detail.account_id,
            rank=detail.rank,
            proba=detail.proba,
            risk_tier=detail.risk_tier,
            recommended_action=detail.recommended_action,
            observed_facts=detail.observed_facts,
            top_shap_features=detail.top_shap_features,
            graph_evidence=detail.graph_evidence,
            evidence_status=detail.evidence_status,
            case_report_text=detail.case_report_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))