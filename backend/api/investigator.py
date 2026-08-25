from fastapi import APIRouter, Depends, HTTPException

from backend.schemas.llm import InvestigationResponse, InvestigationRequest
from backend.services.llm_investigator_service import LLMInvestigatorService
from backend.dependencies import get_llm_investigator_service

router = APIRouter(prefix="/accounts", tags=["investigator"])


@router.post("/{account_id}/investigate", response_model=InvestigationResponse)
async def investigate_account(
    account_id: str,
    investigator_service: LLMInvestigatorService = Depends(
        get_llm_investigator_service
    ),
):
    try:
        result = await investigator_service.investigate(account_id)
        return InvestigationResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
