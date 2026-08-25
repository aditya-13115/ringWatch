from fastapi import APIRouter, HTTPException

from backend.dependencies import get_data_store

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Basic liveness probe."""
    return {
        "status": "ok",
        "service": "RingWatch API",
        "version": "1.0.0",
    }


@router.get("/ready")
async def ready():
    """
    Readiness probe.

    Checks if required data store is initialized and accessible.
    """
    try:
        data_store = get_data_store()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="RingWatch data store is not initialized.",
        ) from exc

    return {
        "status": "ready",
        "data_store_initialized": True,
        "explainability_dir": str(data_store.explainability_dir),
        "features_graph_path": str(data_store.features_graph_path),
    }
