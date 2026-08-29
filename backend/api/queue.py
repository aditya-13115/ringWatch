from fastapi import APIRouter, Depends
from backend.schemas.queue import QueueAccount, QueueResponse
from backend.services.queue_service import QueueService
from backend.dependencies import get_queue_service

router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=QueueResponse)
async def get_queue(
    limit: int = 10,
    queue_service: QueueService = Depends(get_queue_service),
):
    accounts = await queue_service.get_queue(limit=limit)

    all_accounts = await queue_service.get_queue(limit=100000)

    queue_accounts = [
        QueueAccount(
            account_id=account.account_id,
            rank=account.rank,
            proba=account.proba,
            risk_tier=account.risk_tier,
            recommended_action=account.recommended_action,
        )
        for account in accounts
    ]

    return QueueResponse(
        accounts=queue_accounts,
        total=len(all_accounts),
    )