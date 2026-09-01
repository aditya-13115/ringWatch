from fastapi import APIRouter, Depends, HTTPException, Query

from backend.schemas.ring import RingDetail, RingListResponse
from backend.services.ring_service import RingService

router = APIRouter(prefix="/rings", tags=["rings"])


def get_ring_service() -> RingService:
    return RingService()


@router.get("", response_model=RingListResponse)
async def get_rings(
    limit: int = Query(25, ge=1, le=250),
    detected_only: bool = False,
    service: RingService = Depends(get_ring_service),
):
    return service.list_rings(limit=limit, detected_only=detected_only)


@router.get("/{candidate_id}", response_model=RingDetail)
async def get_ring(
    candidate_id: str,
    service: RingService = Depends(get_ring_service),
):
    ring = service.get_ring(candidate_id)
    if ring is None:
        raise HTTPException(status_code=404, detail="Ring candidate not found")
    return ring
