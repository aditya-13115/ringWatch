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

    if (
        HARD_NEGATIVE_ACCOUNT_START
        <= account_index
        <= HARD_NEGATIVE_ACCOUNT_END
    ):
        return "hard_negative"

    raise ValueError(
        f"Account index {account_index} "
        "does not belong to a valid population range."
    )


def generate_accounts():
    rows = []

    account_start = pd.Timestamp(START_DATE)

    # Keep normal accounts available for ordinary behaviour.
    account_end = (
        pd.Timestamp(END_DATE)
        - pd.Timedelta(days=30)
    )

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

    df = df.sort_values(
        "account_id"
    ).reset_index(drop=True)

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

        browser_family = rng.choice(
            browser_by_os[os_family]
        )

        ip_prefix = (
            f"10."
            f"{rng.integers(0, 256)}."
            f"{rng.integers(0, 256)}.0/24"
        )

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

    return pd.DataFrame(rows)


def generate_addresses():
    rows = []

    cities = [
        "Mumbai",
        "Delhi",
        "Bengaluru",
        "Chennai",
        "Hyderabad",
        "Pune",
        "Ahmedabad",
        "Kolkata",
        "Jaipur",
        "Lucknow",
        "Vapi",
        "Surat",
    ]

    for i in range(N_ADDRESSES):

        address = fake.address().replace(
            "\n",
            ", ",
        )

        city = rng.choice(cities)

        pincode = str(
            rng.integers(
                100000,
                999999,
            )
        )

        rows.append(
            {
                "address_id": make_address_id(i),
                "canonical_address": address,
                "city": city,
                "pincode": pincode,

                # Ring injection can update this later.
                "is_drop_address": False,

                "first_seen_at": random_datetime(
                    START_DATE,
                    END_DATE,
                ),
            }
        )

    return pd.DataFrame(rows)


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

    return pd.DataFrame(rows)


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

                "bin_or_vpa_hash":
                    make_instrument_hash(i),

                "first_seen_at": random_datetime(
                    START_DATE,
                    END_DATE,
                ),
            }
        )

    return pd.DataFrame(rows)


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