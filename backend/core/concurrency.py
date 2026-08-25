import asyncio

from backend.core.config import get_settings


settings = get_settings()

GENERAL_SEMAPHORE = asyncio.Semaphore(
    settings.general_concurrency
)

LLM_SEMAPHORE = asyncio.Semaphore(
    settings.llm_concurrency
)

ADDRESS_LLM_SEMAPHORE = asyncio.Semaphore(
    settings.address_llm_concurrency
)