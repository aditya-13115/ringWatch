from pathlib import Path

import pandas as pd

from backend.core.config import get_settings
from backend.core.concurrency import ADDRESS_LLM_SEMAPHORE


class AddressNormalizerService:
    """Deterministic placeholder for LLM address normalization.

    Later this will call an LLM to parse messy addresses and then
    resolve them against canonical addresses.
    """

    def __init__(self, addresses_path: Path):
        self.addresses = pd.read_csv(addresses_path)

    async def normalize(self, raw_address: str) -> dict:
        async with ADDRESS_LLM_SEMAPHORE:
            normalized = self._normalize_text(raw_address)

            match = self.addresses[
                self.addresses["canonical_address"] == normalized
            ]

            if not match.empty:
                return {
                    "raw_address": raw_address,
                    "normalized_address": normalized,
                    "candidate_address_id": match.iloc[0]["address_id"],
                    "confidence": 1.0,
                    "requires_human_review": False,
                }

            return {
                "raw_address": raw_address,
                "normalized_address": normalized,
                "candidate_address_id": None,
                "confidence": 0.0,
                "requires_human_review": True,
            }

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.lower().split())