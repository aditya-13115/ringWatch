from fastapi import APIRouter, Depends, HTTPException

from backend.schemas.action import BoundedActionResponse
from backend.services.action_service import ActionService
from backend.dependencies import get_action_service

router = APIRouter(prefix="/accounts", tags=["actions"])


@router.get("/{account_id}/action", response_model=BoundedActionResponse)
async def get_action(
    account_id: str,
    action_service: ActionService = Depends(get_action_service),
):
    try:
        action = await action_service.get_action(account_id)
        return BoundedActionResponse(
            account_id=action.account_id,
            risk_tier=action.risk_tier,
            action_code=action.action_code,
            action_description=action.action_description,
            requires_human_review=action.requires_human_review,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
