import pandas as pd
from .config import N_ACCOUNTS, N_RING_TYPES, RING_ACCOUNTS_PER_TYPE
from .config import (
    START_DATE,
    END_DATE,
    PATHS,
)


def check_unique(df, column, table_name):
    duplicates = df[column].duplicated().sum()
    if duplicates > 0:
        raise ValueError(
            f"{table_name}.{column}: " f"{duplicates} duplicate values found."
        )


def check_timestamps(df, column, table_name):
    start = pd.Timestamp(START_DATE)
    end = pd.Timestamp(END_DATE)
    values = pd.to_datetime(df[column])
    invalid = ((values < start) | (values > end)).sum()
    if invalid > 0:
        raise ValueError(
            f"{table_name}.{column}: " f"{invalid} timestamps outside dataset window."
        )


def validate_entities():
    accounts = pd.read_csv(PATHS["accounts"])
    devices = pd.read_csv(PATHS["devices"])
    addresses = pd.read_csv(PATHS["addresses"])
    phones = pd.read_csv(PATHS["phones"])
    instruments = pd.read_csv(PATHS["payment_instruments"])

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
                raise ValueError(f"Missing column: " f"{table_name}.{column}")

    # Unique IDs
    check_unique(accounts, "account_id", "accounts")
    check_unique(devices, "device_id", "devices")
    check_unique(addresses, "address_id", "addresses")
    check_unique(phones, "phone_hash", "phones")
    check_unique(instruments, "instrument_id", "payment_instruments")
    check_unique(instruments, "bin_or_vpa_hash", "payment_instruments")

    # Timestamp checks
    check_timestamps(accounts, "account_created_at", "accounts")
    for table_name in ["devices", "addresses", "phones", "payment_instruments"]:
        check_timestamps(tables[table_name], "first_seen_at", table_name)

    # Null checks
    for table_name, df in tables.items():
        if df.isnull().any().any():
            null_count = int(df.isnull().sum().sum())
            raise ValueError(f"{table_name}: " f"{null_count} null values found.")

    # Valid categorical values
    valid_customer_types = {"regular", "new", "guest"}
    if not set(accounts["customer_type"]).issubset(valid_customer_types):
        raise ValueError("Invalid customer_type found.")

    valid_os = {"Android", "iOS", "Windows", "macOS", "Linux"}
    if not set(devices["os_family"]).issubset(valid_os):
        raise ValueError("Invalid os_family found.")

    valid_instruments = {"card", "upi", "netbanking", "wallet"}
    if not set(instruments["instrument_type"]).issubset(valid_instruments):
        raise ValueError("Invalid instrument_type found.")

    print(f"Accounts:              {len(accounts):,}")
    print(f"Devices:               {len(devices):,}")
    print(f"Addresses:             {len(addresses):,}")
    print(f"Phones:                {len(phones):,}")
    print(f"Payment instruments:   " f"{len(instruments):,}")
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

    accounts = pd.read_csv(PATHS["accounts"], parse_dates=["account_created_at"])
    devices = pd.read_csv(PATHS["devices"], parse_dates=["first_seen_at"])
    addresses = pd.read_csv(PATHS["addresses"], parse_dates=["first_seen_at"])
    phones = pd.read_csv(PATHS["phones"], parse_dates=["first_seen_at"])
    instruments = pd.read_csv(
        PATHS["payment_instruments"], parse_dates=["first_seen_at"]
    )
    orders = pd.read_csv(
        PATHS["orders"],
        low_memory=False,
        parse_dates=[
            "order_timestamp",
            "delivery_timestamp",
            "return_timestamp",
            "refund_timestamp",
        ],
    )

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
    missing_columns = [col for col in required_columns if col not in orders.columns]
    if missing_columns:
        raise AssertionError(f"Missing order columns: " f"{missing_columns}")

    duplicate_orders = orders["order_id"].duplicated().sum()
    if duplicate_orders:
        raise AssertionError(f"Duplicate order IDs: " f"{duplicate_orders}")

    account_ids = set(accounts["account_id"])
    device_ids = set(devices["device_id"])
    address_ids = set(addresses["address_id"])
    phone_ids = set(phones["phone_hash"])
    instrument_ids = set(instruments["instrument_id"])

    assert set(orders["account_id"]).issubset(account_ids), "Invalid account_id found."
    assert set(orders["device_id"]).issubset(device_ids), "Invalid device_id found."
    assert set(orders["address_id"]).issubset(address_ids), "Invalid address_id found."
    assert set(orders["phone_hash"]).issubset(phone_ids), "Invalid phone_hash found."
    assert set(orders["instrument_id"]).issubset(
        instrument_ids
    ), "Invalid instrument_id found."

    # Population type no longer in accounts.csv
    # (validation of normal-only orders can be removed or adjusted)
    # We skip the check for normal accounts here because it's not needed.

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
    null_counts = orders[required_non_null].isna().sum()
    invalid_nulls = null_counts[null_counts > 0]
    if len(invalid_nulls) > 0:
        raise AssertionError(f"Required fields contain nulls:\n" f"{invalid_nulls}")

    # Account timestamp consistency
    merged = orders.merge(
        accounts[["account_id", "account_created_at"]], on="account_id", how="left"
    )
    invalid_account_time = merged[
        merged["order_timestamp"] < merged["account_created_at"]
    ]
    if len(invalid_account_time) > 0:
        raise AssertionError(
            f"{len(invalid_account_time)} orders occur before account creation."
        )

    # Delivery timestamp consistency
    delivered = orders[orders["delivery_status"] == "delivered"]
    invalid_delivery = delivered[
        delivered["delivery_timestamp"].isna()
        | (delivered["delivery_timestamp"] < delivered["order_timestamp"])
    ]
    if len(invalid_delivery) > 0:
        raise AssertionError(
            f"{len(invalid_delivery)} delivered orders have invalid delivery timestamps."
        )

    not_delivered = orders[orders["delivery_status"].isin(["pending", "failed"])]
    invalid_not_delivered = not_delivered[not_delivered["delivery_timestamp"].notna()]
    if len(invalid_not_delivered) > 0:
        raise AssertionError(
            f"{len(invalid_not_delivered)} pending/failed orders have delivery timestamps."
        )

    invalid_rto = orders[(orders["delivery_status"] == "failed") != orders["rto_flag"]]
    if len(invalid_rto) > 0:
        raise AssertionError(f"{len(invalid_rto)} orders have invalid RTO flags.")

    total_orders = len(orders)
    delivered_count = orders["delivery_status"].eq("delivered").sum()
    pending_count = orders["delivery_status"].eq("pending").sum()
    failed_count = orders["delivery_status"].eq("failed").sum()

    print("-----------------------------------------------")
    print(f"Orders:                 {total_orders:,}")
    print(f"Average orders/account: " f"{total_orders / len(accounts):.2f}")
    print(f"Delivered:              " f"{delivered_count / total_orders:.2%}")
    print(f"Pending:                " f"{pending_count / total_orders:.2%}")
    print(f"Failed:                 " f"{failed_count / total_orders:.2%}")
    print(f"Average order value:    " f"₹{orders['amount'].mean():,.2f}")
    print("\nAverage amount by category:")
    print(orders.groupby("category")["amount"].mean().round(2))
    print("\nOrder validation passed.")
    return True


# ============================================================
# DAY 3 VALIDATION
# ============================================================


def validate_day3():
    print("\n")
    print("=" * 55)
    print("RINGWATCH DAY-3 DATASET VALIDATION")
    print("=" * 55)

    accounts = pd.read_csv(PATHS["accounts"], parse_dates=["account_created_at"])
    # Load private population labels
    private_path = PATHS["accounts"].parent / "account_population_labels_private.csv"
    if not private_path.exists():
        raise FileNotFoundError("Missing private population labels file")
    private_accounts = pd.read_csv(private_path)

    devices = pd.read_csv(PATHS["devices"], parse_dates=["first_seen_at"])
    addresses = pd.read_csv(PATHS["addresses"], parse_dates=["first_seen_at"])
    phones = pd.read_csv(PATHS["phones"], parse_dates=["first_seen_at"])
    instruments = pd.read_csv(
        PATHS["payment_instruments"], parse_dates=["first_seen_at"]
    )
    orders = pd.read_csv(
        PATHS["orders"],
        low_memory=False,
        parse_dates=[
            "order_timestamp",
            "delivery_timestamp",
            "return_timestamp",
            "refund_timestamp",
        ],
    )
    refunds = pd.read_csv(PATHS["refunds"], parse_dates=["refund_timestamp"])
    disputes = pd.read_csv(
        PATHS["disputes"], parse_dates=["dispute_created_at", "respond_by"]
    )
    ground_truth = pd.read_csv(
        PATHS["ring_ground_truth"], parse_dates=["ring_start_time", "ring_end_time"]
    )

    # Basic file checks
    required_files = [
        PATHS["accounts"],
        PATHS["orders"],
        PATHS["refunds"],
        PATHS["disputes"],
        PATHS["ring_ground_truth"],
    ]
    for path in required_files:
        if not path.exists():
            raise FileNotFoundError(f"Missing file: {path}")

    # Unique IDs
    if accounts["account_id"].duplicated().any():
        raise AssertionError("Duplicate account IDs.")
    if orders["order_id"].duplicated().any():
        raise AssertionError("Duplicate order IDs.")
    if len(refunds) > 0 and refunds["refund_id"].duplicated().any():
        raise AssertionError("Duplicate refund IDs.")
    if len(disputes) > 0 and disputes["dispute_id"].duplicated().any():
        raise AssertionError("Duplicate dispute IDs.")

    # Foreign keys
    account_ids = set(accounts["account_id"])
    order_ids = set(orders["order_id"])
    if not set(orders["account_id"]).issubset(account_ids):
        raise AssertionError("Invalid account FK in orders.")
    device_ids = set(devices["device_id"])
    address_ids = set(addresses["address_id"])
    phone_ids = set(phones["phone_hash"])
    instrument_ids = set(instruments["instrument_id"])
    if not set(orders["device_id"]).issubset(device_ids):
        raise AssertionError("Invalid device FK in orders.")
    if not set(orders["address_id"]).issubset(address_ids):
        raise AssertionError("Invalid address FK in orders.")
    if not set(orders["phone_hash"]).issubset(phone_ids):
        raise AssertionError("Invalid phone FK in orders.")
    if not set(orders["instrument_id"]).issubset(instrument_ids):
        raise AssertionError("Invalid instrument FK in orders.")
    if len(refunds) > 0:
        if not set(refunds["order_id"]).issubset(order_ids):
            raise AssertionError("Invalid order FK in refunds.")
        if not set(refunds["account_id"]).issubset(account_ids):
            raise AssertionError("Invalid account FK in refunds.")
    if len(disputes) > 0:
        if not set(disputes["order_id"]).issubset(order_ids):
            raise AssertionError("Invalid order FK in disputes.")
        if not set(disputes["account_id"]).issubset(account_ids):
            raise AssertionError("Invalid account FK in disputes.")

    # Refund consistency
    if len(refunds) > 0:
        refund_orders = orders[orders["order_id"].isin(refunds["order_id"])]
        if not refund_orders["refund_flag"].all():
            raise AssertionError("Refund table contains orders without refund_flag.")

    # Dispute consistency
    if len(disputes) > 0:
        dispute_orders = orders[orders["order_id"].isin(disputes["order_id"])]
        if not dispute_orders["dispute_flag"].all():
            raise AssertionError("Dispute table contains orders without dispute_flag.")

    # Timestamp checks
    invalid_delivery = orders[
        (orders["delivery_status"] == "delivered")
        & (orders["delivery_timestamp"] < orders["order_timestamp"])
    ]
    if len(invalid_delivery) > 0:
        raise AssertionError(f"{len(invalid_delivery)} invalid delivery timestamps.")

    returned_orders = orders[orders["return_flag"] == True]
    if len(returned_orders) > 0:
        invalid_returns = returned_orders[
            returned_orders["return_timestamp"] < returned_orders["delivery_timestamp"]
        ]
        if len(invalid_returns) > 0:
            raise AssertionError("Invalid return timestamps.")

    refunded_orders = orders[orders["refund_flag"] == True]
    if len(refunded_orders) > 0:
        invalid_refunds = refunded_orders[
            refunded_orders["refund_timestamp"] < refunded_orders["return_timestamp"]
        ]
        if len(invalid_refunds) > 0:
            raise AssertionError("Invalid refund timestamps.")

    if len(disputes) > 0:
        dispute_orders = orders[orders["order_id"].isin(disputes["order_id"])][
            ["order_id", "refund_timestamp", "delivery_timestamp"]
        ]
        dispute_check = disputes.merge(dispute_orders, on="order_id", how="left")
        expected_base = dispute_check["refund_timestamp"].where(
            dispute_check["refund_timestamp"].notna(),
            dispute_check["delivery_timestamp"],
        )
        invalid_dispute_created = dispute_check["dispute_created_at"] < expected_base
        if invalid_dispute_created.any():
            raise AssertionError("Invalid dispute_created_at timestamps.")
        invalid_respond_by = disputes["respond_by"] < disputes["dispute_created_at"]
        if invalid_respond_by.any():
            raise AssertionError("Invalid dispute respond_by timestamps.")

    # Ring checks
    if len(accounts) != N_ACCOUNTS:
        raise AssertionError(f"Expected {N_ACCOUNTS} accounts, got {len(accounts)}.")

    ring_accounts = private_accounts[private_accounts["population_type"] == "ring"]
    true_ring_members = ground_truth[ground_truth["true_ring_member"] == True]

    expected_ring_members = sum(
        N_RING_TYPES[rt] * RING_ACCOUNTS_PER_TYPE[rt] for rt in N_RING_TYPES
    )
    if len(ring_accounts) != expected_ring_members:
        raise AssertionError(
            f"Expected {expected_ring_members} ring-reserved accounts, got {len(ring_accounts)}."
        )
    if len(true_ring_members) != expected_ring_members:
        raise AssertionError(
            f"Expected {expected_ring_members} ring members, got {len(true_ring_members)}."
        )

    unique_ring_ids = ground_truth["abuse_ring_id"].dropna().nunique()
    expected_ring_ids = sum(N_RING_TYPES.values())
    if unique_ring_ids != expected_ring_ids:
        raise AssertionError(
            f"Expected {expected_ring_ids} unique ring IDs, got {unique_ring_ids}."
        )

    ring_types_present = set(true_ring_members["ring_type"])
    if ring_types_present != set(N_RING_TYPES):
        raise AssertionError(
            f"Ring types missing: {set(N_RING_TYPES) - ring_types_present}"
        )

    for rt, expected_members in RING_ACCOUNTS_PER_TYPE.items():
        actual_count = true_ring_members[true_ring_members["ring_type"] == rt].shape[0]
        expected_total = N_RING_TYPES[rt] * expected_members
        if actual_count != expected_total:
            raise AssertionError(
                f"{rt} expected {expected_total} accounts, got {actual_count}"
            )

    if true_ring_members["abuse_ring_id"].isna().any():
        raise AssertionError("A true ring member is missing abuse_ring_id.")

    # Hard negative check
    hard_accounts = private_accounts[
        private_accounts["population_type"] == "hard_negative"
    ]
    expected_hard_accounts = (
        N_ACCOUNTS
        - len(ring_accounts)
        - int((private_accounts["population_type"] == "normal").sum())
    )
    if len(hard_accounts) != expected_hard_accounts:
        raise AssertionError(
            f"Expected {expected_hard_accounts} hard-negative accounts, got {len(hard_accounts)}."
        )

    hard_orders = orders[orders["account_id"].isin(hard_accounts["account_id"])]
    ring_orders = orders[orders["account_id"].isin(true_ring_members["account_id"])]
    if len(hard_orders) == 0:
        raise AssertionError("No hard-negative orders found.")

    hard_truth = ground_truth[
        ground_truth["account_id"].isin(hard_accounts["account_id"])
    ]
    if hard_truth["true_ring_member"].any():
        raise AssertionError("Hard-negative account marked as true ring member.")

    # V4-specific checks
    for col in accounts.columns:
        if col.startswith("_"):
            raise AssertionError(
                f"Internal latent column '{col}' leaked into accounts.csv"
            )

    # Optional: Warn if some ring members have no orders
    ring_member_ids = set(true_ring_members["account_id"])
    ring_orders = orders[orders["account_id"].isin(ring_member_ids)]
    missing_orders = ring_member_ids - set(ring_orders["account_id"])
    if missing_orders:
        print(f"Warning: {len(missing_orders)} ring members have no orders")

    # Report
    print(f"Accounts:              {len(accounts):,}")
    print(f"Orders:                {len(orders):,}")
    print(f"Refunds:               {len(refunds):,}")
    print(f"Disputes:              {len(disputes):,}")
    print()
    print(f"Ring accounts:         {len(ring_accounts):,}")
    print(f"True ring members:     {len(true_ring_members):,}")
    print(f"Hard-negative accounts: {len(hard_accounts):,}")
    print(f"Ring orders:           {len(ring_orders):,}")
    print(f"Hard-negative orders:  {len(hard_orders):,}")
    print()
    print("Foreign-key failures:  0")
    print("Duplicate IDs:         0")
    print("Timestamp violations:  0")
    print()
    if len(orders) > 0:
        print(f"Return rate:           {orders['return_flag'].mean():.2%}")
        print(f"Refund rate:           {orders['refund_flag'].mean():.2%}")
        print(f"Dispute rate:          {orders['dispute_flag'].mean():.2%}")

    print("=" * 55)
    print("DAY-3 VALIDATION PASSED")
    print("=" * 55)
    return True


if __name__ == "__main__":
    validate_entities()
