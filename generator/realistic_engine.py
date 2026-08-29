"""Cohesive RingWatch V4 synthetic data engine.

The engine keeps the existing RingWatch CSV schemas and exact population counts,
but generates all populations from one latent behavioural process. Abuse and
hard-negative labels are applied after the benign population is sampled.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import hashlib
import math
import os

import numpy as np
import pandas as pd
from faker import Faker

from .config import (
    DATA_DIR,
    END_DATE,
    N_ACCOUNTS,
    N_NORMAL_ACCOUNTS,
    N_RING_ACCOUNTS,
    N_HARD_NEGATIVE_ACCOUNTS,
    N_RING_TYPES,
    RING_ACCOUNTS_PER_TYPE,
    START_DATE,
    PATHS,
)
from .ids import (
    make_account_id,
    make_device_id,
    make_address_id,
    make_phone_hash,
    make_instrument_id,
    make_instrument_hash,
    make_order_id,
    make_refund_id,
    make_dispute_id,
)
from .address_utils import normalize_address

SEED = int(os.getenv("RINGWATCH_SEED", "42"))
rng = np.random.default_rng(SEED)
fake = Faker("en_IN")
fake.seed_instance(SEED)
START = pd.Timestamp(START_DATE)
END = pd.Timestamp(END_DATE)
CUTOFF = pd.Timestamp("2026-02-20 00:00:00")

LOCATIONS = [
    ("Mumbai", "Maharashtra", ["400", "401"]),
    ("Delhi", "Delhi", ["110"]),
    ("Bengaluru", "Karnataka", ["560"]),
    ("Chennai", "Tamil Nadu", ["600"]),
    ("Hyderabad", "Telangana", ["500"]),
    ("Pune", "Maharashtra", ["411"]),
    ("Ahmedabad", "Gujarat", ["380"]),
    ("Kolkata", "West Bengal", ["700"]),
    ("Jaipur", "Rajasthan", ["302"]),
    ("Lucknow", "Uttar Pradesh", ["226"]),
    ("Surat", "Gujarat", ["395"]),
]

PERSONAS = [
    ("casual", 0.72, 0.08, 0.12, 0.003, 0.10, 0.10),
    ("frequent", 1.45, 0.13, 0.18, 0.006, 0.18, 0.12),
    ("bargain", 1.12, 0.18, 0.52, 0.005, 0.24, 0.20),
    ("fashion", 1.08, 0.29, 0.24, 0.008, 0.13, 0.10),
    ("electronics", 0.82, 0.10, 0.11, 0.004, 0.08, 0.08),
    ("family", 1.32, 0.17, 0.27, 0.005, 0.68, 0.18),
    ("student", 1.25, 0.21, 0.46, 0.008, 0.52, 0.26),
    ("traveler", 0.92, 0.14, 0.16, 0.012, 0.27, 0.12),
    ("office", 1.02, 0.11, 0.20, 0.004, 0.75, 0.16),
    ("collector", 1.58, 0.15, 0.22, 0.006, 0.16, 0.09),
]
PERSONA_W = np.array([0.18, 0.10, 0.11, 0.10, 0.08, 0.14, 0.10, 0.06, 0.07, 0.06])
PERSONA_W /= PERSONA_W.sum()

CATEGORIES = ["electronics", "fashion", "grocery", "home", "books", "toys"]
CAT_W = np.array([0.15, 0.30, 0.20, 0.15, 0.10, 0.10])
CAT_RANGES = {
    "electronics": (1200, 24000),
    "fashion": (500, 9000),
    "grocery": (150, 4500),
    "home": (700, 12000),
    "books": (150, 2500),
    "toys": (300, 6000),
}


def sha16(prefix: str, value: object) -> str:
    return hashlib.sha256(f"{prefix}:{value}".encode()).hexdigest()[:16]


def poisson_count(rate: float) -> int:
    return int(min(20, rng.poisson(max(0.25, rate))))


def latent_accounts():
    n = N_ACCOUNTS
    persona_idx = rng.choice(len(PERSONAS), n, p=PERSONA_W)
    # Correlated latent factors make behavioural dimensions co-vary naturally.
    z = rng.normal(size=(n, 5))
    corr = np.array(
        [
            [1, 0.28, 0.18, 0.05, 0.20],
            [0.28, 1, 0.22, 0.08, 0.12],
            [0.18, 0.22, 1, 0.15, 0.18],
            [0.05, 0.08, 0.15, 1, 0.12],
            [0.20, 0.12, 0.18, 0.12, 1],
        ]
    )
    z = z @ np.linalg.cholesky(corr).T

    population = np.array(
        ["normal"] * N_NORMAL_ACCOUNTS
        + ["ring"] * N_RING_ACCOUNTS
        + ["hard_negative"] * N_HARD_NEGATIVE_ACCOUNTS,
        dtype=object,
    )
    rng.shuffle(population)

    rows = []
    for i in range(n):
        p = PERSONAS[persona_idx[i]]
        name, rate, ret, disc, disp, share, value = p
        day = int(rng.triangular(0, 22, 52))
        hour_probs = np.array(
            [
                0.03,
                0.04,
                0.05,
                0.06,
                0.08,
                0.10,
                0.11,
                0.11,
                0.10,
                0.08,
                0.07,
                0.06,
                0.05,
                0.04,
                0.03,
                0.02,
                0.01,
            ]
        )
        hour_probs = hour_probs / hour_probs.sum()
        hour = int(rng.choice(np.arange(7, 24), p=hour_probs))
        created = START + pd.Timedelta(
            days=day, hours=hour, minutes=int(rng.integers(0, 60))
        )
        rows.append(
            {
                "account_id": make_account_id(i),
                "account_created_at": created,
                "customer_type": rng.choice(
                    ["regular", "new", "guest"], p=[0.72, 0.23, 0.05]
                ),
                "population_type": population[i],
                # Internal-only columns. They are removed before any downstream feature table is built.
                "_persona": name,
                "_activity_rate": float(rate * math.exp(0.28 * z[i, 0])),
                "_return_p": float(np.clip(ret + 0.08 * np.tanh(z[i, 1]), 0.015, 0.82)),
                "_discount_p": float(
                    np.clip(disc + 0.16 * np.tanh(z[i, 2]), 0.02, 0.90)
                ),
                "_dispute_p": float(
                    np.clip(disp * math.exp(0.55 * z[i, 3]), 0.001, 0.08)
                ),
                "_share_p": float(np.clip(share + 0.18 * np.tanh(z[i, 4]), 0.02, 0.92)),
                "_value": float(value + 0.35 * z[i, 0]),
            }
        )
    return pd.DataFrame(rows)


def make_entities(accounts):
    n = len(accounts)
    # Resource pools intentionally overlap; real households/workplaces create reuse.
    n_devices = int(n * 0.82)
    n_addresses = int(n * 0.66)
    n_phones = int(n * 0.84)
    n_instruments = int(n * 1.02)

    devices = []
    browser = {
        "Android": ["Chrome", "Firefox", "Edge"],
        "iOS": ["Safari", "Chrome"],
        "Windows": ["Chrome", "Edge", "Firefox"],
        "macOS": ["Safari", "Chrome", "Firefox"],
        "Linux": ["Chrome", "Firefox"],
    }
    for i in range(n_devices):
        osf = rng.choice(
            ["Android", "iOS", "Windows", "macOS", "Linux"],
            p=[0.50, 0.24, 0.14, 0.10, 0.02],
        )
        devices.append(
            {
                "device_id": make_device_id(i),
                "os_family": osf,
                "browser_family": rng.choice(browser[osf]),
                "ip_prefix": f"10.{rng.integers(1,255)}.{rng.integers(1,255)}.0/24",
                "first_seen_at": START
                + pd.Timedelta(
                    days=int(rng.integers(0, 45)), hours=int(rng.integers(0, 24))
                ),
            }
        )

    addresses = []
    for i in range(n_addresses):
        city, state, prefixes = LOCATIONS[int(rng.integers(len(LOCATIONS)))]
        pin = rng.choice(prefixes) + f"{rng.integers(1000):03d}"
        raw = f"{fake.building_number()}, {fake.street_name()}, {rng.choice(['Sector','Nagar','Layout','Colony'])} {rng.integers(1,120)}, {city}, {state} {pin}"
        addresses.append(
            {
                "address_id": make_address_id(i),
                "canonical_address": normalize_address(raw),
                "city": city,
                "pincode": pin,
                "is_drop_address": bool(rng.random() < 0.025),
                "first_seen_at": START
                + pd.Timedelta(
                    days=int(rng.integers(0, 45)), hours=int(rng.integers(0, 24))
                ),
            }
        )

    phones = [
        {
            "phone_hash": make_phone_hash(i),
            "first_seen_at": START
            + pd.Timedelta(
                days=int(rng.integers(0, 45)), hours=int(rng.integers(0, 24))
            ),
        }
        for i in range(n_phones)
    ]
    instruments = []
    for i in range(n_instruments):
        typ = rng.choice(
            ["card", "upi", "netbanking", "wallet"], p=[0.45, 0.38, 0.10, 0.07]
        )
        instruments.append(
            {
                "instrument_id": make_instrument_id(i),
                "instrument_type": typ,
                "bin_or_vpa_hash": make_instrument_hash(i),
                "first_seen_at": START
                + pd.Timedelta(
                    days=int(rng.integers(0, 45)), hours=int(rng.integers(0, 24))
                ),
            }
        )

    return map(pd.DataFrame, [devices, addresses, phones, instruments])


def assign_resources(accounts, devices, addresses, phones, instruments):
    """Assign resources using sorted first-seen arrays (O(accounts log n))."""
    specs = {
        "devices": (devices.sort_values("first_seen_at"), "device_id"),
        "addresses": (addresses.sort_values("first_seen_at"), "address_id"),
        "phones": (phones.sort_values("first_seen_at"), "phone_hash"),
        "instruments": (instruments.sort_values("first_seen_at"), "instrument_id"),
    }
    arrays = {}
    for key, (df, id_col) in specs.items():
        seen = pd.to_datetime(df["first_seen_at"]).astype("int64").to_numpy()
        ids = df[id_col].to_numpy()
        arrays[key] = (ids, seen)

    result = {}
    for row in accounts.to_dict("records"):
        created_ns = pd.Timestamp(row["account_created_at"]).value
        share = float(row["_share_p"])
        selected = {}
        for key in arrays:
            ids, seen = arrays[key]
            eligible = int(np.searchsorted(seen, created_ns, side="right"))
            eligible = max(1, eligible)
            if key == "phones":
                count = 1
            elif key == "devices":
                count = 2 if rng.random() < (0.12 + 0.20 * share) else 1
            elif key == "addresses":
                count = 2 if rng.random() < (0.15 + 0.15 * share) else 1
            else:
                count = 2 if rng.random() < 0.12 else 1
            count = min(count, eligible)
            idx = rng.choice(eligible, size=count, replace=False)
            selected[key] = ids[idx].tolist()
        result[row["account_id"]] = selected
    return result


def activity_times(created, rate, count):
    if count <= 0:
        return []
    t = pd.Timestamp(created)
    out = []
    for _ in range(count * 5 + 4):
        # Heterogeneous inter-arrivals; intensity rises around weekends and common paydays.
        mean_days = max(0.18, 4.2 / (rate + 0.35))
        t += pd.Timedelta(days=float(rng.exponential(mean_days)))
        if t > CUTOFF:
            break
        weekend = 1.28 if t.dayofweek >= 5 else 1.0
        payday = (
            1.25 if min(abs(t.day - 1), abs(t.day - 15), abs(t.day - 30)) <= 2 else 1.0
        )
        evening = 1.18 if 18 <= t.hour <= 22 else 0.92
        if rng.random() < min(0.96, 0.42 * weekend * payday * evening):
            out.append(t)
        if len(out) >= count:
            break
    return out


def amount(category, value):
    lo, hi = CAT_RANGES[category]
    center = math.log((lo + hi) / 2) + 0.20 * value
    sigma = 0.52 if category in ("electronics", "home") else 0.44
    x = float(np.exp(rng.normal(center, sigma)))
    return float(np.clip(round(x / 10) * 10, lo, hi))


def order_row(
    oid,
    aid,
    resources,
    ts,
    category,
    amt,
    discount,
    coupon,
    ret,
    reason,
    dispute=False,
    dispute_cat=None,
):
    delivery = ts + pd.Timedelta(
        days=int(rng.choice([1, 2, 3, 4], p=[0.18, 0.47, 0.28, 0.07]))
    )
    if delivery > END:
        delivery = END - pd.Timedelta(hours=1)
    if delivery <= ts:
        delivery = ts + pd.Timedelta(hours=6)
    returned = bool(ret and delivery <= END - pd.Timedelta(days=1))
    if returned:
        rt = min(
            delivery
            + pd.Timedelta(
                days=int(rng.choice([1, 2, 3, 4, 5], p=[0.10, 0.27, 0.32, 0.23, 0.08]))
            ),
            END - pd.Timedelta(days=1),
        )
        refund = min(
            rt + pd.Timedelta(hours=int(rng.integers(4, 48))),
            END - pd.Timedelta(hours=1),
        )
        refund_amount = amt
    else:
        rt = pd.NaT
        refund = pd.NaT
        refund_amount = None
    if dispute and delivery <= END - pd.Timedelta(days=1):
        base = refund if pd.notna(refund) else delivery
        dt = min(
            base + pd.Timedelta(days=int(rng.integers(1, 4))),
            END - pd.Timedelta(hours=1),
        )
        phase = rng.choice(
            ["retrieval", "pre_arbitration", "arbitration"], p=[0.58, 0.34, 0.08]
        )
        code = rng.choice(
            [
                "item_not_received",
                "not_as_described",
                "unauthorized_transaction",
                "duplicate_charge",
            ],
            p=[0.48, 0.25, 0.12, 0.15],
        )
    else:
        dt = pd.NaT
        phase = None
        code = None
        dispute = False
    return {
        "order_id": oid,
        "account_id": aid,
        "device_id": rng.choice(resources["devices"]),
        "address_id": rng.choice(resources["addresses"]),
        "phone_hash": rng.choice(resources["phones"]),
        "instrument_id": rng.choice(resources["instruments"]),
        "amount": amt,
        "discount_amount": discount,
        "coupon_code": coupon,
        "category": category,
        "order_timestamp": ts,
        "delivery_status": "delivered",
        "delivery_attempts": int(rng.choice([1, 2, 3], p=[0.72, 0.23, 0.05])),
        "delivery_timestamp": delivery,
        "rto_flag": False,
        "return_flag": returned,
        "return_reason_code": reason if returned else None,
        "return_timestamp": rt,
        "return_lag_hours": (
            float((rt - delivery).total_seconds() / 3600) if returned else None
        ),
        "refund_flag": returned,
        "refund_amount": refund_amount,
        "refund_timestamp": refund,
        "dispute_flag": bool(dispute),
        "dispute_created_at": dt,
        "dispute_phase": phase,
        "dispute_reason_code": code,
        "dispute_reason_category": (
            dispute_cat if dispute else ("customer_dispute" if dispute else None)
        ),
        "evidence_availability": None,
    }


def base_orders(accounts, assignments):
    orders = []
    counter = 0
    for row in accounts.to_dict("records"):
        n = poisson_count(2.0 * row["_activity_rate"])
        for ts in activity_times(row["account_created_at"], row["_activity_rate"], n):
            cat = rng.choice(CATEGORIES, p=CAT_W)
            amt = amount(cat, row["_value"])
            coupon = bool(rng.random() < row["_discount_p"] * 0.58)
            disc = round(amt * rng.uniform(0.04, 0.18), 2) if coupon else 0.0
            code = f"PROMO_{rng.integers(100,9999)}" if coupon else None
            ret = rng.random() < row["_return_p"]
            reason = (
                rng.choice(
                    ["size_fit", "changed_mind", "not_as_described", "defective"],
                    p=[0.30, 0.25, 0.25, 0.20],
                )
                if ret
                else None
            )
            dispute = rng.random() < row["_dispute_p"]
            orders.append(
                order_row(
                    make_order_id(counter),
                    row["account_id"],
                    assignments[row["account_id"]],
                    ts,
                    cat,
                    amt,
                    disc,
                    code,
                    ret,
                    reason,
                    dispute,
                )
            )
            counter += 1
    return orders, counter


def ring_plan():
    plan = []
    for rt, count in N_RING_TYPES.items():
        size = RING_ACCOUNTS_PER_TYPE[rt]
        for _ in range(count):
            plan.append((rt, size))
    return plan


def add_shared_entity(df, kind, first_seen, ring_key, ip_prefix=None, drop=False):
    if kind == "device":
        i = len(df)
        ident = make_device_id(i)
        row = {
            "device_id": ident,
            "os_family": rng.choice(
                ["Android", "iOS", "Windows"], p=[0.55, 0.25, 0.20]
            ),
            "browser_family": "Chrome",
            "ip_prefix": ip_prefix
            or f"10.{rng.integers(1,255)}.{rng.integers(1,255)}.0/24",
            "first_seen_at": first_seen,
        }
    elif kind == "address":
        i = len(df)
        ident = make_address_id(i)
        city, state, prefs = LOCATIONS[int(rng.integers(len(LOCATIONS)))]
        pin = rng.choice(prefs) + f"{rng.integers(1000):03d}"
        row = {
            "address_id": ident,
            "canonical_address": normalize_address(
                f"{rng.integers(1,999)}, {ring_key} locality, {city}, {state} {pin}"
            ),
            "city": city,
            "pincode": pin,
            "is_drop_address": drop,
            "first_seen_at": first_seen,
        }
    elif kind == "phone":
        i = len(df)
        ident = make_phone_hash(i)
        row = {"phone_hash": ident, "first_seen_at": first_seen}
    else:
        i = len(df)
        ident = make_instrument_id(i)
        typ = rng.choice(["card", "upi"], p=[0.55, 0.45])
        row = {
            "instrument_id": ident,
            "instrument_type": typ,
            "bin_or_vpa_hash": make_instrument_hash(i),
            "first_seen_at": first_seen,
        }
    df.loc[len(df)] = row
    return ident


def inject_rings(
    accounts, devices, addresses, phones, instruments, assignments, orders, counter
):
    ring_ids = accounts.loc[accounts.population_type == "ring", "account_id"].tolist()
    rng.shuffle(ring_ids)
    lookup = accounts.set_index("account_id").to_dict("index")
    members = []
    pos = 0
    orders_by_account = defaultdict(list)
    for o in orders:
        orders_by_account[o["account_id"]].append(o)
    for ridx, (rt, size) in enumerate(ring_plan(), start=1):
        ids = ring_ids[pos : pos + size]
        pos += size
        rid = f"R{ridx:03d}"
        max_created = max(pd.Timestamp(lookup[x]["account_created_at"]) for x in ids)
        start = max(
            START + pd.Timedelta(days=int(rng.integers(8, 40))),
            max_created + pd.Timedelta(days=1),
        )
        if start >= CUTOFF:
            start = CUTOFF - pd.Timedelta(days=3)
        # One or more shared anchors. Membership is probabilistic, so benign reuse remains common.
        anchor_device = add_shared_entity(
            devices, "device", start - pd.Timedelta(hours=int(rng.integers(2, 12))), rid
        )
        anchor_addr = add_shared_entity(
            addresses,
            "address",
            start - pd.Timedelta(hours=int(rng.integers(2, 12))),
            rid,
            drop=(rt == "friendly_fraud" and rng.random() < 0.5),
        )
        anchor_phone = add_shared_entity(
            phones, "phone", start - pd.Timedelta(hours=2), rid
        )
        anchor_inst = add_shared_entity(
            instruments, "instrument", start - pd.Timedelta(hours=2), rid
        )
        for idx, aid in enumerate(ids):
            strength = float(rng.beta(2.2, 3.0))
            if rng.random() < 0.12:
                strength *= 0.25
            res = assignments[aid]
            # Different ring types emphasize different edges, with substantial omissions.
            probs = {
                "wardrobing": (0.50, 0.28, 0.12, 0.10),
                "promo_refund_farming": (0.65, 0.18, 0.08, 0.70),
                "friendly_fraud": (0.18, 0.62, 0.58, 0.12),
                "subtle_distributed": (0.35, 0.32, 0.18, 0.34),
            }[rt]
            if rng.random() < probs[0] * strength:
                res["devices"] = [anchor_device] + res["devices"][:1]
            if rng.random() < probs[1] * strength:
                res["addresses"] = [anchor_addr] + res["addresses"][:1]
            if rng.random() < probs[2] * strength:
                res["phones"] = [anchor_phone]
            if rng.random() < probs[3] * strength:
                res["instruments"] = [anchor_inst] + res["instruments"][:1]
            assignments[aid] = res

            # Behavioral overlay: modify a subset of existing orders plus a few events.
            acc_orders = orders_by_account.get(aid, [])
            extra_rate = {
                "wardrobing": 0.8,
                "promo_refund_farming": 0.9,
                "friendly_fraud": 0.55,
                "subtle_distributed": 0.7,
            }[rt]
            for o in acc_orders:
                if rng.random() < 0.35 * strength:
                    if rt == "wardrobing":
                        o["return_flag"] = bool(rng.random() < 0.35 + 0.35 * strength)
                    elif rt == "promo_refund_farming":
                        if rng.random() < 0.55 * strength:
                            o["discount_amount"] = round(
                                o["amount"] * rng.uniform(0.10, 0.30), 2
                            )
                            o["coupon_code"] = f"PROMO_{rng.integers(100,9999)}"
                    elif rt == "friendly_fraud":
                        o["dispute_flag"] = bool(rng.random() < 0.18 + 0.32 * strength)
                        if o["dispute_flag"]:
                            o["dispute_reason_category"] = "customer_dispute"
                    else:
                        o["return_flag"] = bool(rng.random() < 0.18 + 0.20 * strength)
                # Shared resource is not forced on every event.
                if rng.random() < 0.35 * strength:
                    o["device_id"] = anchor_device
                if rng.random() < 0.25 * strength:
                    o["address_id"] = anchor_addr
                if (
                    rt in ("promo_refund_farming", "subtle_distributed")
                    and rng.random() < 0.30 * strength
                ):
                    o["instrument_id"] = anchor_inst
                if rt == "friendly_fraud" and rng.random() < 0.32 * strength:
                    o["phone_hash"] = anchor_phone
            n_extra = int(rng.poisson(0.8 + 2.2 * strength))
            for _ in range(min(5, n_extra)):
                base_time = start + pd.Timedelta(hours=float(rng.uniform(0, 72)))
                if base_time <= pd.Timestamp(lookup[aid]["account_created_at"]):
                    base_time = pd.Timestamp(
                        lookup[aid]["account_created_at"]
                    ) + pd.Timedelta(hours=int(rng.integers(2, 18)))
                if base_time >= CUTOFF:
                    continue
                cat = rng.choice(CATEGORIES, p=CAT_W)
                amt = amount(cat, lookup[aid]["_value"])
                discount_p = lookup[aid]["_discount_p"]
                if rt == "promo_refund_farming":
                    discount_p = min(0.95, discount_p + 0.25 * strength)
                coupon = rng.random() < discount_p * 0.62
                disc = round(amt * rng.uniform(0.05, 0.28), 2) if coupon else 0.0
                code = f"PROMO_{rng.integers(100,9999)}" if coupon else None
                ret_p = (
                    lookup[aid]["_return_p"]
                    + (
                        {
                            "wardrobing": 0.32,
                            "promo_refund_farming": 0.20,
                            "friendly_fraud": 0.10,
                            "subtle_distributed": 0.16,
                        }[rt]
                    )
                    * strength
                )
                ret = rng.random() < min(0.88, ret_p)
                reason = (
                    rng.choice(
                        ["size_fit", "changed_mind", "not_as_described", "defective"],
                        p=[0.28, 0.24, 0.30, 0.18],
                    )
                    if ret
                    else None
                )
                disp = rt == "friendly_fraud" and rng.random() < min(
                    0.65, lookup[aid]["_dispute_p"] + 0.24 * strength
                )
                new_order = order_row(
                    make_order_id(counter),
                    aid,
                    assignments[aid],
                    base_time,
                    cat,
                    amt,
                    disc,
                    code,
                    ret,
                    reason,
                    disp,
                    "customer_dispute" if disp else None,
                )
                orders.append(new_order)
                orders_by_account[aid].append(new_order)
                counter += 1
            members.append(
                {
                    "account_id": aid,
                    "abuse_ring_id": rid,
                    "ring_type": rt,
                    "ring_start_time": pd.Timestamp(lookup[aid]["account_created_at"]),
                    "ring_end_time": pd.Timestamp(lookup[aid]["account_created_at"])
                    + pd.Timedelta(days=int(rng.integers(8, 17))),
                }
            )
    # Ensure every ring member has at least one order before cutoff
    for member in members:
        acc_id = member["account_id"]
        if len(orders_by_account.get(acc_id, [])) == 0:
            # Generate a minimal order for this account
            a = lookup[acc_id]
            res = assignments[acc_id]
            base_time = min(
                start + pd.Timedelta(hours=int(rng.uniform(1, 12))),
                CUTOFF - pd.Timedelta(days=1),
            )
            cat = rng.choice(CATEGORIES, p=CAT_W)
            amt = amount(cat, a["_value"])
            coupon = rng.random() < a["_discount_p"] * 0.5
            disc = round(amt * rng.uniform(0.05, 0.2), 2) if coupon else 0.0
            code = f"PROMO_{rng.integers(100,9999)}" if coupon else None
            ret = rng.random() < a["_return_p"]
            reason = (
                rng.choice(
                    ["size_fit", "changed_mind", "not_as_described", "defective"]
                )
                if ret
                else None
            )
            disp = False  # or small probability
            new_order = order_row(
                make_order_id(counter),
                acc_id,
                res,
                base_time,
                cat,
                amt,
                disc,
                code,
                ret,
                reason,
                disp,
            )
            orders.append(new_order)
            orders_by_account[acc_id] = [new_order]
            counter += 1
    assert pos == N_RING_ACCOUNTS
    return accounts, devices, addresses, phones, instruments, orders, members, counter


def inject_hard_negatives(accounts, assignments, orders, counter):
    hard = accounts[accounts.population_type == "hard_negative"].account_id.tolist()
    rng.shuffle(hard)
    lookup = accounts.set_index("account_id").to_dict("index")
    # Legitimate causes overlap with the fraud feature manifold. Groups share resources naturally,
    # but there is no coordinated abuse overlay and no ground-truth label.
    modes = rng.choice(
        [
            "family",
            "bargain",
            "office",
            "high_return",
            "hostel",
            "traveler",
            "frequent",
        ],
        len(hard),
        p=[0.18, 0.16, 0.14, 0.18, 0.12, 0.10, 0.12],
    )
    groups = []
    for mode in ["family", "office", "hostel"]:
        ids = [a for a, m in zip(hard, modes) if m == mode]
        group_size = 4 if mode == "family" else 5
        for j in range(0, len(ids), group_size):
            groups.append((mode, ids[j : j + group_size]))
    for mode, ids in groups:
        if len(ids) < 3:
            continue
        # Reuse existing resources from one account to create legitimate sharing.
        donor = assignments[ids[0]]
        for aid in ids[1:]:
            if rng.random() < 0.72:
                assignments[aid]["devices"] = donor["devices"][:1]
            if rng.random() < 0.65:
                assignments[aid]["addresses"] = donor["addresses"][:1]
            if mode == "hostel" and rng.random() < 0.75:
                assignments[aid]["devices"] = donor["devices"][:1]
    for aid, mode in zip(hard, modes):
        a = lookup[aid]
        res = assignments[aid]
        n = {
            "family": 6,
            "bargain": 7,
            "office": 5,
            "high_return": 6,
            "hostel": 5,
            "traveler": 4,
            "frequent": 9,
        }[mode]
        rp = {
            "family": 0.14,
            "bargain": 0.30,
            "office": 0.11,
            "high_return": 0.56,
            "hostel": 0.17,
            "traveler": 0.21,
            "frequent": 0.23,
        }[mode]
        dp = {
            "family": 0.30,
            "bargain": 0.64,
            "office": 0.25,
            "high_return": 0.20,
            "hostel": 0.37,
            "traveler": 0.19,
            "frequent": 0.30,
        }[mode]
        times = activity_times(a["account_created_at"], max(1, a["_activity_rate"]), n)
        for ts in times:
            cat = rng.choice(CATEGORIES, p=CAT_W)
            amt = amount(cat, a["_value"])
            coupon = rng.random() < dp
            disc = round(amt * rng.uniform(0.05, 0.28), 2) if coupon else 0.0
            code = f"PROMO_{rng.integers(100,9999)}" if coupon else None
            ret = rng.random() < rp
            reason = (
                rng.choice(
                    ["size_fit", "changed_mind", "not_as_described", "defective"]
                )
                if ret
                else None
            )
            disp = mode in ("family", "traveler", "frequent") and rng.random() < 0.045
            orders.append(
                order_row(
                    make_order_id(counter),
                    aid,
                    res,
                    ts,
                    cat,
                    amt,
                    disc,
                    code,
                    ret,
                    reason,
                    disp,
                )
            )
            counter += 1
    return orders, counter


def aux_tables(orders):
    odf = pd.DataFrame(orders)
    refunds = []
    disputes = []
    for i, row in odf[odf.refund_flag].reset_index(drop=True).iterrows():
        refunds.append(
            {
                "refund_id": make_refund_id(i),
                "order_id": row.order_id,
                "account_id": row.account_id,
                "refund_timestamp": row.refund_timestamp,
                "refund_amount": float(row.refund_amount),
                "refund_reason": row.return_reason_code,
                "refund_status": rng.choice(
                    ["processed", "processed", "pending_review"]
                ),
                "refund_method": rng.choice(
                    ["original_payment", "wallet", "bank_transfer"]
                ),
            }
        )
    for i, row in odf[odf.dispute_flag].reset_index(drop=True).iterrows():
        probs = np.array([0.72, 0.58, 0.64, 0.48, 0.80, 0.78])
        if row.dispute_reason_category == "customer_dispute":
            probs *= rng.uniform(0.72, 1.0, 6)
        ev = rng.random(6) < probs
        disputes.append(
            {
                "dispute_id": make_dispute_id(i),
                "order_id": row.order_id,
                "account_id": row.account_id,
                "dispute_created_at": row.dispute_created_at,
                "dispute_phase": row.dispute_phase,
                "dispute_reason_code": row.dispute_reason_code,
                "dispute_reason_category": row.dispute_reason_category,
                "respond_by": min(row.dispute_created_at + pd.Timedelta(days=7), END),
                "proof_of_service": bool(ev[0]),
                "explanation_letter": bool(ev[1]),
                "refund_confirmation": bool(ev[2]),
                "access_activity_log": bool(ev[3]),
                "refund_cancellation_policy": bool(ev[4]),
                "terms_and_conditions": bool(ev[5]),
            }
        )
    return odf, pd.DataFrame(refunds), pd.DataFrame(disputes)


def ground_truth(accounts, members):
    gt = accounts[["account_id"]].copy()
    gt["abuse_ring_id"] = None
    gt["true_ring_member"] = False
    gt["ring_type"] = None
    gt["ring_start_time"] = pd.NaT
    gt["ring_end_time"] = pd.NaT
    for m in members:
        mask = gt.account_id == m["account_id"]
        gt.loc[
            mask,
            [
                "abuse_ring_id",
                "true_ring_member",
                "ring_type",
                "ring_start_time",
                "ring_end_time",
            ],
        ] = [
            m["abuse_ring_id"],
            True,
            m["ring_type"],
            m["ring_start_time"],
            m["ring_end_time"],
        ]
    return gt


def write_all(
    accounts, devices, addresses, phones, instruments, orders, refunds, disputes, gt
):
    # Public accounts: remove population_type
    public_accounts = accounts[
        ["account_id", "account_created_at", "customer_type"]
    ].copy()
    # Save population_type separately (private)
    private_accounts = accounts[["account_id", "population_type"]].copy()
    private_accounts.to_csv(
        PATHS["accounts"].parent / "account_population_labels_private.csv", index=False
    )

    for name, df in [
        ("accounts", public_accounts),
        ("devices", devices),
        ("addresses", addresses),
        ("phones", phones),
        ("payment_instruments", instruments),
        ("orders", orders),
        ("refunds", refunds),
        ("disputes", disputes),
        ("ring_ground_truth", gt),
    ]:
        df.to_csv(PATHS[name], index=False)


def generate_dataset():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    accounts = latent_accounts()
    devices, addresses, phones, instruments = make_entities(accounts)
    # map() above returns an iterator; materialize it.
    devices, addresses, phones, instruments = map(
        lambda x: x.copy(), [devices, addresses, phones, instruments]
    )
    assignments = assign_resources(accounts, devices, addresses, phones, instruments)
    orders, counter = base_orders(accounts, assignments)
    accounts, devices, addresses, phones, instruments, orders, members, counter = (
        inject_rings(
            accounts,
            devices,
            addresses,
            phones,
            instruments,
            assignments,
            orders,
            counter,
        )
    )
    orders, counter = inject_hard_negatives(accounts, assignments, orders, counter)
    orders_df, refunds, disputes = aux_tables(orders)
    gt = ground_truth(accounts, members)
    write_all(
        accounts,
        devices,
        addresses,
        phones,
        instruments,
        orders_df,
        refunds,
        disputes,
        gt,
    )
    return (
        accounts,
        devices,
        addresses,
        phones,
        instruments,
        orders_df,
        refunds,
        disputes,
        gt,
    )
