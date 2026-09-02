import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

from backend.core.concurrency import ADDRESS_LLM_SEMAPHORE
from backend.core.config import get_settings
from backend.schemas.address import AddressComponents

# ============================================================================
# FIELD WEIGHTS
# ============================================================================

FIELD_WEIGHTS = {
    "pincode": 0.35,
    "city": 0.15,
    "area": 0.15,
    "street": 0.10,
    "building": 0.10,
    "house_no": 0.10,
    "state": 0.05,
    "district": 0.03,
    "country": 0.02,
    "landmark": 0.05,
}


# ============================================================================
# FIELD ALIASES
# ============================================================================

ALIASES = {
    "flat": "house_no",
    "flat_no": "house_no",
    "flat_number": "house_no",
    "house": "house_no",
    "house_number": "house_no",
    "hno": "house_no",
    "house_no": "house_no",
    "building_name": "building",
    "street_name": "street",
    "road": "street",
    "locality": "area",
    "neighborhood": "area",
    "neighbourhood": "area",
    "pin": "pincode",
    "postal_code": "pincode",
    "zip": "pincode",
}


# ============================================================================
# ABBREVIATIONS
# ============================================================================

ABBREVIATIONS = {
    r"\bapt\b": "apartment",
    r"\bappt\b": "apartment",
    r"\bflt\b": "flat",
    r"\bh\.?(?:\s*no\.?)\b": "house number",
    r"\bhno\b": "house number",
    r"\brd\b": "road",
    r"\bst\b": "street",
    r"\bave\b": "avenue",
    r"\bavn\b": "avenue",
    r"\bln\b": "lane",
    r"\bnr\b": "near",
    r"\bopp\b": "opposite",
    r"\bsec\b": "sector",
    r"\bblr\b": "bengaluru",
    r"\bbglr\b": "bengaluru",
    r"\bbangalore\b": "bengaluru",
    r"\bbombay\b": "mumbai",
    r"\bcalcutta\b": "kolkata",
    r"\bmadras\b": "chennai",
}


# ============================================================================
# CITY ALIASES
# ============================================================================

CITY_ALIASES = {
    "bengaluru": "bengaluru",
    "bangalore": "bengaluru",
    "blr": "bengaluru",
    "mumbai": "mumbai",
    "bombay": "mumbai",
    "kolkata": "kolkata",
    "calcutta": "kolkata",
    "chennai": "chennai",
    "madras": "chennai",
    "new delhi": "delhi",
    "delhi": "delhi",
    "hyderabad": "hyderabad",
    "pune": "pune",
    "ahmedabad": "ahmedabad",
    "jaipur": "jaipur",
    "surat": "surat",
    "lucknow": "lucknow",
    "kanpur": "kanpur",
    "nagpur": "nagpur",
    "indore": "indore",
    "bhopal": "bhopal",
    "patna": "patna",
    "kochi": "kochi",
    "coimbatore": "coimbatore",
}


# ============================================================================
# STATE ALIASES
# ============================================================================

STATE_ALIASES = {
    "ka": "karnataka",
    "karnataka": "karnataka",
    "mh": "maharashtra",
    "maharashtra": "maharashtra",
    "tn": "tamil nadu",
    "tamil nadu": "tamil nadu",
    "dl": "delhi",
    "delhi": "delhi",
    "gj": "gujarat",
    "gujarat": "gujarat",
    "rj": "rajasthan",
    "rajasthan": "rajasthan",
    "ts": "telangana",
    "telangana": "telangana",
    "wb": "west bengal",
    "west bengal": "west bengal",
    "up": "uttar pradesh",
    "uttar pradesh": "uttar pradesh",
    "mp": "madhya pradesh",
    "madhya pradesh": "madhya pradesh",
    "hr": "haryana",
    "haryana": "haryana",
    "pb": "punjab",
    "punjab": "punjab",
    "kl": "kerala",
    "kerala": "kerala",
    "ap": "andhra pradesh",
    "andhra pradesh": "andhra pradesh",
    "od": "odisha",
    "orissa": "odisha",
    "odisha": "odisha",
    "uk": "uttarakhand",
    "uttarakhand": "uttarakhand",
    "bihar": "bihar",
    "jharkhand": "jharkhand",
    "chhattisgarh": "chhattisgarh",
    "goa": "goa",
    "assam": "assam",
    "hp": "himachal pradesh",
    "himachal pradesh": "himachal pradesh",
    "jk": "jammu and kashmir",
    "jammu and kashmir": "jammu and kashmir",
    "chandigarh": "chandigarh",
}


class AddressNormalizerService:
    """
    Structured address extraction and verification service.

    Pipeline:

        raw address
            ↓
        structured extraction
            ↓
        user review/edit
            ↓
        indexed candidate retrieval
            ↓
        field-level weighted scoring
            ↓
        top 3 candidates
            ↓
        confidence + human-review decision

    SequenceMatcher is intentionally not used.
    """

    def __init__(self, addresses_path: Path):
        self.addresses = pd.read_csv(addresses_path).fillna("")

        required_columns = {
            "address_id",
            "canonical_address",
            "city",
            "pincode",
        }

        missing = required_columns - set(self.addresses.columns)

        if missing:
            raise ValueError(
                "Address dataset is missing required columns: " f"{sorted(missing)}"
            )

        settings = get_settings()

        self.client = (
            AsyncGroq(api_key=settings.groq_api_key)
            if (AsyncGroq is not None and settings.groq_api_key)
            else None
        )

        self.model = settings.groq_model

        self.records: list[dict[str, Any]] = []

        self.record_by_id: dict[
            str,
            dict[str, Any],
        ] = {}

        # Retrieval indexes.
        self.by_pincode: dict[
            str,
            set[int],
        ] = defaultdict(set)

        self.by_city: dict[
            str,
            set[int],
        ] = defaultdict(set)

        self.by_state: dict[
            str,
            set[int],
        ] = defaultdict(set)

        self.by_pincode_city: dict[
            tuple[str, str],
            set[int],
        ] = defaultdict(set)

        self.by_city_state: dict[
            tuple[str, str],
            set[int],
        ] = defaultdict(set)

        self.token_index: dict[
            str,
            set[int],
        ] = defaultdict(set)

        self._build_indexes()

    # ========================================================================
    # EXTRACTION
    # ========================================================================

    async def extract_components(
        self,
        raw_address: str,
    ) -> tuple[AddressComponents, str]:
        raw = str(raw_address or "").strip()

        if len(raw) < 3:
            raise ValueError("Address must contain at least 3 characters.")

        parsed = await self._safe_llm_parse(raw)

        if parsed:
            source = "llm_structured"
        else:
            parsed = self._deterministic_parse(raw)
            source = "deterministic_structured"

        cleaned = self._clean_components(parsed)

        return (
            AddressComponents(**cleaned),
            source,
        )

    # ========================================================================
    # VERIFICATION
    # ========================================================================

    def verify_components(
        self,
        raw_address: str | None,
        components: dict[str, Any],
    ) -> dict[str, Any]:
        cleaned = self._clean_components(components)

        raw = str(raw_address).strip() if raw_address else None

        if not any(cleaned.values()):
            return {
                "raw_address": raw,
                "normalized_address": None,
                "candidate_address_id": None,
                "confidence": 0.0,
                "requires_human_review": True,
                "components": cleaned,
                "matches": [],
                "candidate_count": 0,
                "matching_strategy": ("structured:no_components"),
                "review_reasons": ["At least one address component is required."],
            }

        candidates, strategy = self._retrieve_candidates(cleaned)

        ranked = self._rank(
            query=cleaned,
            candidate_indexes=candidates,
        )

        if not ranked:
            return {
                "raw_address": raw,
                "normalized_address": (self._format_components(cleaned)),
                "candidate_address_id": None,
                "confidence": 0.0,
                "requires_human_review": True,
                "components": cleaned,
                "matches": [],
                "candidate_count": len(candidates),
                "matching_strategy": (f"structured:{strategy}"),
                "review_reasons": [
                    "No candidate address matched the supplied components."
                ],
            }

        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else None

        reasons: list[str] = []

        active_fields = sum(bool(cleaned.get(field)) for field in FIELD_WEIGHTS)

        if best["score"] < 0.72:
            reasons.append(
                "Best candidate similarity is below the safe acceptance threshold."
            )

        if second is not None and best["score"] - second["score"] < 0.05:
            reasons.append(
                "The top candidates are too close to distinguish confidently."
            )

        if not cleaned.get("pincode"):
            reasons.append(
                "Pincode is missing; verification cannot use the strongest location key."
            )

        if not cleaned.get("city"):
            reasons.append("City is missing; location-level verification is weaker.")

        if active_fields < 3:
            reasons.append(
                "Only a small number of components are available for verification."
            )

        confidence = self._confidence(
            best=best["score"],
            second=(second["score"] if second else None),
            components=cleaned,
        )

        if confidence < 0.85:
            reasons.append(
                "Overall confidence is below the automatic acceptance threshold."
            )

        accepted = best["score"] >= 0.60

        return {
            "raw_address": raw,
            "normalized_address": (
                best["canonical_address"]
                if accepted
                else self._format_components(cleaned)
            ),
            "candidate_address_id": (best["address_id"] if accepted else None),
            "confidence": round(
                confidence,
                3,
            ),
            "requires_human_review": bool(reasons),
            "components": cleaned,
            "matches": [self._public_match(item) for item in ranked[:3]],
            "candidate_count": len(candidates),
            "matching_strategy": (f"structured:{strategy}"),
            "review_reasons": reasons,
        }

    # ========================================================================
    # BACKWARD-COMPATIBLE COMBINED FLOW
    # ========================================================================

    async def normalize(
        self,
        raw_address: str,
        components: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw = str(raw_address or "").strip()

        if len(raw) < 3:
            raise ValueError("Address must contain at least 3 characters.")

        if components is None:
            extracted, source = await self.extract_components(raw)

            result = self.verify_components(
                raw_address=raw,
                components=extracted.model_dump(),
            )

            result["matching_strategy"] = f"{source}+" f"{result['matching_strategy']}"

            return result

        return self.verify_components(
            raw_address=raw,
            components=components,
        )

    # ========================================================================
    # INDEXING
    # ========================================================================

    def _build_indexes(self) -> None:
        for row_index, row in self.addresses.iterrows():
            address_id = str(row["address_id"]).strip()

            canonical = str(row["canonical_address"]).strip()

            city = self._canonical_city(str(row["city"]))

            pincode = self._clean_pincode(row["pincode"])

            components = self._parse_canonical(
                canonical=canonical,
                city=city,
                pincode=pincode,
            )

            record = {
                "address_id": address_id,
                "canonical_address": canonical,
                "city": city,
                "pincode": pincode,
                "components": components,
            }

            self.records.append(record)

            self.record_by_id[address_id] = record

            if pincode:
                self.by_pincode[pincode].add(row_index)

            if city:
                self.by_city[city].add(row_index)

            state = components.get("state")

            if state:
                self.by_state[state].add(row_index)

            if pincode and city:
                self.by_pincode_city[(pincode, city)].add(row_index)

            if city and state:
                self.by_city_state[(city, state)].add(row_index)

            for token in self._tokens(canonical):
                self.token_index[token].add(row_index)

    # ========================================================================
    # CANONICAL ADDRESS PARSING
    # ========================================================================

    def _parse_canonical(
        self,
        canonical: str,
        city: str,
        pincode: str,
    ) -> dict[str, str | None]:
        text = self._expand(self._basic(canonical))

        house = self._extract_house(text)

        detected_city = city or self._detect_city(text)

        state = self._detect_state(text)

        detected_pin = pincode or self._extract_pincode(text)

        segments = [
            self._basic(segment)
            for segment in re.split(
                r"[,;|]+",
                canonical,
            )
            if self._basic(segment)
        ]

        street = self._extract_street(text)

        residual = text

        for value in (
            detected_pin,
            detected_city,
            state,
            "india",
            house,
        ):
            if value:
                residual = residual.replace(
                    self._basic(value),
                    " ",
                )

        residual = re.sub(
            r"\s+",
            " ",
            residual,
        ).strip()

        area = self._derive_area(
            residual=residual,
            street=street,
        )

        building = self._derive_building(
            residual=residual,
            street=street,
            area=area,
            house_no=house,
        )

        # If a comma-separated segment looks like a building/society name,
        # prefer it over a generic residual-derived value.
        if segments and not building:
            excluded = {
                detected_city,
                state,
                detected_pin,
            }

            for segment in segments:
                if not segment or segment in excluded:
                    continue

                if re.fullmatch(
                    r"(?:house|flat|hno)\s*\w+",
                    segment,
                ):
                    continue

                building = segment
                break

        return {
            "house_no": house,
            "building": building,
            "street": street,
            "area": area,
            "landmark": None,
            "city": (detected_city or None),
            "district": None,
            "state": (state or None),
            "country": (
                "india"
                if re.search(
                    r"\b(?:india|bharat)\b",
                    text,
                )
                else None
            ),
            "pincode": (detected_pin or None),
        }

    # ========================================================================
    # LLM EXTRACTION
    # ========================================================================

    async def _safe_llm_parse(
        self,
        raw_address: str,
    ) -> dict[str, Any] | None:
        if not self.client:
            return None

        prompt = f"""
Extract the structure of this Indian postal address.

ADDRESS:
{raw_address}

Return JSON only with exactly these keys:
house_no
building
street
area
landmark
city
district
state
country
pincode

Rules:
- Never invent a component.
- Use null when a field is missing or uncertain.
- Keep house/flat numbers as strings.
- Keep pincode as a six-digit string when present.
- Normalize Bangalore/Bengaluru to Bengaluru.
- Normalize Bombay/Mumbai to Mumbai.
- Normalize Calcutta/Kolkata to Kolkata.
- Normalize Madras/Chennai to Chennai.
- Preserve building, society, street, road, locality,
  landmark, and area names.
- Do not produce a single normalized address sentence.
"""

        try:
            async with ADDRESS_LLM_SEMAPHORE:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a high-precision "
                                "Indian postal-address "
                                "information extraction "
                                "system. Return valid JSON only."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=300,
                )

            content = response.choices[0].message.content or ""

            parsed = json.loads(self._strip_code_fence(content))

            return parsed if isinstance(parsed, dict) else None

        except Exception:
            # Extraction must gracefully fall back to deterministic parsing.
            return None

    # ========================================================================
    # DETERMINISTIC EXTRACTION FALLBACK
    # ========================================================================

    def _deterministic_parse(
        self,
        raw_address: str,
    ) -> dict[str, Any]:
        text = self._expand(self._basic(raw_address))

        components = {
            "house_no": self._extract_house(text),
            "building": None,
            "street": self._extract_street(text),
            "area": None,
            "landmark": None,
            "city": (self._detect_city(text) or None),
            "district": None,
            "state": (self._detect_state(text) or None),
            "country": (
                "india"
                if re.search(
                    r"\b(?:india|bharat)\b",
                    text,
                )
                else None
            ),
            "pincode": (self._extract_pincode(text) or None),
        }

        residual = text

        for value in (
            components["pincode"],
            components["city"],
            components["state"],
            components["country"],
            components["street"],
            components["house_no"],
        ):
            if value:
                residual = residual.replace(
                    self._basic(value),
                    " ",
                )

        residual = re.sub(
            r"\s+",
            " ",
            residual,
        ).strip()

        components["area"] = self._derive_area(
            residual=residual,
            street=components["street"],
        )

        components["building"] = self._derive_building(
            residual=residual,
            street=components["street"],
            area=components["area"],
            house_no=components["house_no"],
        )

        return components

    # ========================================================================
    # CANDIDATE RETRIEVAL
    # ========================================================================

    def _retrieve_candidates(
        self,
        components: dict[str, Any],
    ) -> tuple[list[int], str]:
        pincode = self._clean_pincode(components.get("pincode"))

        city = self._canonical_city(str(components.get("city") or ""))

        state = self._canonical_state(str(components.get("state") or ""))

        # Strongest: pincode + city.
        if pincode and city:
            candidates = self.by_pincode_city.get(
                (pincode, city),
                set(),
            )

            if candidates:
                return (
                    list(candidates),
                    "pincode+city",
                )

        # Next: exact pincode.
        if pincode:
            candidates = self.by_pincode.get(
                pincode,
                set(),
            )

            if candidates:
                return (
                    list(candidates),
                    "pincode",
                )

        # Next: city + state.
        if city and state:
            candidates = self.by_city_state.get(
                (city, state),
                set(),
            )

            if candidates:
                return (
                    list(candidates),
                    "city+state",
                )

        # Next: city.
        if city:
            candidates = self.by_city.get(
                city,
                set(),
            )

            if candidates:
                return (
                    list(candidates),
                    "city",
                )

        # Token retrieval for incomplete addresses.
        query_tokens = self._query_tokens(components)

        ranked_tokens = sorted(
            query_tokens,
            key=lambda token: len(
                self.token_index.get(
                    token,
                    set(),
                )
            ),
        )[:5]

        if ranked_tokens:
            token_sets = [
                self.token_index.get(
                    token,
                    set(),
                )
                for token in ranked_tokens
            ]

            intersection = set(token_sets[0])

            for values in token_sets[1:]:
                intersection &= values

            if intersection:
                return (
                    list(intersection),
                    "token_intersection",
                )

            union = set().union(*token_sets)

            if union:
                return (
                    list(union)[:2500],
                    "token_union",
                )

        # Last resort only.
        return (
            list(range(len(self.records))),
            "full_scan_fallback",
        )

    # ========================================================================
    # RANKING
    # ========================================================================

    def _rank(
        self,
        query: dict[str, Any],
        candidate_indexes: list[int],
    ) -> list[dict[str, Any]]:
        results = []

        for index in candidate_indexes:
            record = self.records[index]

            score, field_scores, exact_fields = self._score_components(
                query=query,
                candidate=record["components"],
            )

            results.append(
                {
                    "address_id": record["address_id"],
                    "canonical_address": (record["canonical_address"]),
                    "score": score,
                    "matched_fields": field_scores,
                    "exact_fields": exact_fields,
                    "_record": record,
                }
            )

        results.sort(
            key=lambda item: (
                item["score"],
                len(item["exact_fields"]),
            ),
            reverse=True,
        )

        return results

    def _score_components(
        self,
        query: dict[str, Any],
        candidate: dict[str, Any],
    ) -> tuple[
        float,
        dict[str, float],
        list[str],
    ]:
        weighted_sum = 0.0
        active_weight = 0.0

        field_scores: dict[
            str,
            float,
        ] = {}

        exact_fields: list[str] = []

        for field, weight in FIELD_WEIGHTS.items():
            left = query.get(field)
            right = candidate.get(field)

            if self._missing(left) or self._missing(right):
                continue

            left = self._field_normalize(
                field,
                left,
            )

            right = self._field_normalize(
                field,
                right,
            )

            if not left or not right:
                continue

            similarity = self._field_similarity(
                field,
                left,
                right,
            )

            field_scores[field] = round(
                similarity,
                4,
            )

            weighted_sum += weight * similarity

            active_weight += weight

            if similarity >= 0.999:
                exact_fields.append(field)

        if active_weight == 0:
            return (
                0.0,
                field_scores,
                exact_fields,
            )

        # Renormalize when some fields are missing.
        score = weighted_sum / active_weight

        strong_exact = sum(
            field in exact_fields
            for field in (
                "pincode",
                "city",
                "house_no",
                "building",
            )
        )

        if strong_exact >= 2:
            score = min(
                1.0,
                score + 0.04,
            )

        return (
            score,
            field_scores,
            exact_fields,
        )

    # ========================================================================
    # FIELD SIMILARITY
    # ========================================================================

    def _field_similarity(
        self,
        field: str,
        left: str,
        right: str,
    ) -> float:
        if left == right:
            return 1.0

        # Pincode must be exact.
        if field == "pincode":
            return 0.0

        token_score = self._token_similarity(
            left,
            right,
        )

        # Strong categorical/location fields.
        if field in {
            "city",
            "state",
            "district",
            "country",
        }:
            return token_score

        ngram_score = self._ngram_similarity(
            left,
            right,
        )

        containment = float(left in right or right in left)

        return min(
            1.0,
            (0.55 * token_score + 0.30 * ngram_score + 0.15 * containment),
        )

    # ========================================================================
    # CONFIDENCE
    # ========================================================================

    def _confidence(
        self,
        best: float,
        second: float | None,
        components: dict[str, Any],
    ) -> float:
        confidence = best

        if second is not None:
            confidence += min(
                0.08,
                max(
                    0.0,
                    best - second,
                ),
            )

        strong_field_count = sum(
            bool(components.get(field))
            for field in (
                "pincode",
                "city",
                "house_no",
                "building",
            )
        )

        if strong_field_count >= 3:
            confidence += 0.04

        elif strong_field_count == 2:
            confidence += 0.02

        return max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

    # ========================================================================
    # COMPONENT CLEANING
    # ========================================================================

    def _clean_components(
        self,
        components: dict[str, Any] | None,
    ) -> dict[str, Any]:
        result = {field: None for field in FIELD_WEIGHTS}

        for key, value in (components or {}).items():
            field = ALIASES.get(
                key,
                key,
            )

            if field not in result or self._missing(value):
                continue

            text = str(value).strip()

            if field == "pincode":
                text = self._clean_pincode(text)

            elif field == "city":
                text = self._canonical_city(text)

            elif field == "state":
                text = self._canonical_state(text)

            elif field == "country":
                normalized = self._basic(text)

                text = (
                    "india"
                    if normalized
                    in {
                        "india",
                        "bharat",
                        "in",
                    }
                    else normalized
                )

            elif field == "house_no":
                text = self._canonical_house(text)

            else:
                text = self._expand(self._basic(text))

            result[field] = text or None

        return result

    def _field_normalize(
        self,
        field: str,
        value: Any,
    ) -> str:
        text = str(value or "").strip()

        if field == "pincode":
            return self._clean_pincode(text)

        if field == "city":
            return self._canonical_city(text)

        if field == "state":
            return self._canonical_state(text)

        if field == "country":
            normalized = self._basic(text)

            return (
                "india"
                if normalized
                in {
                    "india",
                    "bharat",
                    "in",
                }
                else normalized
            )

        if field == "house_no":
            return self._canonical_house(text)

        return self._expand(self._basic(text))

    # ========================================================================
    # EXTRACTION HELPERS
    # ========================================================================

    def _extract_house(
        self,
        text: str,
    ) -> str | None:
        patterns = [
            (
                r"\b(?:house number|house no|hno|"
                r"house|flat|apartment|plot)\s*"
                r"([a-z]?\d+[a-z]?)\b"
            ),
            r"^\s*([a-z]?\d+[a-z]?)\b",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                text,
                flags=re.I,
            )

            if match:
                return match.group(1)

        return None

    @staticmethod
    def _extract_pincode(
        text: str,
    ) -> str:
        match = re.search(
            r"\b(\d{6})\b",
            text,
        )

        return match.group(1) if match else ""

    def _detect_city(
        self,
        text: str,
    ) -> str:
        normalized = self._basic(text)

        for alias, canonical in sorted(
            CITY_ALIASES.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if re.search(
                rf"\b{re.escape(alias)}\b",
                normalized,
            ):
                return canonical

        return ""

    def _detect_state(
        self,
        text: str,
    ) -> str:
        normalized = self._basic(text)

        for alias, canonical in sorted(
            STATE_ALIASES.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if re.search(
                rf"\b{re.escape(alias)}\b",
                normalized,
            ):
                return canonical

        return ""

    def _extract_street(
        self,
        text: str,
    ) -> str | None:
        words = text.split()

        markers = {
            "road",
            "street",
            "lane",
            "avenue",
            "highway",
            "marg",
        }

        marker_index = next(
            (index for index, word in enumerate(words) if word in markers),
            None,
        )

        if marker_index is None:
            return None

        start = max(
            0,
            marker_index - 2,
        )

        selected = words[start : marker_index + 1]

        # Do not let a leading house number become part of street.
        if selected and re.fullmatch(
            r"[a-z]?\d+[a-z]?",
            selected[0],
        ):
            selected = selected[1:]

        while selected and selected[0] in {
            "near",
            "opposite",
        }:
            selected = selected[1:]

        return " ".join(selected) if selected else None

    def _derive_area(
        self,
        residual: str,
        street: str | None,
    ) -> str | None:
        text = residual

        if street:
            text = text.replace(
                street,
                " ",
            )

        words = (
            re.sub(
                r"\s+",
                " ",
                text,
            )
            .strip()
            .split()
        )

        if not words:
            return None

        for marker in (
            "colony",
            "nagar",
            "sector",
            "layout",
            "phase",
        ):
            if marker in words:
                index = words.index(marker)

                return " ".join(words[index : index + 2])

        if len(words) >= 2:
            return " ".join(words[-2:])

        return words[0]

    def _derive_building(
        self,
        residual: str,
        street: str | None,
        area: str | None,
        house_no: str | None,
    ) -> str | None:
        text = residual

        for value in (
            street,
            area,
            house_no,
        ):
            if value:
                text = text.replace(
                    str(value),
                    " ",
                )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        return text[:120] if text else None

    # ========================================================================
    # TOKEN / SIMILARITY HELPERS
    # ========================================================================

    def _query_tokens(
        self,
        components: dict[str, Any],
    ) -> set[str]:
        tokens: set[str] = set()

        for field, value in components.items():
            if value and field != "pincode":
                tokens.update(self._tokens(str(value)))

        return tokens

    def _tokens(
        self,
        text: str,
    ) -> set[str]:
        normalized = self._expand(self._basic(text))

        return {
            token
            for token in normalized.split()
            if (
                len(token) > 1
                and token
                not in {
                    "the",
                    "road",
                    "street",
                    "lane",
                    "near",
                    "opposite",
                }
            )
        }

    def _token_similarity(
        self,
        left: str,
        right: str,
    ) -> float:
        left_tokens = self._tokens(left)

        right_tokens = self._tokens(right)

        if not left_tokens or not right_tokens:
            return 0.0

        union = left_tokens | right_tokens

        return len(left_tokens & right_tokens) / len(union) if union else 0.0

    def _ngram_similarity(
        self,
        left: str,
        right: str,
        n: int = 3,
    ) -> float:
        left = self._basic(left).replace(" ", "")

        right = self._basic(right).replace(" ", "")

        if left == right:
            return 1.0

        if len(left) < n or len(right) < n:
            return 0.0

        left_ngrams = {left[index : index + n] for index in range(len(left) - n + 1)}

        right_ngrams = {right[index : index + n] for index in range(len(right) - n + 1)}

        union = left_ngrams | right_ngrams

        return len(left_ngrams & right_ngrams) / len(union) if union else 0.0

    # ========================================================================
    # CANONICALIZATION
    # ========================================================================

    def _canonical_city(
        self,
        value: str,
    ) -> str:
        text = self._basic(value)

        return CITY_ALIASES.get(
            text,
            text,
        )

    def _canonical_state(
        self,
        value: str,
    ) -> str:
        text = self._basic(value)

        return STATE_ALIASES.get(
            text,
            text,
        )

    def _canonical_house(
        self,
        value: str,
    ) -> str:
        text = self._basic(value)

        return re.sub(
            r"^(?:flat|apartment|house number|" r"house no|house|hno|plot)\s+",
            "",
            text,
        ).strip()

    @staticmethod
    def _clean_pincode(
        value: Any,
    ) -> str:
        text = str(value or "").strip()

        if text.endswith(".0") and text[:-2].isdigit():
            text = text[:-2]

        match = re.search(
            r"\b(\d{6})\b",
            text,
        )

        return match.group(1) if match else ""

    @staticmethod
    def _basic(
        text: str,
    ) -> str:
        text = str(text or "").lower().replace("&", " and ")

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

    def _expand(
        self,
        text: str,
    ) -> str:
        result = text

        for (
            pattern,
            replacement,
        ) in ABBREVIATIONS.items():
            result = re.sub(
                pattern,
                replacement,
                result,
            )

        return self._basic(result)

    @staticmethod
    def _strip_code_fence(
        text: str,
    ) -> str:
        text = text.strip()

        if text.startswith("```"):
            text = re.sub(
                r"^```(?:json)?",
                "",
                text,
                flags=re.I,
            )

            text = re.sub(
                r"```$",
                "",
                text,
            )

        return text.strip()

    # ========================================================================
    # RESULT HELPERS
    # ========================================================================

    @staticmethod
    def _format_components(
        components: dict[str, Any],
    ) -> str:
        field_order = [
            "house_no",
            "building",
            "street",
            "area",
            "landmark",
            "city",
            "district",
            "state",
            "pincode",
            "country",
        ]

        return ", ".join(
            str(components[field]).strip()
            for field in field_order
            if components.get(field)
        )

    @staticmethod
    def _public_match(
        match: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "address_id": match["address_id"],
            "canonical_address": match["canonical_address"],
            "score": round(
                float(match["score"]),
                3,
            ),
            "matched_fields": match["matched_fields"],
            "exact_fields": match["exact_fields"],
        }

    @staticmethod
    def _missing(
        value: Any,
    ) -> bool:
        if value is None:
            return True

        try:
            if pd.isna(value):
                return True
        except (
            TypeError,
            ValueError,
        ):
            pass

        return not str(value).strip()
