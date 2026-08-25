from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder

from backend.schemas.account import AccountDetailResponse
from backend.services.account_service import AccountService
from backend.dependencies import get_account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/{account_id}", response_model=AccountDetailResponse)
async def get_account(
    account_id: str,
    account_service: AccountService = Depends(get_account_service),
):
    detail = await account_service.get_account_detail(account_id)
    return jsonable_encoder(detail)