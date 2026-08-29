# generator/entities.py

import numpy as np
import pandas as pd
from faker import Faker

from .config import (
    SEED,
    START_DATE,
    END_DATE,
    N_ACCOUNTS,
    N_DEVICES,
    N_ADDRESSES,
    N_PHONES,
    N_INSTRUMENTS,
    N_NORMAL_ACCOUNTS,
    N_RING_ACCOUNTS,
    N_HARD_NEGATIVE_ACCOUNTS,
    NORMAL_ACCOUNT_START,
    NORMAL_ACCOUNT_END,
    RING_ACCOUNT_START,
    RING_ACCOUNT_END,
    HARD_NEGATIVE_ACCOUNT_START,
    HARD_NEGATIVE_ACCOUNT_END,
    DATA_DIR,
    PATHS,
)

from .ids import (
    make_account_id,
    make_device_id,
    make_address_id,
    make_phone_hash,
    make_instrument_id,
    make_instrument_hash,
)

from .address_utils import normalize_address

fake = Faker("en_IN")
fake.seed_instance(SEED)

rng = np.random.default_rng(SEED)


def random_datetime(start, end):
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    seconds = int((end - start).total_seconds())
    offset = rng.integers(0, seconds + 1)

    return start + pd.Timedelta(seconds=int(offset))


def get_population_type(account_index):
    if NORMAL_ACCOUNT_START <= account_index <= NORMAL_ACCOUNT_END:
        return "normal"

    if RING_ACCOUNT_START <= account_index <= RING_ACCOUNT_END:
        return "ring"

    if HARD_NEGATIVE_ACCOUNT_START <= account_index <= HARD_NEGATIVE_ACCOUNT_END:
        return "hard_negative"

    raise ValueError(
        f"Account index {account_index} does not belong "
        f"to a valid population range."
    )


def generate_accounts():
    rows = []

    account_start = pd.Timestamp(START_DATE)
    account_end = pd.Timestamp(END_DATE) - pd.Timedelta(days=30)

    customer_types = [
        "regular",
        "new",
        "guest",
    ]

    probabilities = [
        0.75,
        0.20,
        0.05,
    ]

    for i in range(N_ACCOUNTS):
        population_type = get_population_type(i)

        rows.append(
            {
                "account_id": make_account_id(i),
                "account_created_at": random_datetime(
                    account_start,
                    account_end,
                ),
                "customer_type": rng.choice(
                    customer_types,
                    p=probabilities,
                ),
                "population_type": population_type,
            }
        )

    df = pd.DataFrame(rows)

    df = df.sort_values("account_id").reset_index(drop=True)

    # ---------------------------------------------------------
    # Population sanity checks
    # ---------------------------------------------------------

    if len(df) != N_ACCOUNTS:
        raise AssertionError(f"Expected {N_ACCOUNTS} accounts, got {len(df)}.")

    if not df["account_id"].is_unique:
        raise AssertionError("Duplicate account IDs generated.")

    expected = {
        "normal": N_NORMAL_ACCOUNTS,
        "ring": N_RING_ACCOUNTS,
        "hard_negative": N_HARD_NEGATIVE_ACCOUNTS,
    }

    counts = df["population_type"].value_counts().to_dict()

    if counts != expected:
        raise AssertionError(
            f"Population mismatch: {counts} " f"vs expected {expected}"
        )

    return df


# -------------------------------------------------------------
# Realistic Indian locations used for base address generation
# -------------------------------------------------------------

LOCATIONS = [
    {
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode_prefix": ["400", "401"],
    },
    {
        "city": "Delhi",
        "state": "Delhi",
        "pincode_prefix": ["110"],
    },
    {
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode_prefix": ["560"],
    },
    {
        "city": "Chennai",
        "state": "Tamil Nadu",
        "pincode_prefix": ["600"],
    },
    {
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode_prefix": ["500"],
    },
    {
        "city": "Pune",
        "state": "Maharashtra",
        "pincode_prefix": ["411"],
    },
    {
        "city": "Ahmedabad",
        "state": "Gujarat",
        "pincode_prefix": ["380"],
    },
    {
        "city": "Kolkata",
        "state": "West Bengal",
        "pincode_prefix": ["700"],
    },
    {
        "city": "Jaipur",
        "state": "Rajasthan",
        "pincode_prefix": ["302"],
    },
    {
        "city": "Lucknow",
        "state": "Uttar Pradesh",
        "pincode_prefix": ["226"],
    },
    {
        "city": "Vapi",
        "state": "Gujarat",
        "pincode_prefix": ["396"],
    },
    {
        "city": "Surat",
        "state": "Gujarat",
        "pincode_prefix": ["395"],
    },
]


def generate_addresses():
    rows = []

    for i in range(N_ADDRESSES):
        loc = rng.choice(LOCATIONS)

        city = loc["city"]
        state = loc["state"]

        prefix = rng.choice(loc["pincode_prefix"])

        pincode = prefix + f"{rng.integers(0, 1000):03d}"

        house_num = fake.building_number()
        street = fake.street_name()
        locality = f"{city} Locality {rng.integers(1, 500)}"

        raw_address = f"{house_num}, {street}, {locality}, {city}, {state} {pincode}"

        canonical = normalize_address(raw_address)

        rows.append(
            {
                "address_id": make_address_id(i),
                "canonical_address": canonical,
                "city": city,
                "pincode": pincode,
                "is_drop_address": False,
                "first_seen_at": random_datetime(
                    START_DATE,
                    END_DATE,
                ),
            }
        )

    df = pd.DataFrame(rows)

    if len(df) != N_ADDRESSES:
        raise AssertionError(f"Expected {N_ADDRESSES} addresses, got {len(df)}.")

    if not df["address_id"].is_unique:
        raise AssertionError("Duplicate address IDs generated.")

    return df


def generate_devices():
    rows = []

    os_families = [
        "Android",
        "iOS",
        "Windows",
        "macOS",
        "Linux",
    ]

    os_probabilities = [
        0.48,
        0.25,
        0.15,
        0.10,
        0.02,
    ]

    browser_by_os = {
        "Android": [
            "Chrome",
            "Firefox",
            "Edge",
        ],
        "iOS": [
            "Safari",
            "Chrome",
        ],
        "Windows": [
            "Chrome",
            "Edge",
            "Firefox",
        ],
        "macOS": [
            "Safari",
            "Chrome",
            "Firefox",
        ],
        "Linux": [
            "Chrome",
            "Firefox",
        ],
    }

    for i in range(N_DEVICES):
        os_family = rng.choice(
            os_families,
            p=os_probabilities,
        )

        browser_family = rng.choice(browser_by_os[os_family])

        ip_prefix = f"10." f"{rng.integers(0, 256)}." f"{rng.integers(0, 256)}." f"0/24"

        rows.append(
            {
                "device_id": make_device_id(i),
                "os_family": os_family,
                "browser_family": browser_family,
                "ip_prefix": ip_prefix,
                "first_seen_at": random_datetime(
                    START_DATE,
                    END_DATE,
                ),
            }
        )

    df = pd.DataFrame(rows)

    if len(df) != N_DEVICES:
        raise AssertionError(f"Expected {N_DEVICES} devices, got {len(df)}.")

    if not df["device_id"].is_unique:
        raise AssertionError("Duplicate device IDs generated.")

    return df


def generate_phones():
    rows = []

    for i in range(N_PHONES):
        rows.append(
            {
                "phone_hash": make_phone_hash(i),
                "first_seen_at": random_datetime(
                    START_DATE,
                    END_DATE,
                ),
            }
        )

    df = pd.DataFrame(rows)

    if len(df) != N_PHONES:
        raise AssertionError(f"Expected {N_PHONES} phones, got {len(df)}.")

    if not df["phone_hash"].is_unique:
        raise AssertionError("Duplicate phone hashes generated.")

    return df


def generate_payment_instruments():
    rows = []

    instrument_types = [
        "card",
        "upi",
        "netbanking",
        "wallet",
    ]

    probabilities = [
        0.40,
        0.40,
        0.10,
        0.10,
    ]

    for i in range(N_INSTRUMENTS):
        instrument_type = rng.choice(
            instrument_types,
            p=probabilities,
        )

        rows.append(
            {
                "instrument_id": make_instrument_id(i),
                "instrument_type": instrument_type,
                "bin_or_vpa_hash": make_instrument_hash(i),
                "first_seen_at": random_datetime(
                    START_DATE,
                    END_DATE,
                ),
            }
        )

    df = pd.DataFrame(rows)

    if len(df) != N_INSTRUMENTS:
        raise AssertionError(
            f"Expected {N_INSTRUMENTS} payment instruments, " f"got {len(df)}."
        )

    if not df["instrument_id"].is_unique:
        raise AssertionError("Duplicate instrument IDs generated.")

    return df


def generate_all_entities():
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    accounts = generate_accounts()
    devices = generate_devices()
    addresses = generate_addresses()
    phones = generate_phones()
    instruments = generate_payment_instruments()

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

    return {
        "accounts": accounts,
        "devices": devices,
        "addresses": addresses,
        "phones": phones,
        "payment_instruments": instruments,
    }
