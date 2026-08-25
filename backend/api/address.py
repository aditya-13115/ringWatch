from fastapi import APIRouter, Depends

from backend.schemas.address import AddressNormalizeRequest, AddressNormalizeResponse
from backend.services.address_normalizer_service import AddressNormalizerService
from backend.dependencies import get_address_normalizer_service

router = APIRouter(prefix="/address", tags=["address"])


@router.post("/normalize", response_model=AddressNormalizeResponse)
async def normalize_address(
    request: AddressNormalizeRequest,
    address_service: AddressNormalizerService = Depends(get_address_normalizer_service),
):
    result = await address_service.normalize(request.raw_address)
    return AddressNormalizeResponse(**result)