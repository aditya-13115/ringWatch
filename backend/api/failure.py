from fastapi import APIRouter, Depends

from backend.services.failure_service import FailureDemoService
from backend.dependencies import get_failure_service

router = APIRouter(prefix="/failure-demo", tags=["failure"])


@router.post("")
async def simulate_failure(
    failure_service: FailureDemoService = Depends(get_failure_service),
):
    return await failure_service.simulate_malformed_batch()