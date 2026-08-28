"""RingWatch dataset generation entry point.

This entry point intentionally keeps the historical Day-1/Day-3 validation
contract while using the cohesive V4 data-generating process.
"""
from .realistic_engine import generate_dataset
from .validate import validate_entities, validate_day3
from .quality_audit import run as run_quality_audit


def main():
    print("=" * 60)
    print("RINGWATCH V4 — REALISTIC DATASET GENERATION")
    print("=" * 60)
    generate_dataset()

    print("\nRunning entity validation...")
    validate_entities()

    print("\nRunning final Day-3 validation...")
    validate_day3()

    print("\nRunning V4 anti-shortcut quality audit...")
    audit = run_quality_audit()
    if not audit["anti_shortcut_passed"]:
        raise RuntimeError("V4 anti-shortcut quality audit failed.")

    print("\n" + "=" * 60)
    print("RINGWATCH V4 DATASET GENERATION + VALIDATION PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
