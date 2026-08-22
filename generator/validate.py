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


def validate_orders():

    print("\nValidating orders...")

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

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required_columns = [
        "order_id",
        "account_id",
        "device_id",
        "address_id",
        "phone_hash",
        "instrument_id",
        "amount",
        "discount_amount",
        "category",
        "order_timestamp",
        "delivery_status",
        "delivery_timestamp",
        "rto_flag",
        "return_flag",
        "refund_flag",
        "dispute_flag",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in orders.columns
    ]

    if missing_columns:
        raise AssertionError(
            f"Missing order columns: "
            f"{missing_columns}"
        )

    # --------------------------------------------------------
    # Order ID uniqueness
    # --------------------------------------------------------

    duplicate_orders = (
        orders["order_id"].duplicated().sum()
    )

    if duplicate_orders:
        raise AssertionError(
            f"Duplicate order IDs: "
            f"{duplicate_orders}"
        )

    # --------------------------------------------------------
    # Foreign keys
    # --------------------------------------------------------

    account_ids = set(
        accounts["account_id"]
    )

    device_ids = set(
        devices["device_id"]
    )

    address_ids = set(
        addresses["address_id"]
    )

    phone_ids = set(
        phones["phone_hash"]
    )

    instrument_ids = set(
        instruments["instrument_id"]
    )

    assert set(orders["account_id"]).issubset(
        account_ids
    ), "Invalid account_id found."

    assert set(orders["device_id"]).issubset(
        device_ids
    ), "Invalid device_id found."

    assert set(orders["address_id"]).issubset(
        address_ids
    ), "Invalid address_id found."

    assert set(orders["phone_hash"]).issubset(
        phone_ids
    ), "Invalid phone_hash found."

    assert set(orders["instrument_id"]).issubset(
        instrument_ids
    ), "Invalid instrument_id found."

    # --------------------------------------------------------
    # CRITICAL: only normal accounts
    # --------------------------------------------------------

    account_population = accounts[
        [
            "account_id",
            "population_type",
        ]
    ]

    merged = orders.merge(
        account_population,
        on="account_id",
        how="left",
    )

    non_normal_orders = merged[
        merged["population_type"] != "normal"
    ]

    if len(non_normal_orders) > 0:
        raise AssertionError(
            f"Found {len(non_normal_orders)} "
            "orders belonging to ring/hard-negative "
            "accounts."
        )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    required_non_null = [
        "order_id",
        "account_id",
        "device_id",
        "address_id",
        "phone_hash",
        "instrument_id",
        "amount",
        "category",
        "order_timestamp",
        "delivery_status",
    ]

    null_counts = (
        orders[required_non_null]
        .isna()
        .sum()
    )

    invalid_nulls = (
        null_counts[null_counts > 0]
    )

    if len(invalid_nulls) > 0:
        raise AssertionError(
            f"Required fields contain nulls:\n"
            f"{invalid_nulls}"
        )

    # --------------------------------------------------------
    # Account timestamp consistency
    # --------------------------------------------------------

    merged = orders.merge(
        accounts[
            [
                "account_id",
                "account_created_at",
            ]
        ],
        on="account_id",
        how="left",
    )

    invalid_account_time = merged[
        merged["order_timestamp"]
        < merged["account_created_at"]
    ]

    if len(invalid_account_time) > 0:
        raise AssertionError(
            f"{len(invalid_account_time)} orders "
            "occur before account creation."
        )

    # --------------------------------------------------------
    # Delivery timestamp consistency
    # --------------------------------------------------------

    delivered = orders[
        orders["delivery_status"] == "delivered"
    ]

    invalid_delivery = delivered[
        delivered["delivery_timestamp"].isna()
        |
        (
            delivered["delivery_timestamp"]
            < delivered["order_timestamp"]
        )
    ]

    if len(invalid_delivery) > 0:
        raise AssertionError(
            f"{len(invalid_delivery)} delivered "
            "orders have invalid delivery timestamps."
        )

    # Pending/failed orders must not have delivery timestamp.
    not_delivered = orders[
        orders["delivery_status"].isin(
            ["pending", "failed"]
        )
    ]

    invalid_not_delivered = (
        not_delivered[
            not_delivered["delivery_timestamp"].notna()
        ]
    )

    if len(invalid_not_delivered) > 0:
        raise AssertionError(
            f"{len(invalid_not_delivered)} "
            "pending/failed orders have delivery timestamps."
        )

    # --------------------------------------------------------
    # RTO consistency
    # --------------------------------------------------------

    invalid_rto = orders[
        (
            orders["delivery_status"] == "failed"
        )
        != orders["rto_flag"]
    ]

    if len(invalid_rto) > 0:
        raise AssertionError(
            f"{len(invalid_rto)} orders have "
            "invalid RTO flags."
        )

    # --------------------------------------------------------
    # Distribution report
    # --------------------------------------------------------

    total_orders = len(orders)

    delivered_count = (
        orders["delivery_status"]
        .eq("delivered")
        .sum()
    )

    pending_count = (
        orders["delivery_status"]
        .eq("pending")
        .sum()
    )

    failed_count = (
        orders["delivery_status"]
        .eq("failed")
        .sum()
    )

    print(
        "-----------------------------------------------"
    )

    print(
        f"Orders:                 {total_orders:,}"
    )

    print(
        f"Average orders/account: "
        f"{total_orders / len(accounts):.2f}"
    )

    print(
        f"Delivered:              "
        f"{delivered_count / total_orders:.2%}"
    )

    print(
        f"Pending:                "
        f"{pending_count / total_orders:.2%}"
    )

    print(
        f"Failed:                 "
        f"{failed_count / total_orders:.2%}"
    )

    print(
        f"Average order value:    "
        f"₹{orders['amount'].mean():,.2f}"
    )

    print(
        "\nAverage amount by category:"
    )

    print(
        orders.groupby("category")[
            "amount"
        ].mean().round(2)
    )

    print(
        "\nOrder validation passed."
    )

    return True



if __name__ == "__main__":
    validate_entities()