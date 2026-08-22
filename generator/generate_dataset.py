from .entities import generate_all_entities
from .normal_orders import (
    load_entities,
    generate_normal_orders,
)
from .validate import (
    validate_entities,
    validate_orders,
)
from .config import PATHS


def main():

    print("Generating RingWatch Day 1...")

    generate_all_entities()

    print("\nRunning entity validation...")

    validate_entities()

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

    print(
        f"Normal orders generated: "
        f"{len(orders_df):,}"
    )

    print("\nRunning order validation...")

    validate_orders()

    print("\n===================================")
    print("RINGWATCH DAY-2 COMPLETED")
    print("===================================")


if __name__ == "__main__":
    main()