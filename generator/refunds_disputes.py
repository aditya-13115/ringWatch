import numpy as np
import pandas as pd

from .config import PATHS, SEED
from .ids import (
    make_refund_id,
    make_dispute_id,
)

rng = np.random.default_rng(SEED)


# ============================================================
# LOAD
# ============================================================


def load_data():

    orders = pd.read_csv(
        PATHS["orders"],
        parse_dates=[
            "order_timestamp",
            "delivery_timestamp",
            "return_timestamp",
            "refund_timestamp",
        ],
    )

    accounts = pd.read_csv(PATHS["accounts"])

    return orders, accounts


# ============================================================
# BASELINE NORMAL EVENTS
# ============================================================


def apply_normal_behavior(
    orders,
    accounts,
):
    population = accounts[
        [
            "account_id",
            "population_type",
        ]
    ]

    orders = orders.merge(
        population,
        on="account_id",
        how="left",
    )

    # --------------------------------------------------------
    # Normalize timestamp columns
    # --------------------------------------------------------
    timestamp_columns = [
        "order_timestamp",
        "delivery_timestamp",
        "return_timestamp",
        "refund_timestamp",
        "dispute_created_at",
    ]

    for column in timestamp_columns:
        if column in orders.columns:
            orders[column] = pd.to_datetime(
                orders[column],
                errors="coerce",
            )

    normal_mask = orders["population_type"] == "normal"
    delivered_mask = orders["delivery_status"] == "delivered"
    eligible = normal_mask & delivered_mask

    # --------------------------------------------------------
    # Return ~4%
    # --------------------------------------------------------

    return_mask = eligible & (rng.random(len(orders)) < 0.04)

    orders.loc[
        return_mask,
        "return_flag",
    ] = True

    return_indices = orders.index[return_mask]

    for idx in return_indices:
        delivery_time = orders.loc[
            idx,
            "delivery_timestamp",
        ]

        # Safety check
        if pd.isna(delivery_time):
            continue

        return_time = delivery_time + pd.Timedelta(days=int(rng.integers(2, 6)))

        orders.loc[
            idx,
            "return_reason_code",
        ] = rng.choice(
            [
                "size_fit",
                "not_as_described",
                "changed_mind",
            ]
        )

        orders.loc[
            idx,
            "return_timestamp",
        ] = return_time

        orders.loc[
            idx,
            "return_lag_hours",
        ] = (return_time - delivery_time).total_seconds() / 3600

        # Refund follows return.
        orders.loc[
            idx,
            "refund_flag",
        ] = True

        orders.loc[
            idx,
            "refund_amount",
        ] = orders.loc[
            idx,
            "amount",
        ]

        orders.loc[
            idx,
            "refund_timestamp",
        ] = return_time + pd.Timedelta(hours=int(rng.integers(4, 24)))

    # --------------------------------------------------------
    # Dispute ~0.5%
    # --------------------------------------------------------

    dispute_mask = eligible & (rng.random(len(orders)) < 0.005)

    orders.loc[
        dispute_mask,
        "dispute_flag",
    ] = True

    dispute_indices = orders.index[dispute_mask]

    for idx in dispute_indices:
        refund_time = orders.loc[
            idx,
            "refund_timestamp",
        ]

        if pd.notna(refund_time):
            dispute_time = refund_time + pd.Timedelta(days=int(rng.integers(1, 4)))
        else:
            delivery_time = orders.loc[
                idx,
                "delivery_timestamp",
            ]

            if pd.isna(delivery_time):
                continue

            dispute_time = delivery_time + pd.Timedelta(days=int(rng.integers(2, 5)))

        orders.loc[
            idx,
            "dispute_created_at",
        ] = dispute_time

        orders.loc[
            idx,
            "dispute_phase",
        ] = rng.choice(
            [
                "retrieval",
                "pre_arbitration",
            ]
        )

        orders.loc[
            idx,
            "dispute_reason_code",
        ] = rng.choice(
            [
                "item_not_received",
                "duplicate_charge",
                "unauthorized_transaction",
            ]
        )

        orders.loc[
            idx,
            "dispute_reason_category",
        ] = "customer_dispute"

    orders = orders.drop(
        columns=[
            "population_type",
        ]
    )

    return orders


# ============================================================
# REFUNDS TABLE
# ============================================================


def generate_refunds(orders):

    rows = []

    refund_counter = 0

    refund_orders = orders[orders["refund_flag"] == True]

    for _, order in refund_orders.iterrows():

        refund_timestamp = order["refund_timestamp"]

        if pd.isna(refund_timestamp):

            refund_timestamp = order["return_timestamp"] + pd.Timedelta(hours=6)

        rows.append(
            {
                "refund_id": make_refund_id(refund_counter),
                "order_id": order["order_id"],
                "account_id": order["account_id"],
                "refund_timestamp": refund_timestamp,
                "refund_amount": float(order["refund_amount"]),
                "refund_reason": (order["return_reason_code"]),
                "refund_status": "processed",
                "refund_method": rng.choice(
                    [
                        "original_payment",
                        "wallet",
                        "bank_transfer",
                    ]
                ),
            }
        )

        refund_counter += 1

    return pd.DataFrame(rows)


# ============================================================
# DISPUTES TABLE
# ============================================================


def generate_disputes(orders):
    rows = []
    dispute_counter = 0

    evidence_columns = [
        "proof_of_service",
        "explanation_letter",
        "refund_confirmation",
        "access_activity_log",
        "refund_cancellation_policy",
        "terms_and_conditions",
    ]

    dispute_orders = orders[orders["dispute_flag"] == True]

    for _, order in dispute_orders.iterrows():

        # ----------------------------------------------------
        # Determine dispute creation timestamp
        # ----------------------------------------------------

        refund_time = order["refund_timestamp"]

        if pd.notna(refund_time):
            dispute_created = refund_time + pd.Timedelta(days=int(rng.integers(1, 4)))
        else:
            dispute_created = order["delivery_timestamp"] + pd.Timedelta(
                days=int(rng.integers(2, 5))
            )

        # ----------------------------------------------------
        # Generate Razorpay-style evidence availability
        # ----------------------------------------------------

        if order["dispute_reason_category"] == "friendly_fraud":
            # Friendly-fraud ring:
            # delivery/service evidence is deliberately missing.
            evidence = {
                "proof_of_service": False,
                "explanation_letter": True,
                "refund_confirmation": False,
                "access_activity_log": True,
                "refund_cancellation_policy": True,
                "terms_and_conditions": False,
            }

        else:
            # Normal / other disputes:
            # evidence availability is probabilistic.
            probabilities = {
                "proof_of_service": 0.70,
                "explanation_letter": 0.55,
                "refund_confirmation": 0.60,
                "access_activity_log": 0.50,
                "refund_cancellation_policy": 0.80,
                "terms_and_conditions": 0.80,
            }

            evidence = {
                field: bool(rng.random() < probabilities[field])
                for field in evidence_columns
            }

        # ----------------------------------------------------
        # Build dispute row
        # ----------------------------------------------------

        rows.append(
            {
                "dispute_id": make_dispute_id(dispute_counter),
                "order_id": order["order_id"],
                "account_id": order["account_id"],
                "dispute_created_at": (dispute_created),
                "dispute_phase": order["dispute_phase"],
                "dispute_reason_code": order["dispute_reason_code"],
                "dispute_reason_category": order["dispute_reason_category"],
                "respond_by": (dispute_created + pd.Timedelta(days=7)),
                # ------------------------------------------------
                # Razorpay evidence fields
                # ------------------------------------------------
                "proof_of_service": evidence["proof_of_service"],
                "explanation_letter": evidence["explanation_letter"],
                "refund_confirmation": evidence["refund_confirmation"],
                "access_activity_log": evidence["access_activity_log"],
                "refund_cancellation_policy": evidence["refund_cancellation_policy"],
                "terms_and_conditions": evidence["terms_and_conditions"],
            }
        )

        dispute_counter += 1

    return pd.DataFrame(rows)


# ============================================================
# MAIN
# ============================================================


def run_refunds_disputes():

    orders, accounts = load_data()

    orders = apply_normal_behavior(
        orders,
        accounts,
    )

    refunds = generate_refunds(orders)

    disputes = generate_disputes(orders)

    orders.to_csv(
        PATHS["orders"],
        index=False,
    )

    refunds.to_csv(
        PATHS["refunds"],
        index=False,
    )

    disputes.to_csv(
        PATHS["disputes"],
        index=False,
    )

    print(f"Refunds generated: " f"{len(refunds):,}")

    print(f"Disputes generated: " f"{len(disputes):,}")

    return (
        orders,
        refunds,
        disputes,
    )


if __name__ == "__main__":
    run_refunds_disputes()
