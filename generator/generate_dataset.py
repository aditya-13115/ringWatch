from .entities import generate_all_entities

from .normal_orders import (
    load_entities,
    generate_normal_orders,
)

from .rings import run_ring_injection

from .hard_negatives import (
    run_hard_negatives,
)

from .refunds_disputes import (
    run_refunds_disputes,
)

from .ground_truth import (
    run_ground_truth,
)

from .validate import (
    validate_entities,
    validate_orders,
    validate_day3,
)

from .config import PATHS


def main():

    # ========================================================
    # DAY 1
    # ========================================================

    print("Generating RingWatch Day 1...")

    generate_all_entities()

    print("\nRunning entity validation...")

    validate_entities()

    # ========================================================
    # DAY 2
    # ========================================================

    print("\nGenerating normal orders...")

    (
        accounts,
        devices,
        addresses,
        phones,
        instruments,
    ) = load_entities()

    orders_df = generate_normal_orders(
        accounts,
        devices,
        addresses,
        phones,
        instruments,
    )

    orders_df.to_csv(
        PATHS["orders"],
        index=False,
    )

    print(f"Normal orders generated: " f"{len(orders_df):,}")

    print("\nRunning order validation...")

    validate_orders()

    # ========================================================
    # DAY 3 — RINGS
    # ========================================================

    print("\n===================================")

    print("DAY 3 — INJECTING ABUSE RINGS")

    print("===================================")

    (
        accounts,
        devices,
        addresses,
        phones,
        instruments,
        orders_df,
        ring_members,
    ) = run_ring_injection()

    # Validate orders after rings.
    print("\nValidating after ring injection...")

    # At this stage validate_orders()
    # must NOT be called because its Day-2
    # rule intentionally rejects non-normal
    # accounts.
    print("Ring injection completed.")

    # ========================================================
    # DAY 3 — HARD NEGATIVES
    # ========================================================

    print("\n===================================")

    print("DAY 3 — INJECTING HARD NEGATIVES")

    print("===================================")

    (
        accounts,
        devices,
        addresses,
        phones,
        instruments,
        orders_df,
    ) = run_hard_negatives()

    print("Hard-negative injection completed.")

    # ========================================================
    # DAY 3 — REFUNDS / DISPUTES
    # ========================================================

    print("\n===================================")

    print("DAY 3 — GENERATING REFUNDS/DISPUTES")

    print("===================================")

    (
        orders_df,
        refunds_df,
        disputes_df,
    ) = run_refunds_disputes()

    print("Refund/dispute generation completed.")

    # ========================================================
    # DAY 3 — GROUND TRUTH
    # ========================================================

    print("\n===================================")

    print("DAY 3 — GENERATING GROUND TRUTH")

    print("===================================")

    ground_truth_df = run_ground_truth(
        accounts,
        ring_members,
    )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    print("\n===================================")

    print("RUNNING FINAL DAY-3 VALIDATION")

    print("===================================")

    validate_day3()

    print("\n===================================")

    print("RINGWATCH DAY-3 COMPLETED")

    print("===================================")


if __name__ == "__main__":
    main()
