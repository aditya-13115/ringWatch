from fastapi import APIRouter, Depends

from backend.dependencies import get_address_normalizer_service
from backend.schemas.address import (
    AddressExtractRequest,
    AddressExtractResponse,
    AddressNormalizeRequest,
    AddressNormalizeResponse,
    AddressVerifyRequest,
    AddressVerifyResponse,
)
from backend.services.address_normalizer_service import (
    AddressNormalizerService,
)

router = APIRouter(
    prefix="/address",
    tags=["address"],
)


@router.post(
    "/extract",
    response_model=AddressExtractResponse,
)
async def extract_address(
    request: AddressExtractRequest,
    address_service: AddressNormalizerService = Depends(get_address_normalizer_service),
):
    components, source = await address_service.extract_components(request.raw_address)

    return AddressExtractResponse(
        raw_address=request.raw_address,
        components=components,
        extraction_source=source,
    )


@router.post(
    "/verify",
    response_model=AddressVerifyResponse,
)
async def verify_address(
    request: AddressVerifyRequest,
    address_service: AddressNormalizerService = Depends(get_address_normalizer_service),
):
    result = address_service.verify_components(
        raw_address=request.raw_address,
        components=request.components.model_dump(exclude_none=True),
    )

    return AddressVerifyResponse(**result)


@router.post(
    "/normalize",
    response_model=AddressNormalizeResponse,
)
async def normalize_address(
    request: AddressNormalizeRequest,
    address_service: AddressNormalizerService = Depends(get_address_normalizer_service),
):
    result = await address_service.normalize(
        raw_address=request.raw_address,
        components=(
            request.components.model_dump(exclude_none=True)
            if request.components is not None
            else None
        ),
    )

    return AddressNormalizeResponse(**result)
