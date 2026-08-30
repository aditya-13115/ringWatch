from fastapi import APIRouter, Depends, HTTPException

from backend.services.failure_service import FailureDemoService
from backend.dependencies import get_failure_service

router = APIRouter(
    prefix="/failure-demo",
    tags=["failure"],
)


@router.post("/razorpay")
async def ingest_razorpay_batch(
    failure_service: FailureDemoService = Depends(get_failure_service),
):
    """
    Fetch a Test Mode Razorpay batch and run RingWatch
    validation/quarantine handling.
    """
    try:
        return await failure_service.ingest_razorpay_batch()

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failure demo processing failed: {exc}",
        ) from exc


@router.post("/razorpay-synthetic")
async def generate_razorpay_synthetic_batch(
    failure_service: FailureDemoService = Depends(get_failure_service),
):
    """
    Generate a deterministic Razorpay-shaped test batch
    and run the same RingWatch validation/quarantine pipeline.
    """
    try:
        return await failure_service.ingest_synthetic_razorpay_batch()

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Synthetic failure demo failed: {exc}",
        ) from exc
