import numpy as np
import pandas as pd

from .config import PATHS, SEED
from .ids import (
    make_order_id,
    make_device_id,
    make_address_id,
    make_phone_hash,
    make_instrument_id,
    make_instrument_hash,
)

rng = np.random.default_rng(SEED)


# ============================================================
# HELPERS
# ============================================================


def next_numeric_id(series):

    if len(series) == 0:
        return 0

    values = series.astype(str).str.extract(r"(\d+)$")[0]

    values = pd.to_numeric(
        values,
        errors="coerce",
    ).dropna()

    if len(values) == 0:
        return 0

    return int(values.max()) + 1


def next_order_id(orders):

    if len(orders) == 0:
        return 0

    numbers = (
        orders["order_id"]
        .astype(str)
        .str.replace(
            "ORD",
            "",
            regex=False,
        )
    )

    numbers = pd.to_numeric(
        numbers,
        errors="coerce",
    ).dropna()

    return int(numbers.max()) + 1 if len(numbers) else 0


def create_device(
    devices,
    first_seen,
    ip_prefix=None,
):

    idx = next_numeric_id(devices["device_id"])

    device_id = make_device_id(idx)

    if ip_prefix is None:
        ip_prefix = f"10." f"{rng.integers(0, 256)}." f"{rng.integers(0, 256)}.0/24"

    os_family = rng.choice(
        [
            "Android",
            "iOS",
            "Windows",
            "macOS",
            "Linux",
        ]
    )

    browser_map = {
        "Android": ["Chrome", "Firefox"],
        "iOS": ["Safari", "Chrome"],
        "Windows": ["Chrome", "Edge"],
        "macOS": ["Safari", "Chrome"],
        "Linux": ["Chrome", "Firefox"],
    }

    row = {
        "device_id": device_id,
        "os_family": os_family,
        "browser_family": rng.choice(browser_map[os_family]),
        "ip_prefix": ip_prefix,
        "first_seen_at": pd.Timestamp(first_seen),
    }

    devices = pd.concat(
        [
            devices,
            pd.DataFrame([row]),
        ],
        ignore_index=True,
    )

    return devices, device_id


def create_address(
    addresses,
    first_seen,
):

    idx = next_numeric_id(addresses["address_id"])

    address_id = make_address_id(idx)

    row = {
        "address_id": address_id,
        "canonical_address": (f"Hard Negative Address {idx}, India"),
        "city": rng.choice(
            [
                "Mumbai",
                "Delhi",
                "Bengaluru",
                "Chennai",
                "Pune",
            ]
        ),
        "pincode": str(
            rng.integers(
                100000,
                999999,
            )
        ),
        "is_drop_address": False,
        "first_seen_at": pd.Timestamp(first_seen),
    }

    addresses = pd.concat(
        [
            addresses,
            pd.DataFrame([row]),
        ],
        ignore_index=True,
    )

    return addresses, address_id


def create_phone(phones, first_seen):
    # Phone hashes are generated from sequential integer IDs.
    # Do not attempt to parse the hexadecimal hash.
    idx = len(phones)

    phone_hash = make_phone_hash(idx)

    row = {
        "phone_hash": phone_hash,
        "first_seen_at": pd.Timestamp(first_seen),
    }

    phones = pd.concat(
        [
            phones,
            pd.DataFrame([row]),
        ],
        ignore_index=True,
    )

    return phones, phone_hash


def create_instrument(
    instruments,
    first_seen,
):

    idx = next_numeric_id(instruments["instrument_id"])

    instrument_id = make_instrument_id(idx)

    row = {
        "instrument_id": instrument_id,
        "instrument_type": rng.choice(
            [
                "card",
                "upi",
                "wallet",
            ]
        ),
        "bin_or_vpa_hash": make_instrument_hash(idx),
        "first_seen_at": pd.Timestamp(first_seen),
    }

    instruments = pd.concat(
        [
            instruments,
            pd.DataFrame([row]),
        ],
        ignore_index=True,
    )

    return instruments, instrument_id


def make_order(
    order_id,
    account_id,
    device_id,
    address_id,
    phone_hash,
    instrument_id,
    timestamp,
    amount,
    category,
    return_flag=False,
    return_reason=None,
):

    delivery_timestamp = timestamp + pd.Timedelta(days=int(rng.integers(1, 4)))

    if return_flag:

        return_timestamp = delivery_timestamp + pd.Timedelta(
            days=int(rng.integers(2, 5))
        )

        refund_flag = True
        refund_amount = amount

        refund_timestamp = return_timestamp + pd.Timedelta(hours=6)

        return_lag_hours = (
            return_timestamp - delivery_timestamp
        ).total_seconds() / 3600

    else:

        return_timestamp = pd.NaT
        refund_flag = False
        refund_amount = None
        refund_timestamp = pd.NaT
        return_lag_hours = None
        return_reason = None

    return {
        "order_id": order_id,
        "account_id": account_id,
        "device_id": device_id,
        "address_id": address_id,
        "phone_hash": phone_hash,
        "instrument_id": instrument_id,
        "amount": float(amount),
        "discount_amount": 0.0,
        "coupon_code": None,
        "category": category,
        "order_timestamp": timestamp,
        "delivery_status": "delivered",
        "delivery_attempts": 1,
        "delivery_timestamp": delivery_timestamp,
        "rto_flag": False,
        "return_flag": return_flag,
        "return_reason_code": return_reason,
        "return_timestamp": return_timestamp,
        "return_lag_hours": return_lag_hours,
        "refund_flag": refund_flag,
        "refund_amount": refund_amount,
        "refund_timestamp": refund_timestamp,
        "dispute_flag": False,
        "dispute_phase": None,
        "dispute_reason_code": None,
        "dispute_reason_category": None,
        "evidence_availability": None,
    }


# ============================================================
# MAIN
# ============================================================


def run_hard_negatives():

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

    orders = pd.read_csv(
        PATHS["orders"],
        parse_dates=[
            "order_timestamp",
            "delivery_timestamp",
            "return_timestamp",
            "refund_timestamp",
        ],
    )

    hard_accounts = accounts[accounts["population_type"] == "hard_negative"][
        "account_id"
    ].tolist()

    # 4 family
    family_ids = hard_accounts[0:4]

    # 1 size sampler
    size_id = hard_accounts[4]

    # 5 office
    office_ids = hard_accounts[5:10]

    # 1 discount addict
    discount_id = hard_accounts[10]

    # 1 address change
    address_change_id = hard_accounts[11]

    # 5 hostel
    hostel_ids = hard_accounts[12:17]

    order_counter = next_order_id(orders)

    new_orders = []

    # ========================================================
    # FAMILY
    # ========================================================

    family_time = pd.Timestamp("2026-01-05")

    devices, family_device = create_device(
        devices,
        family_time,
    )

    addresses, family_address = create_address(
        addresses,
        family_time,
    )

    for idx, account_id in enumerate(family_ids):

        created = family_time + pd.Timedelta(days=idx)

        accounts.loc[
            accounts["account_id"] == account_id,
            "account_created_at",
        ] = created

        phones, phone = create_phone(
            phones,
            created,
        )

        instruments, instrument = create_instrument(
            instruments,
            created,
        )

        for j in range(3):

            timestamp = created + pd.Timedelta(days=j + 1)

            # ~3% overall, so rare.
            return_flag = rng.random() < 0.03

            new_orders.append(
                make_order(
                    make_order_id(order_counter),
                    account_id,
                    family_device,
                    family_address,
                    phone,
                    instrument,
                    timestamp,
                    float(
                        rng.integers(
                            1000,
                            5000,
                        )
                    ),
                    "fashion",
                    return_flag,
                    "size_fit",
                )
            )

            order_counter += 1

    # ========================================================
    # SIZE SAMPLER
    # ========================================================

    created = pd.Timestamp("2026-01-15")

    accounts.loc[
        accounts["account_id"] == size_id,
        "account_created_at",
    ] = created

    devices, device = create_device(
        devices,
        created,
    )

    addresses, address = create_address(
        addresses,
        created,
    )

    phones, phone = create_phone(
        phones,
        created,
    )

    instruments, instrument = create_instrument(
        instruments,
        created,
    )

    sizes = ["S", "M", "L"]

    for j, size in enumerate(sizes):

        return_flag = j in [0, 2]

        new_orders.append(
            make_order(
                make_order_id(order_counter),
                size_id,
                device,
                address,
                phone,
                instrument,
                created + pd.Timedelta(days=j + 1),
                float(
                    rng.integers(
                        1500,
                        4000,
                    )
                ),
                "fashion",
                return_flag,
                "size_fit",
            )
        )

        order_counter += 1

    # ========================================================
    # SMALL OFFICE
    # ========================================================

    office_time = pd.Timestamp("2026-01-20")

    addresses, office_address = create_address(
        addresses,
        office_time,
    )

    for idx, account_id in enumerate(office_ids):

        created = office_time + pd.Timedelta(days=idx)

        accounts.loc[
            accounts["account_id"] == account_id,
            "account_created_at",
        ] = created

        devices, device = create_device(
            devices,
            created,
        )

        phones, phone = create_phone(
            phones,
            created,
        )

        instruments, instrument = create_instrument(
            instruments,
            created,
        )

        for j in range(3):

            new_orders.append(
                make_order(
                    make_order_id(order_counter),
                    account_id,
                    device,
                    office_address,
                    phone,
                    instrument,
                    created + pd.Timedelta(days=j + 1),
                    float(
                        rng.integers(
                            500,
                            5000,
                        )
                    ),
                    rng.choice(
                        [
                            "grocery",
                            "home",
                            "electronics",
                        ]
                    ),
                    rng.random() < 0.04,
                    "not_as_described",
                )
            )

            order_counter += 1

    # ========================================================
    # DISCOUNT ADDICT
    # ========================================================

    created = pd.Timestamp("2026-01-25")

    accounts.loc[
        accounts["account_id"] == discount_id,
        "account_created_at",
    ] = created

    devices, device = create_device(
        devices,
        created,
    )

    addresses, address = create_address(
        addresses,
        created,
    )

    phones, phone = create_phone(
        phones,
        created,
    )

    instruments, instrument = create_instrument(
        instruments,
        created,
    )

    for j in range(8):

        timestamp = created + pd.Timedelta(days=j + 1)

        return_flag = rng.random() < 0.12

        row = make_order(
            make_order_id(order_counter),
            discount_id,
            device,
            address,
            phone,
            instrument,
            timestamp,
            float(
                rng.integers(
                    800,
                    3500,
                )
            ),
            rng.choice(
                [
                    "fashion",
                    "grocery",
                    "home",
                ]
            ),
            return_flag,
            "not_as_described",
        )

        row["coupon_code"] = f"COUPON_{100 + j}"

        row["discount_amount"] = round(
            row["amount"]
            * rng.uniform(
                0.10,
                0.20,
            ),
            2,
        )

        new_orders.append(row)

        order_counter += 1

    # ========================================================
    # ADDRESS CHANGE
    # ========================================================

    created = pd.Timestamp("2026-01-28")

    accounts.loc[
        accounts["account_id"] == address_change_id,
        "account_created_at",
    ] = created

    phones, phone = create_phone(
        phones,
        created,
    )

    instruments, instrument = create_instrument(
        instruments,
        created,
    )

    for j in range(3):

        event_time = created + pd.Timedelta(days=j * 10)

        devices, device = create_device(
            devices,
            event_time,
        )

        addresses, address = create_address(
            addresses,
            event_time,
        )

        new_orders.append(
            make_order(
                make_order_id(order_counter),
                address_change_id,
                device,
                address,
                phone,
                instrument,
                event_time,
                float(
                    rng.integers(
                        1000,
                        5000,
                    )
                ),
                rng.choice(
                    [
                        "home",
                        "grocery",
                        "electronics",
                    ]
                ),
                rng.random() < 0.04,
                "not_as_described",
            )
        )

        order_counter += 1

    # ========================================================
    # HOSTEL / SHARED NETWORK
    # ========================================================

    hostel_time = pd.Timestamp("2026-02-05")

    shared_ip = "10.88.88.0/24"

    addresses, hostel_address = create_address(
        addresses,
        hostel_time,
    )

    for idx, account_id in enumerate(hostel_ids):

        created = hostel_time + pd.Timedelta(days=idx)

        accounts.loc[
            accounts["account_id"] == account_id,
            "account_created_at",
        ] = created

        devices, device = create_device(
            devices,
            created,
            shared_ip,
        )

        phones, phone = create_phone(
            phones,
            created,
        )

        instruments, instrument = create_instrument(
            instruments,
            created,
        )

        for j in range(3):

            new_orders.append(
                make_order(
                    make_order_id(order_counter),
                    account_id,
                    device,
                    hostel_address,
                    phone,
                    instrument,
                    created + pd.Timedelta(days=j + 1),
                    float(
                        rng.integers(
                            500,
                            4500,
                        )
                    ),
                    rng.choice(
                        [
                            "grocery",
                            "fashion",
                            "home",
                        ]
                    ),
                    rng.random() < 0.04,
                    "not_as_described",
                )
            )

            order_counter += 1

    # ========================================================
    # SAVE
    # ========================================================

    hard_orders = pd.DataFrame(new_orders)

    updated_orders = pd.concat(
        [
            orders,
            hard_orders,
        ],
        ignore_index=True,
    )

    accounts.to_csv(
        PATHS["accounts"],
        index=False,
    )

    devices.to_csv(
        PATHS["devices"],
        index=False,
    )

    addresses.to_csv(
        PATHS["addresses"],
        index=False,
    )

    phones.to_csv(
        PATHS["phones"],
        index=False,
    )

    instruments.to_csv(
        PATHS["payment_instruments"],
        index=False,
    )

    updated_orders.to_csv(
        PATHS["orders"],
        index=False,
    )

    active_hard_ids = set(hard_orders["account_id"])

    print(f"Active hard-negative accounts: " f"{len(active_hard_ids)}")

    print(f"Hard-negative orders: " f"{len(hard_orders):,}")

    return (
        accounts,
        devices,
        addresses,
        phones,
        instruments,
        updated_orders,
    )


if __name__ == "__main__":
    run_hard_negatives()
