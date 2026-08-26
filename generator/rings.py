import numpy as np
import pandas as pd

from .config import (
    SEED, PATHS,
    N_RING_TYPES, RING_ACCOUNTS_PER_TYPE, N_RING_ACCOUNTS,
    RING_START_MIN, RING_START_MAX,
)
from .ids import (
    make_order_id, make_device_id, make_address_id,
    make_phone_hash, make_instrument_id, make_instrument_hash,
)

rng = np.random.default_rng(SEED)


def next_numeric_id(series):
    if len(series) == 0:
        return 0
    values = series.astype(str).str.extract(r"(\d+)$")[0]
    values = pd.to_numeric(values, errors="coerce").dropna()
    if len(values) == 0:
        return 0
    return int(values.max()) + 1


def get_next_order_counter(orders):
    if len(orders) == 0:
        return 0
    numbers = orders["order_id"].astype(str).str.replace("ORD", "", regex=False)
    numbers = pd.to_numeric(numbers, errors="coerce").dropna()
    if len(numbers) == 0:
        return 0
    return int(numbers.max()) + 1


def load_data():
    accounts = pd.read_csv(PATHS["accounts"], parse_dates=["account_created_at"])
    devices = pd.read_csv(PATHS["devices"], parse_dates=["first_seen_at"])
    addresses = pd.read_csv(PATHS["addresses"], parse_dates=["first_seen_at"])
    phones = pd.read_csv(PATHS["phones"], parse_dates=["first_seen_at"])
    instruments = pd.read_csv(PATHS["payment_instruments"], parse_dates=["first_seen_at"])
    orders = pd.read_csv(PATHS["orders"], parse_dates=[
        "order_timestamp", "delivery_timestamp", "return_timestamp", "refund_timestamp",
    ])
    return accounts, devices, addresses, phones, instruments, orders


def create_device(devices, first_seen_at, ip_prefix=None):
    index = next_numeric_id(devices["device_id"])
    device_id = make_device_id(index)
    if ip_prefix is None:
        ip_prefix = f"10.{rng.integers(0, 256)}.{rng.integers(0, 256)}.0/24"
    os_family = rng.choice(
        ["Android", "iOS", "Windows", "macOS", "Linux"],
        p=[0.48, 0.25, 0.15, 0.10, 0.02],
    )
    browser_map = {
        "Android": ["Chrome", "Firefox", "Edge"],
        "iOS": ["Safari", "Chrome"],
        "Windows": ["Chrome", "Edge", "Firefox"],
        "macOS": ["Safari", "Chrome", "Firefox"],
        "Linux": ["Chrome", "Firefox"],
    }
    row = {
        "device_id": device_id,
        "os_family": os_family,
        "browser_family": rng.choice(browser_map[os_family]),
        "ip_prefix": ip_prefix,
        "first_seen_at": pd.Timestamp(first_seen_at),
    }
    devices = pd.concat([devices, pd.DataFrame([row])], ignore_index=True)
    return devices, device_id


def create_address(addresses, first_seen_at, is_drop_address=False):
    index = next_numeric_id(addresses["address_id"])
    address_id = make_address_id(index)
    row = {
        "address_id": address_id,
        "canonical_address": f"ring address {index}",
        "city": rng.choice(["Mumbai","Delhi","Bengaluru","Chennai","Hyderabad","Pune","Ahmedabad","Kolkata"]),
        "pincode": str(rng.integers(100000, 999999)),
        "is_drop_address": bool(is_drop_address),
        "first_seen_at": pd.Timestamp(first_seen_at),
    }
    addresses = pd.concat([addresses, pd.DataFrame([row])], ignore_index=True)
    return addresses, address_id


def create_phone(phones, first_seen):
    idx = len(phones)
    phone_hash = make_phone_hash(idx)
    row = {"phone_hash": phone_hash, "first_seen_at": pd.Timestamp(first_seen)}
    phones = pd.concat([phones, pd.DataFrame([row])], ignore_index=True)
    return phones, phone_hash


def create_instrument(instruments, first_seen_at, instrument_type="card"):
    index = next_numeric_id(instruments["instrument_id"])
    instrument_id = make_instrument_id(index)
    row = {
        "instrument_id": instrument_id,
        "instrument_type": instrument_type,
        "bin_or_vpa_hash": make_instrument_hash(index),
        "first_seen_at": pd.Timestamp(first_seen_at),
    }
    instruments = pd.concat([instruments, pd.DataFrame([row])], ignore_index=True)
    return instruments, instrument_id


def build_order(
    order_id, account_id, device_id, address_id, phone_hash, instrument_id,
    order_timestamp, amount, discount_amount, coupon_code, category, delivery_timestamp,
    return_flag=False, return_reason_code=None, return_timestamp=pd.NaT,
    refund_flag=False, refund_amount=None, refund_timestamp=pd.NaT,
    dispute_flag=False, dispute_phase=None, dispute_reason_code=None, dispute_reason_category=None,
):
    if pd.notna(delivery_timestamp):
        delivery_status = "delivered"
    else:
        delivery_status = "pending"

    return {
        "order_id": order_id,
        "account_id": account_id,
        "device_id": device_id,
        "address_id": address_id,
        "phone_hash": phone_hash,
        "instrument_id": instrument_id,
        "amount": float(amount),
        "discount_amount": float(discount_amount),
        "coupon_code": coupon_code,
        "category": category,
        "order_timestamp": pd.Timestamp(order_timestamp),
        "delivery_status": delivery_status,
        "delivery_attempts": 1,
        "delivery_timestamp": pd.Timestamp(delivery_timestamp) if pd.notna(delivery_timestamp) else pd.NaT,
        "rto_flag": False,
        "return_flag": bool(return_flag),
        "return_reason_code": return_reason_code,
        "return_timestamp": pd.Timestamp(return_timestamp) if pd.notna(return_timestamp) else pd.NaT,
        "return_lag_hours": (
            (pd.Timestamp(return_timestamp) - pd.Timestamp(delivery_timestamp)).total_seconds() / 3600
            if return_flag else None
        ),
        "refund_flag": bool(refund_flag),
        "refund_amount": float(refund_amount) if refund_amount is not None else None,
        "refund_timestamp": pd.Timestamp(refund_timestamp) if pd.notna(refund_timestamp) else pd.NaT,
        "dispute_flag": bool(dispute_flag),
        "dispute_phase": dispute_phase,
        "dispute_reason_code": dispute_reason_code,
        "dispute_reason_category": dispute_reason_category,
        "evidence_availability": None,
    }


def inject_wardrobing(
    accounts, devices, addresses, phones, instruments,
    account_ids, order_counter, ring_id="R001", ring_start=pd.Timestamp("2026-01-10"),
):
    devices, shared_device = create_device(devices, ring_start - pd.Timedelta(days=1))
    orders = []
    members = []

    for idx, account_id in enumerate(account_ids):
        account_created = ring_start + pd.Timedelta(hours=idx * 2)
        accounts.loc[accounts["account_id"] == account_id, "account_created_at"] = account_created

        addresses, address_id = create_address(addresses, account_created - pd.Timedelta(hours=1))
        phones, phone_hash = create_phone(phones, account_created - pd.Timedelta(hours=1))
        instruments, instrument_id = create_instrument(
            instruments, account_created - pd.Timedelta(hours=1), "card"
        )

        return_rates = [0.30, 0.90, 0.90, 0.50]

        for order_num, return_rate in enumerate(return_rates):
            order_time = (
                account_created
                + pd.Timedelta(days=order_num * 2)
                + pd.Timedelta(hours=int(rng.integers(1, 12)))
            )
            delivery_time = order_time + pd.Timedelta(days=2)
            amount = float(rng.integers(4000, 9000))
            return_flag = rng.random() < return_rate

            if return_flag:
                return_reason = rng.choice(["size_fit", "not_as_described"])
                return_time = delivery_time + pd.Timedelta(days=int(rng.integers(2, 6)))
                refund_flag = True
                refund_amount = amount
                refund_time = return_time + pd.Timedelta(hours=int(rng.integers(4, 24)))
            else:
                return_reason = None
                return_time = pd.NaT
                refund_flag = False
                refund_amount = None
                refund_time = pd.NaT

            order_id = make_order_id(order_counter)
            order_counter += 1

            orders.append(
                build_order(
                    order_id, account_id, shared_device, address_id, phone_hash, instrument_id,
                    order_time, amount, 0, None, "fashion", delivery_time,
                    return_flag, return_reason, return_time,
                    refund_flag, refund_amount, refund_time,
                )
            )

        members.append({
            "account_id": account_id,
            "abuse_ring_id": ring_id,
            "ring_type": "wardrobing",
            "ring_start_time": account_created,
            "ring_end_time": account_created + pd.Timedelta(days=12),
        })

    return accounts, devices, addresses, phones, instruments, pd.DataFrame(orders), members, order_counter


def inject_promo_farming(
    accounts, devices, addresses, phones, instruments,
    account_ids, order_counter, ring_id="R002", ring_start=pd.Timestamp("2026-01-20 09:00:00"),
):
    shared_ip = "10.77.77.0/24"
    shared_coupon = "RING_RARE_777"
    instruments, shared_instrument = create_instrument(
        instruments, ring_start - pd.Timedelta(hours=2), "upi"
    )
    orders = []
    members = []

    for idx, account_id in enumerate(account_ids):
        account_created = ring_start + pd.Timedelta(minutes=idx * 15)
        accounts.loc[accounts["account_id"] == account_id, "account_created_at"] = account_created

        devices, device_id = create_device(
            devices, account_created - pd.Timedelta(hours=1), shared_ip
        )
        addresses, address_id = create_address(addresses, account_created - pd.Timedelta(hours=1))
        phones, phone_hash = create_phone(phones, account_created - pd.Timedelta(hours=1))

        n_orders = int(rng.integers(2, 4))

        for order_num in range(n_orders):
            order_time = (
                account_created
                + pd.Timedelta(hours=order_num * 2)
                + pd.Timedelta(minutes=int(rng.integers(0, 30)))
            )
            delivery_time = order_time + pd.Timedelta(days=1)
            category = rng.choice(["grocery", "home", "fashion"])
            amount = float(rng.integers(500, 2000))
            discount_amount = round(amount * rng.uniform(0.25, 0.35), 2)
            return_flag = rng.random() < 0.65

            if return_flag:
                return_time = delivery_time + pd.Timedelta(days=int(rng.integers(1, 3)))
                refund_flag = True
                refund_amount = amount
                refund_time = return_time + pd.Timedelta(hours=6)
                return_reason = "not_as_described"
            else:
                return_time = pd.NaT
                refund_flag = False
                refund_amount = None
                refund_time = pd.NaT
                return_reason = None

            if idx < 5 and order_num == 0:
                coupon_code = shared_coupon
            else:
                coupon_code = f"PROMO_{rng.integers(1000, 9999)}"

            order_id = make_order_id(order_counter)
            order_counter += 1

            orders.append(
                build_order(
                    order_id, account_id, device_id, address_id, phone_hash, shared_instrument,
                    order_time, amount, discount_amount, coupon_code, category, delivery_time,
                    return_flag, return_reason, return_time,
                    refund_flag, refund_amount, refund_time,
                )
            )

        members.append({
            "account_id": account_id,
            "abuse_ring_id": ring_id,
            "ring_type": "promo_refund_farming",
            "ring_start_time": account_created,
            "ring_end_time": account_created + pd.Timedelta(days=6),
        })

    return accounts, devices, addresses, phones, instruments, pd.DataFrame(orders), members, order_counter


def inject_friendly_fraud(
    accounts, devices, addresses, phones, instruments,
    account_ids, order_counter, ring_id="R003", ring_start=pd.Timestamp("2026-02-01"),
):
    addresses, shared_address = create_address(
        addresses, ring_start - pd.Timedelta(days=1), is_drop_address=True
    )
    phones, shared_phone = create_phone(phones, ring_start - pd.Timedelta(days=1))
    orders = []
    members = []

    for idx, account_id in enumerate(account_ids):
        account_created = ring_start + pd.Timedelta(hours=idx * 4)
        accounts.loc[accounts["account_id"] == account_id, "account_created_at"] = account_created

        devices, device_id = create_device(devices, account_created - pd.Timedelta(hours=1))
        instruments, instrument_id = create_instrument(
            instruments, account_created - pd.Timedelta(hours=1), "card"
        )

        for order_num in range(2):
            order_time = (
                account_created
                + pd.Timedelta(days=order_num * 3)
                + pd.Timedelta(hours=int(rng.integers(1, 12)))
            )
            delivery_time = order_time + pd.Timedelta(days=2)
            amount = float(rng.integers(3000, 7000))

            order_id = make_order_id(order_counter)
            order_counter += 1

            orders.append(
                build_order(
                    order_id, account_id, device_id, shared_address, shared_phone,
                    instrument_id, order_time, amount, 0, None, "electronics", delivery_time,
                    False, None, pd.NaT, False, None, pd.NaT,
                    True, "retrieval", "item_not_received", "friendly_fraud",
                )
            )

        members.append({
            "account_id": account_id,
            "abuse_ring_id": ring_id,
            "ring_type": "friendly_fraud",
            "ring_start_time": account_created,
            "ring_end_time": account_created + pd.Timedelta(days=8),
        })

    return accounts, devices, addresses, phones, instruments, pd.DataFrame(orders), members, order_counter


def inject_subtle_distributed(
    accounts, devices, addresses, phones, instruments,
    account_ids, order_counter, ring_id="R004", ring_start=pd.Timestamp("2026-02-10"),
):
    shared_coupon = "RING_RARE_555"
    orders = []
    members = []

    for idx, account_id in enumerate(account_ids):
        account_created = ring_start + pd.Timedelta(hours=idx * 6)
        accounts.loc[accounts["account_id"] == account_id, "account_created_at"] = account_created

        devices, device_id = create_device(devices, account_created - pd.Timedelta(hours=1))
        addresses, address_id = create_address(addresses, account_created - pd.Timedelta(hours=1))
        phones, phone_hash = create_phone(phones, account_created - pd.Timedelta(hours=1))
        instruments, instrument_id = create_instrument(
            instruments, account_created - pd.Timedelta(hours=1), "upi"
        )

        for order_num in range(3):
            base_date = account_created.normalize() + pd.Timedelta(days=order_num + 1)
            order_time = base_date.replace(
                hour=10, minute=int(rng.integers(0, 15)), second=0, microsecond=0
            )
            jitter_minutes = int(rng.integers(0, 45))
            jitter_seconds = int(rng.integers(0, 60))
            order_time += pd.Timedelta(minutes=jitter_minutes, seconds=jitter_seconds)

            if order_time <= account_created:
                order_time = account_created + pd.Timedelta(minutes=int(rng.integers(5, 60)))

            delivery_time = order_time + pd.Timedelta(days=2)
            amount = float(rng.integers(1500, 4500))
            discount_amount = round(amount * rng.uniform(0.20, 0.30), 2)
            return_flag = rng.random() < 0.50

            if return_flag:
                return_time = delivery_time + pd.Timedelta(days=int(rng.integers(2, 4)))
                refund_flag = True
                refund_amount = amount
                refund_time = return_time + pd.Timedelta(hours=4)
                return_reason = rng.choice(["not_as_described", "size_fit"])
            else:
                return_time = pd.NaT
                refund_flag = False
                refund_amount = None
                refund_time = pd.NaT
                return_reason = None

            if idx < 5 and order_num == 0:
                coupon_code = shared_coupon
            else:
                coupon_code = None

            order_id = make_order_id(order_counter)
            order_counter += 1

            orders.append(
                build_order(
                    order_id, account_id, device_id, address_id, phone_hash, instrument_id,
                    order_time, amount, discount_amount, coupon_code,
                    rng.choice(["fashion", "home", "toys"]), delivery_time,
                    return_flag, return_reason, return_time,
                    refund_flag, refund_amount, refund_time,
                )
            )

        members.append({
            "account_id": account_id,
            "abuse_ring_id": ring_id,
            "ring_type": "subtle_distributed",
            "ring_start_time": account_created,
            "ring_end_time": account_created + pd.Timedelta(days=8),
        })

    return accounts, devices, addresses, phones, instruments, pd.DataFrame(orders), members, order_counter


def run_ring_injection():
    accounts, devices, addresses, phones, instruments, orders = load_data()
    ring_accounts = accounts[accounts["population_type"] == "ring"].copy()
    ring_ids = ring_accounts["account_id"].tolist()

    if len(ring_accounts) != N_RING_ACCOUNTS:
        raise AssertionError(
            f"Expected {N_RING_ACCOUNTS} ring-reserved accounts, "
            f"found {len(ring_accounts)}."
        )

    if len(ring_ids) != len(set(ring_ids)):
        raise AssertionError("Ring account IDs are not unique.")

    order_counter = get_next_order_counter(orders)
    all_orders = []
    all_members = []

    idx = 0
    ring_count = 0

    start_min = pd.Timestamp(RING_START_MIN)
    start_max = pd.Timestamp(RING_START_MAX)
    total_days = (start_max - start_min).days

    for ring_type, count in N_RING_TYPES.items():
        size = RING_ACCOUNTS_PER_TYPE[ring_type]
        for ring_num in range(count):
            days_offset = rng.integers(0, total_days + 1)
            start_time = start_min + pd.Timedelta(days=int(days_offset))
            ids = ring_ids[idx:idx + size]
            idx += size
            ring_id_str = f"R{ring_count + 1:03d}"

            if ring_type == "wardrobing":
                result = inject_wardrobing(
                    accounts, devices, addresses, phones, instruments,
                    ids, order_counter, ring_id=ring_id_str, ring_start=start_time,
                )
            elif ring_type == "promo_refund_farming":
                result = inject_promo_farming(
                    accounts, devices, addresses, phones, instruments,
                    ids, order_counter, ring_id=ring_id_str, ring_start=start_time,
                )
            elif ring_type == "friendly_fraud":
                result = inject_friendly_fraud(
                    accounts, devices, addresses, phones, instruments,
                    ids, order_counter, ring_id=ring_id_str, ring_start=start_time,
                )
            elif ring_type == "subtle_distributed":
                result = inject_subtle_distributed(
                    accounts, devices, addresses, phones, instruments,
                    ids, order_counter, ring_id=ring_id_str, ring_start=start_time,
                )
            else:
                continue

            accounts, devices, addresses, phones, instruments, ring_orders, members, order_counter = result
            all_orders.append(ring_orders)
            all_members.extend(members)
            ring_count += 1

            print(f"{ring_type} ring {ring_num + 1}/{count}: {len(members)} accounts, {len(ring_orders)} orders")

    # Allocation assertions
    if idx != N_RING_ACCOUNTS:
        raise AssertionError(f"Ring account allocation mismatch: consumed {idx}, expected {N_RING_ACCOUNTS}.")
    if ring_count != sum(N_RING_TYPES.values()):
        raise AssertionError(f"Ring count mismatch: created {ring_count}, expected {sum(N_RING_TYPES.values())}.")
    if len(all_members) != N_RING_ACCOUNTS:
        raise AssertionError(f"Ring member mismatch: created {len(all_members)}, expected {N_RING_ACCOUNTS}.")

    ring_orders_df = pd.concat(all_orders, ignore_index=True)
    updated_orders = pd.concat([orders, ring_orders_df], ignore_index=True)

    accounts.to_csv(PATHS["accounts"], index=False)
    devices.to_csv(PATHS["devices"], index=False)
    addresses.to_csv(PATHS["addresses"], index=False)
    phones.to_csv(PATHS["phones"], index=False)
    instruments.to_csv(PATHS["payment_instruments"], index=False)
    updated_orders.to_csv(PATHS["orders"], index=False)

    print(f"\nTotal ring orders: {len(ring_orders_df):,}")
    print(f"Total orders after rings: {len(updated_orders):,}")

    return accounts, devices, addresses, phones, instruments, updated_orders, all_members