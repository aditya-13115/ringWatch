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
            # Try deterministic first
            det_result = self._deterministic_normalize(raw_address)
            if det_result["confidence"] >= 0.95:
                return det_result

            # Use LLM to parse components
            try:
                llm_comps = await self._llm_parse_components(raw_address)
            except Exception:
                llm_comps = None

            if llm_comps:
                best_match, score = self._best_component_match(llm_comps)
                if score >= 0.90:
                    return {
                        "raw_address": raw_address,
                        "normalized_address": self._format_components(llm_comps),
                        "candidate_address_id": best_match,
                        "confidence": score,
                        "requires_human_review": False,
                    }
                elif score >= 0.70:
                    return {
                        "raw_address": raw_address,
                        "normalized_address": self._format_components(llm_comps),
                        "candidate_address_id": best_match,
                        "confidence": score,
                        "requires_human_review": True,
                    }

            # Unresolved
            return {
                "raw_address": raw_address,
                "normalized_address": None,
                "candidate_address_id": None,
                "confidence": 0.0,
                "requires_human_review": True,
            }

    def _deterministic_normalize(self, raw_address: str) -> dict:
        normalized = self._basic_normalize(raw_address)
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
        return {
            "raw_address": raw_address,
            "normalized_address": normalized,
            "candidate_address_id": None,
            "confidence": 0.0,
            "requires_human_review": True,
        }

    def _basic_normalize(self, text: str) -> str:
        return " ".join(text.lower().split())

    async def _llm_parse_components(self, raw_address: str) -> dict | None:
        if not self.settings.groq_api_key:
            return None
        prompt = (
            "Extract the following fields from this Indian address:\n"
            f"Address: {raw_address}\n"
            "Return JSON: {\"flat\": \"...\", \"building\": \"...\", \"street\": \"...\", \"area\": \"...\", \"city\": \"...\", \"state\": \"...\", \"pincode\": \"...\"}\n"
            "If a field is missing, use null."
        )
        response = await self.client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=200,
        )
        content = response.choices[0].message.content
        return json.loads(content)

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

    def _best_component_match(self, comps: dict) -> tuple[str | None, float]:
        """Score each address based on component overlap."""
        best_id = None
        best_score = 0.0
        for _, addr in self.addresses.iterrows():
            addr_text = addr["canonical_address"].lower()
            score = 0.0
            # Pincode dominates
            if str(comps.get("pincode")) == str(addr.get("pincode", "")):
                score += 0.4
            # City
            if comps.get("city") and comps["city"].lower() in addr_text:
                score += 0.15
            # Area
            if comps.get("area") and comps["area"].lower() in addr_text:
                score += 0.15
            # Building
            if comps.get("building") and comps["building"].lower() in addr_text:
                score += 0.15
            # Street
            if comps.get("street") and comps["street"].lower() in addr_text:
                score += 0.10
            # Flat
            if comps.get("flat") and f"flat {comps['flat'].lower()}" in addr_text:
                score += 0.05

            if score > best_score:
                best_score = score
                best_id = addr["address_id"]
        return best_id, best_score