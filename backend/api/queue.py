from fastapi import APIRouter, Depends, Query
from backend.schemas.queue import QueueResponse, QueueAccount
from backend.services.queue_service import QueueService
from backend.dependencies import get_queue_service

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=QueueResponse)
async def get_queue(
    limit: int = Query(7, ge=1, le=500),
    queue_service: QueueService = Depends(get_queue_service),
):
    queue = await queue_service.get_queue(limit=limit)
    accounts = [
        QueueAccount(
            rank=a.rank,
            account_id=a.account_id,
            proba=a.proba,
            risk_tier=a.risk_tier,
            recommended_action=a.recommended_action,
        )
        for a in queue
    ]
    return QueueResponse(accounts=accounts, total=len(accounts))
