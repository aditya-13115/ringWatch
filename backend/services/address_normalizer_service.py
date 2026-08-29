import json
import re
from difflib import SequenceMatcher
from pathlib import Path

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
            basic_normalized = self._basic_normalize(raw_address)
            expanded_normalized = self._expand_abbreviations(basic_normalized)

            # 1) Exact match
            exact_id = self._exact_match(basic_normalized)
            if exact_id is not None:
                return self._success(raw_address, basic_normalized, exact_id, 1.0)

            # 2) Exact match after abbreviation expansion
            exact_id_expanded = self._exact_match(expanded_normalized)
            if exact_id_expanded is not None:
                return self._success(
                    raw_address, expanded_normalized, exact_id_expanded, 0.98
                )

            # 3) LLM component parsing
            llm_comps = await self._safe_llm_parse(raw_address)
            if llm_comps is not None:
                formatted = self._format_components(llm_comps)
                best_id, score = self._best_component_match(llm_comps)

                if score >= 0.90:
                    return self._success(raw_address, formatted, best_id, score)
                if score >= 0.70:
                    return self._review(raw_address, formatted, best_id, score)
                return self._review(
                    raw_address, formatted or basic_normalized, best_id, score
                )

            # 4) Fuzzy fallback without LLM
            best_id, score = self._fuzzy_match(expanded_normalized)
            if score >= 0.85:
                return self._success(raw_address, expanded_normalized, best_id, score)
            if score >= 0.70:
                return self._review(raw_address, expanded_normalized, best_id, score)

            # 5) Unresolved
            return self._review(raw_address, basic_normalized, None, 0.0)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _success(self, raw, normalized, address_id, confidence):
        return {
            "raw_address": raw,
            "normalized_address": normalized,
            "candidate_address_id": address_id,
            "confidence": round(confidence, 2),
            "requires_human_review": False,
        }

    def _review(self, raw, normalized, address_id, confidence):
        return {
            "raw_address": raw,
            "normalized_address": normalized,
            "candidate_address_id": address_id,
            "confidence": round(confidence, 2),
            "requires_human_review": True,
        }

    def _basic_normalize(self, text: str) -> str:
        return " ".join(text.lower().split())

    def _expand_abbreviations(self, text: str) -> str:
        """Expand common Indian address abbreviations."""
        replacements = {
            r"\bst\b": "street",
            r"\brd\b": "road",
            r"\bapt\b": "apartment",
            r"\bappt\b": "apartment",
            r"\bflt\b": "flat",
            r"\bfl\b": "flat",
            r"\bbldg\b": "building",
            r"\bnr\b": "near",
            r"\bblr\b": "bengaluru",
            r"\bbangalore\b": "bengaluru",
        }
        expanded = text
        for pattern, replacement in replacements.items():
            expanded = re.sub(pattern, replacement, expanded)
        return self._basic_normalize(expanded)

    def _exact_match(self, normalized_text: str) -> str | None:
        match = self.addresses[
            self.addresses["canonical_address"].str.lower() == normalized_text
        ]
        if not match.empty:
            return match.iloc[0]["address_id"]
        return None

    def _similarity(self, a: str, b: str) -> float:
        a = self._basic_normalize(a or "")
        b = self._basic_normalize(b or "")
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    def _fuzzy_match(self, normalized_text: str) -> tuple[str | None, float]:
        """Find best fuzzy match among all addresses."""
        best_id = None
        best_score = 0.0
        for _, addr in self.addresses.iterrows():
            addr_text = self._basic_normalize(str(addr["canonical_address"]))
            score = self._similarity(normalized_text, addr_text)
            if score > best_score:
                best_score = score
                best_id = addr["address_id"]
        return best_id, best_score

    async def _safe_llm_parse(self, raw_address: str) -> dict | None:
        if not self.settings.groq_api_key:
            return None

        prompt = (
            "Extract the following fields from this Indian address:\n"
            f"Address: {raw_address}\n"
            "Return JSON with keys: flat, building, street, area, city, state, pincode.\n"
            "If a field is missing, use null."
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=200,
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception:
            return None

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

        comp_string = self._expand_abbreviations(
            self._basic_normalize(self._format_components(comps))
        )

        for _, addr in self.addresses.iterrows():
            addr_text = self._expand_abbreviations(
                self._basic_normalize(str(addr["canonical_address"]))
            )

            pincode_match = False
            if comps.get("pincode") and str(comps["pincode"]) == str(
                addr.get("pincode", "")
            ):
                pincode_match = True

            city_match = False
            if comps.get("city") and comps["city"].lower() in addr_text:
                city_match = True

            similarity = self._similarity(comp_string, addr_text)

            score = 0.0
            if pincode_match:
                score += 0.4
            if city_match:
                score += 0.2
            score += similarity * 0.4

            score = min(score, 1.0)

            if score > best_score:
                best_score = score
                best_id = addr["address_id"]

        return best_id, best_score
