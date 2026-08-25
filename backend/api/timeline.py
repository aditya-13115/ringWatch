from fastapi import APIRouter, Depends
from backend.dependencies import get_timeline_service
from backend.services.timeline_service import TimelineService

router = APIRouter(prefix="/accounts", tags=["timeline"])


@router.get("/{account_id}/timeline")
async def get_timeline(
    account_id: str,
    timeline_service: TimelineService = Depends(get_timeline_service),
):
    events = await timeline_service.get_timeline(account_id)
    return {"account_id": account_id, "events": events}
