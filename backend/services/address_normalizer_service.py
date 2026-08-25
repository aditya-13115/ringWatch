import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
from groq import AsyncGroq

from backend.core.config import get_settings
from backend.core.concurrency import ADDRESS_LLM_SEMAPHORE


class AddressNormalizerService:
    def __init__(self, addresses_path: Path):
        self.addresses = pd.read_csv(addresses_path)
        self.settings = get_settings()
        self.client = AsyncGroq(api_key=self.settings.groq_api_key)

    async def normalize(self, raw_address: str) -> dict:
        async with ADDRESS_LLM_SEMAPHORE:
            # First try deterministic normalization
            det_result = self._deterministic_normalize(raw_address)
            if det_result["confidence"] >= 0.95:
                return det_result

            # Else use LLM to parse and match
            try:
                llm_result = await self._llm_normalize(raw_address)
                if llm_result["confidence"] >= 0.7:
                    return llm_result
                else:
                    # Low confidence: require human review
                    return {
                        "raw_address": raw_address,
                        "normalized_address": llm_result.get("normalized_address"),
                        "candidate_address_id": None,
                        "confidence": llm_result["confidence"],
                        "requires_human_review": True,
                    }
            except Exception:
                # LLM failed, fall back to deterministic result
                det_result["requires_human_review"] = True
                return det_result

    def _deterministic_normalize(self, raw_address: str) -> dict:
        normalized = self._basic_normalize(raw_address)
        # Try exact match
        match = self.addresses[
            self.addresses["canonical_address"].str.lower() == normalized
        ]
        if not match.empty:
            return {
                "raw_address": raw_address,
                "normalized_address": normalized,
                "candidate_address_id": match.iloc[0]["address_id"],
                "confidence": 1.0,
                "requires_human_review": False,
            }
        else:
            return {
                "raw_address": raw_address,
                "normalized_address": normalized,
                "candidate_address_id": None,
                "confidence": 0.0,
                "requires_human_review": True,
            }

    def _basic_normalize(self, text: str) -> str:
        return " ".join(text.lower().split())

    async def _llm_normalize(self, raw_address: str) -> dict:
        if not self.settings.groq_api_key:
            return {"confidence": 0.0, "normalized_address": None}

        prompt = (
            "Normalize the following Indian address into canonical form.\n"
            f"Address: {raw_address}\n"
            "Return JSON with keys: 'flat', 'building', 'street', 'area', 'city', 'state', 'pincode'.\n"
            "If a component is missing, use null."
        )

        response = await self.client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
        )
        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
            normalized = self._format_components(parsed)
            # Find closest match (exact or contains)
            match = self.addresses[
                self.addresses["canonical_address"].str.lower().str.contains(
                    normalized.split(",")[0], na=False
                )
            ]
            if not match.empty:
                # compute simple confidence based on match length
                confidence = 0.85
                return {
                    "raw_address": raw_address,
                    "normalized_address": normalized,
                    "candidate_address_id": match.iloc[0]["address_id"],
                    "confidence": confidence,
                    "requires_human_review": False,
                }
            else:
                return {
                    "raw_address": raw_address,
                    "normalized_address": normalized,
                    "candidate_address_id": None,
                    "confidence": 0.5,
                    "requires_human_review": True,
                }
        except Exception:
            return {"confidence": 0.0, "normalized_address": None}

    def _format_components(self, comps: dict) -> str:
        parts = []
        if comps.get("flat"):
            parts.append(f"Flat {comps['flat']}")
        if comps.get("building"):
            parts.append(comps["building"])
        if comps.get("street"):
            parts.append(comps["street"])
        if comps.get("area"):
            parts.append(comps["area"])
        if comps.get("city"):
            parts.append(comps["city"])
        if comps.get("state"):
            parts.append(comps["state"])
        if comps.get("pincode"):
            parts.append(str(comps["pincode"]))
        return ", ".join(filter(None, parts))