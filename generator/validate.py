import pandas as pd

from .config import (
    START_DATE,
    END_DATE,
    PATHS,
)


def check_unique(df, column, table_name):
    duplicates = df[column].duplicated().sum()

    if duplicates > 0:
        raise ValueError(
            f"{table_name}.{column}: "
            f"{duplicates} duplicate values found."
        )


def check_timestamps(df, column, table_name):
    start = pd.Timestamp(START_DATE)
    end = pd.Timestamp(END_DATE)

    values = pd.to_datetime(df[column])

    invalid = ((values < start) | (values > end)).sum()

    if invalid > 0:
        raise ValueError(
            f"{table_name}.{column}: "
            f"{invalid} timestamps outside dataset window."
        )


def validate_entities():
    accounts = pd.read_csv(PATHS["accounts"])
    devices = pd.read_csv(PATHS["devices"])
    addresses = pd.read_csv(PATHS["addresses"])
    phones = pd.read_csv(PATHS["phones"])
    instruments = pd.read_csv(
        PATHS["payment_instruments"]
    )

    tables = {
        "accounts": accounts,
        "devices": devices,
        "addresses": addresses,
        "phones": phones,
        "payment_instruments": instruments,
    }

    print("=" * 55)
    print("RINGWATCH DAY-1 DATASET VALIDATION")
    print("=" * 55)

    # Required columns
    required_columns = {
        "accounts": [
            "account_id",
            "account_created_at",
            "customer_type",
        ],
        "devices": [
            "device_id",
            "os_family",
            "browser_family",
            "ip_prefix",
            "first_seen_at",
        ],
        "addresses": [
            "address_id",
            "canonical_address",
            "city",
            "pincode",
            "is_drop_address",
            "first_seen_at",
        ],
        "phones": [
            "phone_hash",
            "first_seen_at",
        ],
        "payment_instruments": [
            "instrument_id",
            "instrument_type",
            "bin_or_vpa_hash",
            "first_seen_at",
        ],
    }

    for table_name, columns in required_columns.items():
        df = tables[table_name]

        for column in columns:
            if column not in df.columns:
                raise ValueError(
                    f"Missing column: "
                    f"{table_name}.{column}"
                )

    # Unique IDs
    check_unique(
        accounts,
        "account_id",
        "accounts",
    )

    check_unique(
        devices,
        "device_id",
        "devices",
    )

    check_unique(
        addresses,
        "address_id",
        "addresses",
    )

    check_unique(
        phones,
        "phone_hash",
        "phones",
    )

    check_unique(
        instruments,
        "instrument_id",
        "payment_instruments",
    )

    check_unique(
        instruments,
        "bin_or_vpa_hash",
        "payment_instruments",
    )

    # Timestamp checks
    check_timestamps(
        accounts,
        "account_created_at",
        "accounts",
    )

    for table_name in [
        "devices",
        "addresses",
        "phones",
        "payment_instruments",
    ]:
        check_timestamps(
            tables[table_name],
            "first_seen_at",
            table_name,
        )

    # Null checks
    for table_name, df in tables.items():
        if df.isnull().any().any():
            null_count = int(df.isnull().sum().sum())

            raise ValueError(
                f"{table_name}: "
                f"{null_count} null values found."
            )

    # Valid categorical values
    valid_customer_types = {
        "regular",
        "new",
        "guest",
    }

    if not set(accounts["customer_type"]).issubset(
        valid_customer_types
    ):
        raise ValueError(
            "Invalid customer_type found."
        )

    valid_os = {
        "Android",
        "iOS",
        "Windows",
        "macOS",
        "Linux",
    }

    if not set(devices["os_family"]).issubset(
        valid_os
    ):
        raise ValueError(
            "Invalid os_family found."
        )

    valid_instruments = {
        "card",
        "upi",
        "netbanking",
        "wallet",
    }

    if not set(
        instruments["instrument_type"]
    ).issubset(valid_instruments):
        raise ValueError(
            "Invalid instrument_type found."
        )

    print(f"Accounts:              {len(accounts):,}")
    print(f"Devices:               {len(devices):,}")
    print(f"Addresses:             {len(addresses):,}")
    print(f"Phones:                {len(phones):,}")
    print(
        f"Payment instruments:   "
        f"{len(instruments):,}"
    )

    print()
    print("Duplicate IDs:         0")
    print("Missing values:        0")
    print("Timestamp violations:  0")
    print("Schema errors:         0")

    print("=" * 55)
    print("DAY-1 VALIDATION PASSED")
    print("=" * 55)


if __name__ == "__main__":
    validate_entities()