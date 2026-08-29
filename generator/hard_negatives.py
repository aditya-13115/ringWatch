import numpy as np
import pandas as pd

from .config import PATHS, SEED, N_HARD_NEGATIVE_ACCOUNTS
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
    accounts = pd.read_csv(PATHS["accounts"], parse_dates=["account_created_at"])
    devices = pd.read_csv(PATHS["devices"], parse_dates=["first_seen_at"])
    addresses = pd.read_csv(PATHS["addresses"], parse_dates=["first_seen_at"])
    phones = pd.read_csv(PATHS["phones"], parse_dates=["first_seen_at"])
    instruments = pd.read_csv(
        PATHS["payment_instruments"], parse_dates=["first_seen_at"]
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

    hard_account_ids = accounts[accounts["population_type"] == "hard_negative"][
        "account_id"
    ].tolist()
    n_total = len(hard_account_ids)

    if n_total != N_HARD_NEGATIVE_ACCOUNTS:
        raise AssertionError(
            f"Expected {N_HARD_NEGATIVE_ACCOUNTS} hard-negative accounts, "
            f"found {n_total}."
        )

    # Budgets
    family_accounts = int(n_total * 0.20)
    size_sampler_accounts = int(n_total * 0.20)
    office_accounts = int(n_total * 0.20)
    discount_accounts = int(n_total * 0.20)
    address_change_accounts = int(n_total * 0.10)
    hostel_accounts = (
        n_total
        - family_accounts
        - size_sampler_accounts
        - office_accounts
        - discount_accounts
        - address_change_accounts
    )

    family_groups = family_accounts // 4
    office_groups = office_accounts // 5
    hostel_groups = hostel_accounts // 5

    cursor = 0
    order_counter = next_order_id(orders)
    new_orders = []

    # FAMILY
    for _ in range(family_groups):
        ids = hard_account_ids[cursor : cursor + 4]
        cursor += 4
        if len(ids) < 4:
            break
        base_time = pd.Timestamp("2026-01-05")
        devices, shared_device = create_device(devices, base_time)
        addresses, shared_address = create_address(addresses, base_time)
        for idx, acc in enumerate(ids):
            created = base_time + pd.Timedelta(days=idx)
            accounts.loc[accounts["account_id"] == acc, "account_created_at"] = created
            phones, phone = create_phone(phones, created)
            instruments, inst = create_instrument(instruments, created)
            for j in range(3):
                ts = created + pd.Timedelta(days=j + 1)
                new_orders.append(
                    make_order(
                        make_order_id(order_counter),
                        acc,
                        shared_device,
                        shared_address,
                        phone,
                        inst,
                        ts,
                        float(rng.integers(1000, 5000)),
                        "fashion",
                        rng.random() < 0.03,
                        "size_fit",
                    )
                )
                order_counter += 1

    # SIZE SAMPLER
    for _ in range(size_sampler_accounts):
        acc = hard_account_ids[cursor]
        cursor += 1
        created = pd.Timestamp("2026-01-15")
        accounts.loc[accounts["account_id"] == acc, "account_created_at"] = created
        devices, device = create_device(devices, created)
        addresses, address = create_address(addresses, created)
        phones, phone = create_phone(phones, created)
        instruments, inst = create_instrument(instruments, created)
        for j in range(3):
            return_flag = j in [0, 2]
            new_orders.append(
                make_order(
                    make_order_id(order_counter),
                    acc,
                    device,
                    address,
                    phone,
                    inst,
                    created + pd.Timedelta(days=j + 1),
                    float(rng.integers(1500, 4000)),
                    "fashion",
                    return_flag,
                    "size_fit",
                )
            )
            order_counter += 1

    # OFFICE
    for _ in range(office_groups):
        ids = hard_account_ids[cursor : cursor + 5]
        cursor += 5
        if len(ids) < 5:
            break
        office_time = pd.Timestamp("2026-01-20")
        addresses, shared_address = create_address(addresses, office_time)
        for idx, acc in enumerate(ids):
            created = office_time + pd.Timedelta(days=idx)
            accounts.loc[accounts["account_id"] == acc, "account_created_at"] = created
            devices, device = create_device(devices, created)
            phones, phone = create_phone(phones, created)
            instruments, inst = create_instrument(instruments, created)
            for j in range(3):
                new_orders.append(
                    make_order(
                        make_order_id(order_counter),
                        acc,
                        device,
                        shared_address,
                        phone,
                        inst,
                        created + pd.Timedelta(days=j + 1),
                        float(rng.integers(500, 5000)),
                        rng.choice(["grocery", "home", "electronics"]),
                        rng.random() < 0.04,
                        "not_as_described",
                    )
                )
                order_counter += 1

    # DISCOUNT ADDICT
    for _ in range(discount_accounts):
        acc = hard_account_ids[cursor]
        cursor += 1
        created = pd.Timestamp("2026-01-25")
        accounts.loc[accounts["account_id"] == acc, "account_created_at"] = created
        devices, device = create_device(devices, created)
        addresses, address = create_address(addresses, created)
        phones, phone = create_phone(phones, created)
        instruments, inst = create_instrument(instruments, created)
        for j in range(8):
            ts = created + pd.Timedelta(days=j + 1)
            row = make_order(
                make_order_id(order_counter),
                acc,
                device,
                address,
                phone,
                inst,
                ts,
                float(rng.integers(800, 3500)),
                rng.choice(["fashion", "grocery", "home"]),
                rng.random() < 0.12,
                "not_as_described",
            )
            row["coupon_code"] = f"COUPON_{100 + j}"
            row["discount_amount"] = round(row["amount"] * rng.uniform(0.10, 0.20), 2)
            new_orders.append(row)
            order_counter += 1

    # ADDRESS CHANGE
    for _ in range(address_change_accounts):
        acc = hard_account_ids[cursor]
        cursor += 1
        created = pd.Timestamp("2026-01-28")
        accounts.loc[accounts["account_id"] == acc, "account_created_at"] = created
        phones, phone = create_phone(phones, created)
        instruments, inst = create_instrument(instruments, created)
        for j in range(3):
            event_time = created + pd.Timedelta(days=j * 10)
            devices, device = create_device(devices, event_time)
            addresses, address = create_address(addresses, event_time)
            new_orders.append(
                make_order(
                    make_order_id(order_counter),
                    acc,
                    device,
                    address,
                    phone,
                    inst,
                    event_time,
                    float(rng.integers(1000, 5000)),
                    rng.choice(["home", "grocery", "electronics"]),
                    rng.random() < 0.04,
                    "not_as_described",
                )
            )
            order_counter += 1

    # HOSTEL
    for _ in range(hostel_groups):
        ids = hard_account_ids[cursor : cursor + 5]
        cursor += 5
        if len(ids) < 5:
            break
        hostel_time = pd.Timestamp("2026-02-05")
        shared_ip = "10.88.88.0/24"
        addresses, shared_address = create_address(addresses, hostel_time)
        for idx, acc in enumerate(ids):
            created = hostel_time + pd.Timedelta(days=idx)
            accounts.loc[accounts["account_id"] == acc, "account_created_at"] = created
            devices, device = create_device(devices, created, shared_ip)
            phones, phone = create_phone(phones, created)
            instruments, inst = create_instrument(instruments, created)
            for j in range(3):
                new_orders.append(
                    make_order(
                        make_order_id(order_counter),
                        acc,
                        device,
                        shared_address,
                        phone,
                        inst,
                        created + pd.Timedelta(days=j + 1),
                        float(rng.integers(500, 4500)),
                        rng.choice(["grocery", "fashion", "home"]),
                        rng.random() < 0.04,
                        "not_as_described",
                    )
                )
                order_counter += 1

    hard_orders = pd.DataFrame(new_orders)
    active_hard_ids = set(hard_orders["account_id"])

    # Assertions BEFORE saving
    if cursor != n_total:
        raise AssertionError(
            f"Hard-negative allocation mismatch: consumed {cursor}, expected {n_total}."
        )
    if len(active_hard_ids) != n_total:
        raise AssertionError(
            f"Active hard-negative accounts mismatch: {len(active_hard_ids)} vs {n_total}."
        )

    updated_orders = pd.concat([orders, hard_orders], ignore_index=True)

    accounts.to_csv(PATHS["accounts"], index=False)
    devices.to_csv(PATHS["devices"], index=False)
    addresses.to_csv(PATHS["addresses"], index=False)
    phones.to_csv(PATHS["phones"], index=False)
    instruments.to_csv(PATHS["payment_instruments"], index=False)
    updated_orders.to_csv(PATHS["orders"], index=False)

    print(f"Active hard-negative accounts: {len(active_hard_ids)}")
    print(f"Hard-negative orders: {len(hard_orders):,}")

    return accounts, devices, addresses, phones, instruments, updated_orders


if __name__ == "__main__":
    run_hard_negatives()
