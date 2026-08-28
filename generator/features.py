import pandas as pd
import numpy as np

from itertools import combinations

from .features_config import (
    PREDICTION_CUTOFF,
    FEATURES_PATH,
    LEAKAGE_REPORT_PATH,
    PATHS,
)

# ============================================================
# CONSTANTS
# ============================================================

T = pd.Timestamp(PREDICTION_CUTOFF)


# ============================================================
# LOAD DATA
# ============================================================


def load_data():
    """
    Load all Day-3 datasets and explicitly normalize datetime columns.
    """

    accounts = pd.read_csv(
        PATHS["accounts"],
        low_memory=False,
    )

    orders = pd.read_csv(
        PATHS["orders"],
        low_memory=False,
    )

    refunds = pd.read_csv(
        PATHS["refunds"],
        low_memory=False,
    )

    disputes = pd.read_csv(
        PATHS["disputes"],
        low_memory=False,
    )

    devices = pd.read_csv(
        PATHS["devices"],
        low_memory=False,
    )

    addresses = pd.read_csv(
        PATHS["addresses"],
        low_memory=False,
    )

    phones = pd.read_csv(
        PATHS["phones"],
        low_memory=False,
    )

    instruments = pd.read_csv(
        PATHS["payment_instruments"],
        low_memory=False,
    )

    # ========================================================
    # EXPLICIT DATETIME NORMALIZATION
    # ========================================================

    datetime_columns = {
        "accounts": [
            "account_created_at",
        ],
        "orders": [
            "order_timestamp",
            "delivery_timestamp",
            "return_timestamp",
            "refund_timestamp",
            "dispute_created_at",
        ],
        "refunds": [
            "refund_timestamp",
        ],
        "disputes": [
            "dispute_created_at",
            "respond_by",
        ],
        "devices": [
            "first_seen_at",
        ],
        "addresses": [
            "first_seen_at",
        ],
        "phones": [
            "first_seen_at",
        ],
        "instruments": [
            "first_seen_at",
        ],
    }

    dataframes = {
        "accounts": accounts,
        "orders": orders,
        "refunds": refunds,
        "disputes": disputes,
        "devices": devices,
        "addresses": addresses,
        "phones": phones,
        "instruments": instruments,
    }

    for name, columns in datetime_columns.items():
        df = dataframes[name]

        for column in columns:
            if column in df.columns:
                df[column] = pd.to_datetime(
                    df[column],
                    errors="coerce",
                )

        dataframes[name] = df

    return (
        dataframes["accounts"],
        dataframes["orders"],
        dataframes["refunds"],
        dataframes["disputes"],
        dataframes["devices"],
        dataframes["addresses"],
        dataframes["phones"],
        dataframes["instruments"],
    )


# ============================================================
# FILTER TO CUTOFF
# ============================================================


def filter_to_cutoff(
    accounts,
    orders,
    refunds,
    disputes,
    devices,
    addresses,
    phones,
    instruments,
):
    T = pd.Timestamp(PREDICTION_CUTOFF)
    original_order_count = len(orders)

    filtered_orders = orders[
        orders["order_timestamp"] <= T
    ].copy()

    filtered_refunds = refunds[refunds["refund_timestamp"] <= T].copy()

    filtered_disputes = disputes[disputes["dispute_created_at"] <= T].copy()

    filtered_devices = devices[devices["first_seen_at"] <= T].copy()

    filtered_addresses = addresses[addresses["first_seen_at"] <= T].copy()

    filtered_phones = phones[phones["first_seen_at"] <= T].copy()

    filtered_instruments = instruments[instruments["first_seen_at"] <= T].copy()

    # Accounts are retained even if they have no activity.
    filtered_accounts = accounts.copy()

    print("\n===================================")
    print("DAY 4 — CUTOFF FILTERING")
    print("===================================")

    print(f"Prediction cutoff:        {T}")
    print(f"Orders before filtering:  {original_order_count}")
    print(f"Orders after filtering:   {len(filtered_orders)}")
    print(f"Refunds after filtering:  {len(filtered_refunds)}")
    print(f"Disputes after filtering: {len(filtered_disputes)}")

    # Safety checks
    if len(filtered_orders) > 0:
        assert filtered_orders["order_timestamp"].max() <= T

    if len(filtered_refunds) > 0:
        assert filtered_refunds["refund_timestamp"].max() <= T

    if len(filtered_disputes) > 0:
        assert filtered_disputes["dispute_created_at"].max() <= T

    return (
        filtered_accounts,
        filtered_orders,
        filtered_refunds,
        filtered_disputes,
        filtered_devices,
        filtered_addresses,
        filtered_phones,
        filtered_instruments,
        original_order_count,
    )


# ============================================================
# DELIVERY STATUS AS OF T
# ============================================================


def compute_delivery_status(orders):
    """
    Recompute delivery status as observed at T.

    An order delivered after T must NOT be considered delivered.
    """

    orders = orders.copy()

    def determine_status(row):
        original_status = row["delivery_status"]
        delivery_timestamp = row["delivery_timestamp"]

        # Failed order with no delivery timestamp
        if original_status == "failed":
            return "failed"

        # Pending order with no delivery timestamp
        if pd.isna(delivery_timestamp):
            return "pending"

        # Delivered by cutoff
        if delivery_timestamp <= T:
            return "delivered"

        # Delivery happens after cutoff
        return "pending"

    orders["status_as_of_t"] = orders.apply(
        determine_status,
        axis=1,
    )

    return orders


# ============================================================
# BASIC BEHAVIORAL FEATURES
# ============================================================


def build_behavioral_features(
    accounts,
    orders,
    refunds,
    disputes,
):
    """
    Build account-level behavioral features using only
    pre-T observable events.
    """

    orders = compute_delivery_status(orders)

    features = accounts[["account_id", "account_created_at"]].copy()

    # --------------------------------------------------------
    # ORDER FEATURES
    # --------------------------------------------------------

    order_group = orders.groupby("account_id")

    order_features = order_group.agg(
        total_orders=("order_id", "count"),
        total_amount=("amount", "sum"),
        avg_order_value=("amount", "mean"),
        distinct_devices=("device_id", "nunique"),
        distinct_addresses=("address_id", "nunique"),
        distinct_phones=("phone_hash", "nunique"),
        distinct_payment_instruments=(
            "instrument_id",
            "nunique",
        ),
    ).reset_index()

    features = features.merge(
        order_features,
        on="account_id",
        how="left",
    )

    # --------------------------------------------------------
    # DELIVERY STATUS
    # --------------------------------------------------------

    delivery_counts = orders.pivot_table(
        index="account_id",
        columns="status_as_of_t",
        values="order_id",
        aggfunc="count",
        fill_value=0,
    ).reset_index()

    delivery_counts.columns.name = None

    rename_map = {
        "delivered": "total_delivered_orders",
        "failed": "total_failed_orders",
        "pending": "total_pending_orders",
    }

    delivery_counts = delivery_counts.rename(columns=rename_map)

    features = features.merge(
        delivery_counts,
        on="account_id",
        how="left",
    )

    # --------------------------------------------------------
    # COUPON + DISCOUNT
    # --------------------------------------------------------

    orders["has_coupon"] = orders["coupon_code"].notna() & (
        orders["coupon_code"].astype(str).str.strip() != ""
    )

    orders["discount_ratio"] = np.where(
        orders["amount"] > 0,
        orders["discount_amount"] / orders["amount"],
        0.0,
    )

    coupon_features = (
        orders.groupby("account_id")
        .agg(
            coupon_usage_rate=("has_coupon", "mean"),
            discount_dependency_score=(
                "discount_ratio",
                "mean",
            ),
        )
        .reset_index()
    )

    features = features.merge(
        coupon_features,
        on="account_id",
        how="left",
    )

    # Number of distinct coupon codes used
    distinct_coupons = orders[orders["coupon_code"].notna()].groupby("account_id")["coupon_code"].nunique().rename("distinct_coupon_count")
    features = features.merge(distinct_coupons, on="account_id", how="left")

    # Maximum discount ratio
    max_discount = orders.groupby("account_id")["discount_ratio"].max().rename("max_discount_ratio")
    features = features.merge(max_discount, on="account_id", how="left")

    # Rare coupon count (coupons used by <10 accounts overall)
    coupon_counts = orders[orders["coupon_code"].notna()]["coupon_code"].value_counts()
    rare_coupons = set(coupon_counts[coupon_counts < 10].index)
    orders["is_rare_coupon"] = orders["coupon_code"].isin(rare_coupons)
    rare_coupon_count = orders.groupby("account_id")["is_rare_coupon"].sum().rename("rare_coupon_count")
    features = features.merge(rare_coupon_count, on="account_id", how="left")

    # Fill NaN
    features[["distinct_coupon_count", "max_discount_ratio", "rare_coupon_count"]] = features[
        ["distinct_coupon_count", "max_discount_ratio", "rare_coupon_count"]
    ].fillna(0)

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    valid_returns = orders[
        (orders["return_flag"] == True)
        & orders["return_timestamp"].notna()
        & (orders["return_timestamp"] <= T)
    ].copy()

    return_features = (
        valid_returns.groupby("account_id")
        .agg(
            total_returns=("order_id", "count"),
            avg_return_lag_hours=(
                "return_lag_hours",
                "mean",
            ),
        )
        .reset_index()
    )

    features = features.merge(
        return_features,
        on="account_id",
        how="left",
    )

    # --------------------------------------------------------
    # REFUNDS
    # --------------------------------------------------------

    valid_refunds = refunds[refunds["refund_timestamp"] <= T].copy()

    refund_features = (
        valid_refunds.groupby("account_id")
        .agg(
            total_refunds=("refund_id", "count"),
            total_refund_amount=(
                "refund_amount",
                "sum",
            ),
        )
        .reset_index()
    )

    features = features.merge(
        refund_features,
        on="account_id",
        how="left",
    )

    # --------------------------------------------------------
    # DISPUTES
    # --------------------------------------------------------

    valid_disputes = disputes[disputes["dispute_created_at"] <= T].copy()

    dispute_features = (
        valid_disputes.groupby("account_id")
        .agg(
            total_disputes=("dispute_id", "count"),
        )
        .reset_index()
    )

    features = features.merge(
        dispute_features,
        on="account_id",
        how="left",
    )

    # --------------------------------------------------------
    # DEFAULTS
    # --------------------------------------------------------

    numeric_defaults = [
        "total_orders",
        "total_amount",
        "avg_order_value",
        "total_delivered_orders",
        "total_failed_orders",
        "total_pending_orders",
        "distinct_devices",
        "distinct_addresses",
        "distinct_phones",
        "distinct_payment_instruments",
        "coupon_usage_rate",
        "discount_dependency_score",
        "total_returns",
        "avg_return_lag_hours",
        "total_refunds",
        "total_refund_amount",
        "total_disputes",
    ]

    for column in numeric_defaults:
        if column not in features.columns:
            features[column] = 0

        features[column] = features[column].fillna(0)

    # --------------------------------------------------------
    # RATES
    # --------------------------------------------------------

    features["return_rate"] = np.where(
        features["total_delivered_orders"] > 0,
        features["total_returns"] / features["total_delivered_orders"],
        0.0,
    )

    features["refund_rate"] = np.where(
        features["total_orders"] > 0,
        features["total_refunds"] / features["total_orders"],
        0.0,
    )

    features["dispute_rate"] = np.where(
        features["total_orders"] > 0,
        features["total_disputes"] / features["total_orders"],
        0.0,
    )

    return features, orders


# ============================================================
# TEMPORAL FEATURES
# ============================================================


def build_temporal_features(
    features,
    accounts,
    orders,
    refunds,
):
    """
    Build time-window and burst features relative to T.
    """

    features = features.copy()

    # --------------------------------------------------------
    # ACCOUNT AGE
    # --------------------------------------------------------

    features["account_age_days"] = (
        T - features["account_created_at"]
    ).dt.total_seconds() / 86400

    features["account_age_days"] = features["account_age_days"].clip(lower=0)

    # --------------------------------------------------------
    # ORDER WINDOWS
    # --------------------------------------------------------

    order_windows = {
        "orders_last_24h": T - pd.Timedelta(hours=24),
        "orders_last_7d": T - pd.Timedelta(days=7),
        "orders_last_30d": T - pd.Timedelta(days=30),
    }

    for column, start_time in order_windows.items():

        mask = (orders["order_timestamp"] > start_time) & (
            orders["order_timestamp"] <= T
        )

        counts = orders.loc[mask].groupby("account_id").size().reset_index(name=column)

        features = features.merge(
            counts,
            on="account_id",
            how="left",
        )

    # --------------------------------------------------------
    # REFUND WINDOWS
    # --------------------------------------------------------

    refund_windows = {
        "refunds_last_24h": T - pd.Timedelta(hours=24),
        "refunds_last_7d": T - pd.Timedelta(days=7),
        "refunds_last_30d": T - pd.Timedelta(days=30),
    }

    for column, start_time in refund_windows.items():

        mask = (refunds["refund_timestamp"] > start_time) & (
            refunds["refund_timestamp"] <= T
        )

        counts = refunds.loc[mask].groupby("account_id").size().reset_index(name=column)

        features = features.merge(
            counts,
            on="account_id",
            how="left",
        )

    # --------------------------------------------------------
    # 30-DAY RETURN RATE
    # --------------------------------------------------------

    start_30d = T - pd.Timedelta(days=30)

    recent_orders = orders[
        (orders["order_timestamp"] > start_30d) & (orders["order_timestamp"] <= T)
    ].copy()

    recent_returns = recent_orders[
        (recent_orders["return_flag"] == True)
        & recent_orders["return_timestamp"].notna()
        & (recent_orders["return_timestamp"] <= T)
    ]

    recent_order_counts = (
        recent_orders.groupby("account_id")
        .size()
        .reset_index(name="recent_order_count")
    )

    recent_return_counts = (
        recent_returns.groupby("account_id")
        .size()
        .reset_index(name="recent_return_count")
    )

    features = features.merge(
        recent_order_counts,
        on="account_id",
        how="left",
    )

    features = features.merge(
        recent_return_counts,
        on="account_id",
        how="left",
    )

    features["recent_order_count"] = features["recent_order_count"].fillna(0)

    features["recent_return_count"] = features["recent_return_count"].fillna(0)

    features["return_rate_last_30d"] = np.where(
        features["recent_order_count"] > 0,
        features["recent_return_count"] / features["recent_order_count"],
        0.0,
    )

    features.drop(
        columns=[
            "recent_order_count",
            "recent_return_count",
        ],
        inplace=True,
    )

    # --------------------------------------------------------
    # DEFAULT WINDOW COUNTS
    # --------------------------------------------------------

    window_columns = [
        "orders_last_24h",
        "refunds_last_24h",
        "orders_last_7d",
        "refunds_last_7d",
        "orders_last_30d",
        "refunds_last_30d",
    ]

    for column in window_columns:
        if column not in features.columns:
            features[column] = 0

        features[column] = features[column].fillna(0)

    # ---- New temporal interaction features ----
    # Time between first and last order
    order_times = orders.groupby("account_id")["order_timestamp"].agg(["min", "max"]).reset_index()
    order_times.columns = ["account_id", "first_order_time", "last_order_time"]
    features = features.merge(order_times, on="account_id", how="left")
    features["account_lifetime_days"] = (features["last_order_time"] - features["first_order_time"]).dt.total_seconds() / 86400
    features.drop(columns=["first_order_time", "last_order_time"], inplace=True)

    # Average time between orders (for accounts with >1 order)
    orders_sorted = orders.sort_values(["account_id", "order_timestamp"])
    orders_sorted["order_diff"] = orders_sorted.groupby("account_id")["order_timestamp"].diff()
    avg_order_gap = orders_sorted.groupby("account_id")["order_diff"].mean().rename("avg_order_gap_days").reset_index()
    avg_order_gap["avg_order_gap_days"] = avg_order_gap["avg_order_gap_days"] / pd.Timedelta(days=1)
    features = features.merge(avg_order_gap, on="account_id", how="left")

    # Ratio of orders in last 7 days vs total orders
    features["recent_activity_ratio"] = features["orders_last_7d"] / features["total_orders"].clip(lower=1)

    # Hour-of-day distribution: fraction of orders in evening (18-22)
    orders["hour"] = orders["order_timestamp"].dt.hour
    evening_ratio = orders.groupby("account_id")["hour"].apply(lambda x: (x.between(18, 22)).mean()).rename("evening_order_ratio").reset_index()
    features = features.merge(evening_ratio, on="account_id", how="left")

    # Fill NaNs with 0
    features[["account_lifetime_days", "avg_order_gap_days", "recent_activity_ratio", "evening_order_ratio"]] = features[
        ["account_lifetime_days", "avg_order_gap_days", "recent_activity_ratio", "evening_order_ratio"]
    ].fillna(0)    

    # --------------------------------------------------------
    # BURST SCORE
    # --------------------------------------------------------

    daily_orders_30d = features["orders_last_30d"] / 30.0

    daily_refunds_30d = features["refunds_last_30d"] / 30.0

    features["transaction_burst_score"] = features[
        "orders_last_24h"
    ] / daily_orders_30d.clip(lower=1.0)

    features["refund_burst_score"] = features[
        "refunds_last_24h"
    ] / daily_refunds_30d.clip(lower=1.0)

    # --------------------------------------------------------
    # ACCOUNT CREATION BURST
    # --------------------------------------------------------

    cutoff_accounts = accounts[accounts["account_created_at"] <= T].copy()

    creation_times = cutoff_accounts[["account_id", "account_created_at"]].dropna()

    burst_counts = []

    for _, account in creation_times.iterrows():

        lower = account["account_created_at"] - pd.Timedelta(hours=1)

        upper = account["account_created_at"] + pd.Timedelta(hours=1)

        count = (
            (creation_times["account_created_at"] >= lower)
            & (creation_times["account_created_at"] <= upper)
            & (creation_times["account_id"] != account["account_id"])
        ).sum()

        burst_counts.append(
            {
                "account_id": account["account_id"],
                "account_creation_burst_score": int(count),
            }
        )

    creation_burst_df = pd.DataFrame(burst_counts)

    features = features.merge(
        creation_burst_df,
        on="account_id",
        how="left",
    )

    features["account_creation_burst_score"] = features[
        "account_creation_burst_score"
    ].fillna(0)

    return features


# ============================================================
# IDENTITY REUSE FEATURES
# ============================================================


def build_identity_features(
    features,
    orders,
):
    """
    Build account-to-account identity reuse features
    using only entities observed through pre-T orders.
    """

    features = features.copy()

    entity_columns = {
        "device_id": "device",
        "address_id": "address",
        "phone_hash": "phone",
        "instrument_id": "instrument",
    }

    # --------------------------------------------------------
    # ENTITY → ACCOUNTS
    # --------------------------------------------------------

    entity_account_maps = {}

    for entity_column, prefix in entity_columns.items():

        mapping = (
            orders[
                [
                    "account_id",
                    entity_column,
                ]
            ]
            .dropna()
            .drop_duplicates()
            .groupby(entity_column)["account_id"]
            .apply(set)
            .to_dict()
        )

        entity_account_maps[entity_column] = mapping

    # --------------------------------------------------------
    # ACCOUNT-LEVEL IDENTITY FEATURES
    # --------------------------------------------------------

    account_records = []

    for account_id, account_orders in orders.groupby("account_id"):

        record = {"account_id": account_id}

        # Store the accounts sharing each entity type
        entity_sets = {}

        for entity_column, prefix in entity_columns.items():

            entities = account_orders[entity_column].dropna().unique()

            reuse_counts = []

            shared_accounts = set()

            for entity in entities:

                users = entity_account_maps[entity_column].get(entity, set())

                reuse_counts.append(len(users))

                shared_accounts.update(users - {account_id})

            if reuse_counts:
                average_reuse = float(np.mean(reuse_counts))
            else:
                average_reuse = 0.0

            record[f"accounts_per_{prefix}"] = average_reuse

            record[f"shared_{prefix}_count"] = len(shared_accounts)

            # Keep the actual shared-account set for enhanced features
            entity_sets[prefix] = shared_accounts

        # --------------------------------------------------------
        # ENHANCED SHARING FEATURES
        # --------------------------------------------------------

        # Accounts sharing both a device AND an address
        record["has_shared_device_and_address"] = int(
            bool(
                entity_sets["device"]
                & entity_sets["address"]
            )
        )

        # Accounts sharing both a payment instrument AND a phone
        record["has_shared_payment_and_phone"] = int(
            bool(
                entity_sets["instrument"]
                & entity_sets["phone"]
            )
        )

        # Number of entity types that have at least one shared account
        record["shared_entity_types_count"] = sum(
            len(shared_set) > 0
            for shared_set in entity_sets.values()
        )

        account_records.append(record)

    identity_df = pd.DataFrame(account_records)

    features = features.merge(
        identity_df,
        on="account_id",
        how="left",
    )

    # --------------------------------------------------------
    # SHARED IP PREFIX
    # --------------------------------------------------------

    # Attach IP prefix to each order through device_id.
    device_ip_map = orders[
        [
            "device_id",
        ]
    ].drop_duplicates()

    # We need the actual devices table data, but IP is already
    # represented in the orders through device IDs. This mapping
    # is populated by merging in main().
    return features


# ============================================================
# SHARED IP FEATURE
# ============================================================


def build_shared_ip_features(
    features,
    orders,
    devices,
):
    """
    Count other accounts sharing an IP prefix where at least
    one order pair occurred within 24 hours.
    """

    features = features.copy()

    device_ip = devices[
        [
            "device_id",
            "ip_prefix",
        ]
    ].drop_duplicates()

    orders_with_ip = orders.merge(
        device_ip,
        on="device_id",
        how="left",
    )

    shared_ip_counts = {}

    for ip_prefix, group in orders_with_ip.groupby("ip_prefix"):

        if pd.isna(ip_prefix):
            continue

        accounts_data = {}

        for account_id, account_orders in group.groupby("account_id"):
            accounts_data[account_id] = (
                account_orders["order_timestamp"].sort_values().tolist()
            )

        account_ids = list(accounts_data.keys())

        for account_a, account_b in combinations(
            account_ids,
            2,
        ):

            found_close_pair = False

            for time_a in accounts_data[account_a]:
                for time_b in accounts_data[account_b]:

                    if abs(time_a - time_b) <= pd.Timedelta(hours=24):

                        found_close_pair = True
                        break

                if found_close_pair:
                    break

            if found_close_pair:

                shared_ip_counts.setdefault(
                    account_a,
                    set(),
                ).add(account_b)

                shared_ip_counts.setdefault(
                    account_b,
                    set(),
                ).add(account_a)

    ip_records = [
        {
            "account_id": account_id,
            "shared_ip_prefix_count": len(accounts),
        }
        for account_id, accounts in shared_ip_counts.items()
    ]

    ip_df = pd.DataFrame(ip_records)

    if len(ip_df) > 0:

        features = features.drop(
            columns=["shared_ip_prefix_count"],
            errors="ignore",
        )

        features = features.merge(
            ip_df,
            on="account_id",
            how="left",
        )

    features["shared_ip_prefix_count"] = features["shared_ip_prefix_count"].fillna(0)

    return features


# ============================================================
# FINAL CLEANUP
# ============================================================


def finalize_features(features):
    """
    Clean and validate final Day-4 feature matrix.
    """

    features = features.copy()

    # Remove generator-only information.
    forbidden_columns = [
        "population_type",
        "abuse_ring_id",
        "true_ring_member",
        "ring_type",
        "ring_start_time",
        "ring_end_time",
    ]

    features = features.drop(
        columns=forbidden_columns,
        errors="ignore",
    )

    # Account creation timestamp is used to derive
    # account_age_days and should not remain as a feature.
    features = features.drop(
        columns=["account_created_at"],
        errors="ignore",
    )

    # Replace infinities.
    features = features.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    # Numeric columns.
    numeric_columns = features.select_dtypes(include=[np.number]).columns

    features[numeric_columns] = features[numeric_columns].fillna(0)

    # Ensure exactly one row per account.
    assert features["account_id"].is_unique

    # Ensure no missing values.
    assert features.isna().sum().sum() == 0

    

    # Sanity check:
    # return rate should not exist for accounts with
    # zero delivered orders.
    invalid_return_rate = (
        (features["total_delivered_orders"] == 0) & (features["return_rate"] > 0)
    ).sum()

    assert invalid_return_rate == 0

    return features


# ============================================================
# LEAKAGE REPORT
# ============================================================


def write_leakage_report(
    original_order_count,
    filtered_orders,
    filtered_refunds,
    filtered_disputes,
    features,
):
    """
    Write feature-only leakage report.
    """

    if len(filtered_orders) > 0:
        max_order_timestamp = filtered_orders["order_timestamp"].max()
    else:
        max_order_timestamp = "N/A"

    if len(filtered_refunds) > 0:
        max_refund_timestamp = filtered_refunds["refund_timestamp"].max()
    else:
        max_refund_timestamp = "N/A"

    if len(filtered_disputes) > 0:
        max_dispute_timestamp = filtered_disputes["dispute_created_at"].max()
    else:
        max_dispute_timestamp = "N/A"

    future_orders = original_order_count - len(filtered_orders)

    report = f"""
RingWatch — Day 4 Feature Leakage Report
==========================================

Prediction cutoff:
{T}

Max order timestamp used:
{max_order_timestamp}

Max refund timestamp used:
{max_refund_timestamp}

Max dispute timestamp used:
{max_dispute_timestamp}

Orders after T excluded:
{future_orders}

Refunds after T excluded:
Not included in filtered refund dataset

Disputes after T excluded:
Not included in filtered dispute dataset

Ground truth used:
NO

population_type used:
NO

Feature matrix rows:
{len(features)}

Feature matrix columns:
{len(features.columns)}

Missing values:
{int(features.isna().sum().sum())}

Forbidden columns present:
NO

LEAKAGE CHECK:
PASSED
"""

    with open(
        LEAKAGE_REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(report.strip() + "\n")


# ============================================================
# MAIN
# ============================================================


def main():

    print("\n===================================")
    print("RINGWATCH DAY 4")
    print("CUTOFF-AWARE FEATURE ENGINEERING")
    print("===================================")

    (
        accounts,
        orders,
        refunds,
        disputes,
        devices,
        addresses,
        phones,
        instruments,
    ) = load_data()

    (
        accounts,
        orders,
        refunds,
        disputes,
        devices,
        addresses,
        phones,
        instruments,
        original_order_count,
    ) = filter_to_cutoff(
        accounts,
        orders,
        refunds,
        disputes,
        devices,
        addresses,
        phones,
        instruments,
    )

    # --------------------------------------------------------
    # Behavioral features
    # --------------------------------------------------------

    print("\nBuilding behavioral features...")

    features, orders = build_behavioral_features(
        accounts,
        orders,
        refunds,
        disputes,
    )

    # --------------------------------------------------------
    # Temporal features
    # --------------------------------------------------------

    print("Building temporal features...")

    features = build_temporal_features(
        features,
        accounts,
        orders,
        refunds,
    )

    # --------------------------------------------------------
    # Identity reuse
    # --------------------------------------------------------

    print("Building identity-reuse features...")

    features = build_identity_features(
        features,
        orders,
    )

    # --------------------------------------------------------
    # Shared IP
    # --------------------------------------------------------

    print("Building shared-IP features...")

    features = build_shared_ip_features(
        features,
        orders,
        devices,
    )

    # --------------------------------------------------------
    # Finalize
    # --------------------------------------------------------

    print("Finalizing feature matrix...")

    features = finalize_features(features)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    features.to_csv(
        FEATURES_PATH,
        index=False,
    )

    # --------------------------------------------------------
    # Validation statistics
    # --------------------------------------------------------

    print("\n===================================")
    print("DAY 4 FEATURE VALIDATION")
    print("===================================")

    print(f"Feature rows:              {len(features)}")

    print(f"Feature columns:           {len(features.columns)}")

    print(f"Missing values:            " f"{int(features.isna().sum().sum())}")

    print(f"Mean total orders:         " f"{features['total_orders'].mean():.2f}")

    print(f"Mean return rate:          " f"{features['return_rate'].mean():.4f}")

    print(f"Mean refund rate:          " f"{features['refund_rate'].mean():.4f}")

    print(f"Mean dispute rate:         " f"{features['dispute_rate'].mean():.4f}")

    print(
        f"Mean shared devices:       " f"{features['shared_device_count'].mean():.2f}"
    )

    print(f"Max shared devices:        " f"{features['shared_device_count'].max():.0f}")

    # --------------------------------------------------------
    # Leakage report
    # --------------------------------------------------------

    write_leakage_report(
        original_order_count,
        orders,
        refunds,
        disputes,
        features,
    )

    print("\n===================================")
    print("DAY 4 COMPLETED")
    print("===================================")

    print(f"Features saved to:\n" f"{FEATURES_PATH}")

    print(f"Leakage report saved to:\n" f"{LEAKAGE_REPORT_PATH}")

    print("\nLEAKAGE CHECK: PASSED")


if __name__ == "__main__":
    main()
