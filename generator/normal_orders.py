import numpy as np
import pandas as pd

from .config import (
    SEED,
    END_DATE,
    PATHS,
)

from .ids import make_order_id


rng = np.random.default_rng(SEED)


CATEGORY_RANGES = {
    "electronics": (2000, 20000),
    "fashion": (800, 5000),
    "grocery": (300, 3000),
    "home": (1000, 8000),
    "books": (200, 2000),
    "toys": (500, 4000),
}

CATEGORY_WEIGHTS = [
    0.15,
    0.30,
    0.20,
    0.15,
    0.10,
    0.10,
]


def load_entities():

    accounts = pd.read_csv(
        PATHS["accounts"],
        parse_dates=["account_created_at"],
    )

    devices = pd.read_csv(
        PATHS["devices"],
        parse_dates=["first_seen_at"],
    )

    addresses = pd.read_csv(
        PATHS["addresses"],
        parse_dates=["first_seen_at"],
    )

    phones = pd.read_csv(
        PATHS["phones"],
        parse_dates=["first_seen_at"],
    )

    instruments = pd.read_csv(
        PATHS["payment_instruments"],
        parse_dates=["first_seen_at"],
    )

    return (
        accounts,
        devices,
        addresses,
        phones,
        instruments,
    )


def random_datetime_after(start, end):

    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    if start >= end:
        return start

    seconds = int(
        (end - start).total_seconds()
    )

    offset = rng.integers(
        0,
        seconds + 1,
    )

    return start + pd.Timedelta(
        seconds=int(offset)
    )


def assign_entities(
    account_created,
    devices,
    addresses,
    phones,
    instruments,
):
    """
    Assign 1–2 devices, 1–2 addresses,
    1 phone and 1–2 payment instruments.

    Only entities that existed by the
    account creation timestamp are eligible.
    """

    available_devices = devices[
        devices["first_seen_at"] <= account_created
    ]

    available_addresses = addresses[
        addresses["first_seen_at"] <= account_created
    ]

    available_phones = phones[
        phones["first_seen_at"] <= account_created
    ]

    available_instruments = instruments[
        instruments["first_seen_at"] <= account_created
    ]

    # If not enough entities existed yet,
    # fall back to earliest available entities.
    if len(available_devices) < 1:
        available_devices = devices.nsmallest(
            1,
            "first_seen_at",
        )

    if len(available_addresses) < 1:
        available_addresses = addresses.nsmallest(
            1,
            "first_seen_at",
        )

    if len(available_phones) < 1:
        available_phones = phones.nsmallest(
            1,
            "first_seen_at",
        )

    if len(available_instruments) < 1:
        available_instruments = instruments.nsmallest(
            1,
            "first_seen_at",
        )

    n_devices = min(
        int(rng.integers(1, 3)),
        len(available_devices),
    )

    n_addresses = min(
        int(rng.integers(1, 3)),
        len(available_addresses),
    )

    n_instruments = min(
        int(rng.integers(1, 3)),
        len(available_instruments),
    )

    selected_devices = (
        available_devices.sample(
            n=n_devices,
            random_state=int(rng.integers(0, 1_000_000)),
        )["device_id"]
        .tolist()
    )

    selected_addresses = (
        available_addresses.sample(
            n=n_addresses,
            random_state=int(rng.integers(0, 1_000_000)),
        )["address_id"]
        .tolist()
    )

    selected_phone = (
        available_phones.sample(
            n=1,
            random_state=int(rng.integers(0, 1_000_000)),
        )["phone_hash"]
        .tolist()
    )

    selected_instruments = (
        available_instruments.sample(
            n=n_instruments,
            random_state=int(rng.integers(0, 1_000_000)),
        )["instrument_id"]
        .tolist()
    )

    return {
        "devices": selected_devices,
        "addresses": selected_addresses,
        "phones": selected_phone,
        "instruments": selected_instruments,
    }


def get_entity_first_seen(
    entity_df,
    id_column,
    entity_id,
):
    row = entity_df[
        entity_df[id_column] == entity_id
    ]

    return pd.Timestamp(
        row.iloc[0]["first_seen_at"]
    )


def generate_order_amount(category):

    low, high = CATEGORY_RANGES[category]

    amount = rng.integers(
        low,
        high + 1,
    )

    # Round to nearest ₹10.
    amount = int(round(amount / 10) * 10)

    return float(amount)


def generate_discount(amount):

    discount_amount = 0.0
    coupon_code = None

    roll = rng.random()

    # ~80% no discount
    if roll < 0.80:
        return discount_amount, coupon_code

    # ~18% ordinary discount
    if roll < 0.98:

        discount_pct = rng.uniform(
            0.05,
            0.15,
        )

        discount_amount = round(
            amount * discount_pct,
            2,
        )

        return discount_amount, coupon_code

    # ~2% rare coupon
    coupon_code = (
        f"RARE_{rng.integers(100, 1000)}"
    )

    discount_pct = rng.uniform(
        0.20,
        0.40,
    )

    discount_amount = round(
        amount * discount_pct,
        2,
    )

    return discount_amount, coupon_code


def generate_delivery(order_timestamp):

    roll = rng.random()

    # 90% delivered
    if roll < 0.90:

        delivery_timestamp = (
            order_timestamp
            + pd.Timedelta(
                days=int(
                    rng.integers(1, 5)
                )
            )
        )

        return {
            "delivery_status": "delivered",
            "delivery_timestamp": delivery_timestamp,
            "delivery_attempts": int(
                rng.integers(1, 4)
            ),
            "rto_flag": False,
        }

    # 5% pending
    if roll < 0.95:

        return {
            "delivery_status": "pending",
            "delivery_timestamp": pd.NaT,
            "delivery_attempts": int(
                rng.integers(1, 3)
            ),
            "rto_flag": False,
        }

    # 5% failed / RTO
    return {
        "delivery_status": "failed",
        "delivery_timestamp": pd.NaT,
        "delivery_attempts": int(
            rng.integers(1, 3)
        ),
        "rto_flag": True,
    }


def generate_normal_orders(
    accounts,
    devices,
    addresses,
    phones,
    instruments,
):

    # CRITICAL:
    # Ring and hard-negative accounts are excluded.
    normal_accounts = accounts[
        accounts["population_type"] == "normal"
    ].copy()

    orders = []

    order_counter = 0

    for _, account in normal_accounts.iterrows():

        n_orders = int(
            rng.negative_binomial(
                n=3,
                p=0.6,
            )
        )

        if n_orders == 0:
            continue

        account_id = account["account_id"]

        account_created = pd.Timestamp(
            account["account_created_at"]
        )

        account_entities = assign_entities(
            account_created,
            devices,
            addresses,
            phones,
            instruments,
        )

        for _ in range(n_orders):

            # Choose entities for this order.
            device_id = rng.choice(
                account_entities["devices"]
            )

            address_id = rng.choice(
                account_entities["addresses"]
            )

            phone_hash = rng.choice(
                account_entities["phones"]
            )

            instrument_id = rng.choice(
                account_entities["instruments"]
            )

            # Find when those entities first existed.
            device_first_seen = get_entity_first_seen(
                devices,
                "device_id",
                device_id,
            )

            address_first_seen = get_entity_first_seen(
                addresses,
                "address_id",
                address_id,
            )

            phone_first_seen = get_entity_first_seen(
                phones,
                "phone_hash",
                phone_hash,
            )

            instrument_first_seen = get_entity_first_seen(
                instruments,
                "instrument_id",
                instrument_id,
            )

            earliest_possible = max(
                account_created,
                device_first_seen,
                address_first_seen,
                phone_first_seen,
                instrument_first_seen,
            )

            # Generate order timestamp only after
            # every associated entity exists.
            order_timestamp = random_datetime_after(
                earliest_possible,
                END_DATE,
            )

            # Category
            category = rng.choice(
                list(CATEGORY_RANGES.keys()),
                p=CATEGORY_WEIGHTS,
            )

            # Amount
            amount = generate_order_amount(
                category
            )

            # Discount
            discount_amount, coupon_code = (
                generate_discount(amount)
            )

            # Delivery
            delivery = generate_delivery(
                order_timestamp
            )

            order_id = make_order_id(
                order_counter
            )

            order_counter += 1

            orders.append(
                {
                    "order_id": order_id,
                    "account_id": account_id,

                    "device_id": device_id,
                    "address_id": address_id,
                    "phone_hash": phone_hash,
                    "instrument_id": instrument_id,

                    "amount": amount,
                    "discount_amount": discount_amount,
                    "coupon_code": coupon_code,

                    "category": category,

                    "order_timestamp": order_timestamp,

                    "delivery_status":
                        delivery["delivery_status"],

                    "delivery_attempts":
                        delivery["delivery_attempts"],

                    "delivery_timestamp":
                        delivery["delivery_timestamp"],

                    "rto_flag":
                        delivery["rto_flag"],

                    # These remain untouched until
                    # refunds_disputes.py.
                    "return_flag": False,
                    "return_reason_code": None,
                    "return_timestamp": pd.NaT,
                    "return_lag_hours": None,

                    "refund_flag": False,
                    "refund_amount": None,
                    "refund_timestamp": pd.NaT,

                    "dispute_flag": False,
                    "dispute_phase": None,
                    "dispute_reason_code": None,
                    "dispute_reason_category": None,

                    # Evidence will be populated later.
                    "evidence_availability": None,
                }
            )

    return pd.DataFrame(orders)


def main():

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


if __name__ == "__main__":
    main()