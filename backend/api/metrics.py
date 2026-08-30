from fastapi import APIRouter, Depends

from backend.services.metrics_service import MetricsService
from backend.dependencies import get_metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    return await metrics_service.get_metrics()


@router.get("/feature-ablation")
async def get_feature_ablation(
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    return await metrics_service.get_feature_ablation()


@router.get("/curves")
async def get_curves(
    metrics_service: MetricsService = Depends(get_metrics_service),
):
    return await metrics_service.get_curves()
