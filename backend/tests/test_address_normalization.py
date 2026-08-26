import asyncio

from backend.services.address_normalizer_service import AddressNormalizerService
from backend.core.config import get_settings


async def main():
    settings = get_settings()
    service = AddressNormalizerService(settings.addresses_path)

    # Use a few real addresses from the dataset
    sample = service.addresses.sample(3, random_state=42)

    for _, row in sample.iterrows():
        canonical = row["canonical_address"]
        address_id = row["address_id"]

        # Create variations
        variations = {
            "exact": canonical,
            "lowercase": canonical.lower(),
            "no pincode": canonical.rsplit(",", 1)[0].strip(),
            "abbreviation": canonical.replace("Road", "Rd").replace("Street", "St"),
        }

        for label, raw in variations.items():
            result = await service.normalize(raw)
            print(f"Case: {label}")
            print(f"  Raw: {raw}")
            print(f"  Normalized: {result['normalized_address']}")
            print(f"  Candidate: {result['candidate_address_id']}")
            print(f"  Confidence: {result['confidence']:.2f}")
            print(f"  Human Review: {result['requires_human_review']}\n")


if __name__ == "__main__":
    asyncio.run(main())