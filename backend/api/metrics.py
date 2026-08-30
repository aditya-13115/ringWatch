from fastapi import APIRouter, Depends

from backend.services.metrics_service import MetricsService
from backend.dependencies import get_metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    return await metrics_service.get_metrics()


@router.get("/curves")
async def get_curves(
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    return await metrics_service.get_curves()
