import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .features_config import (
    MODEL_A_PATH,
    MODEL_B_PATH,
    PREDICTIONS_TEST_PATH,
    GROUND_TRUTH_PATH,
)

# ============================================================
# CONSTANTS
# ============================================================

ID_COL = "account_id"

TARGET_COL = "true_ring_member"

RING_ID_COL = "abuse_ring_id"

RING_TYPE_COL = "ring_type"

RING_TYPES = [
    "wardrobing",
    "promo_refund_farming",
    "friendly_fraud",
    "subtle_distributed",
]


# ============================================================
# LOAD
# ============================================================


def load_data():
    """
    Load Day 6 test predictions and ground truth.

    Also loads the trained models for reference.
    """

    predictions = pd.read_csv(PREDICTIONS_TEST_PATH)
    ground_truth = pd.read_csv(GROUND_TRUTH_PATH)

    # Normalize IDs
    predictions[ID_COL] = predictions[ID_COL].astype(str)
    ground_truth[ID_COL] = ground_truth[ID_COL].astype(str)

    # Validate required columns
    for col in [ID_COL, "true_label", "proba_A", "proba_B", "pred_A", "pred_B"]:
        if col not in predictions.columns:
            raise KeyError(f"Predictions file missing required column: {col}")

    for col in [ID_COL, TARGET_COL, RING_ID_COL, RING_TYPE_COL]:
        if col not in ground_truth.columns:
            raise KeyError(f"Ground truth missing required column: {col}")

    # Load models
    with open(MODEL_A_PATH, "rb") as f:
        model_a = pickle.load(f)

    with open(MODEL_B_PATH, "rb") as f:
        model_b = pickle.load(f)

    return predictions, ground_truth, model_a, model_b


# ============================================================
# RING TYPE ABLATION
# ============================================================


def ring_type_ablation(
    predictions,
    ground_truth,
):
    """
    Compare Model A and Model B recall per ring type.

    The predictions file contains only test accounts.
    """

    # Merge ground truth ring_type and true_ring_member onto predictions
    merged = predictions.merge(
        ground_truth[[ID_COL, RING_ID_COL, RING_TYPE_COL, TARGET_COL]],
        on=ID_COL,
        how="left",
        validate="one_to_one",
    )

    # Ensure all predictions have ground truth
    assert merged[TARGET_COL].notna().all(), (
        "Some test predictions are missing ground truth labels."
    )

    # Ensure true_label column matches ground truth
    assert (merged["true_label"].astype(int) == merged[TARGET_COL].astype(int)).all(), (
        "true_label column does not match ground truth."
    )

    # --------------------------------------------------------
    # Overall false positives
    # --------------------------------------------------------

    non_ring = merged[merged[TARGET_COL] == 0]

    fp_a = int((non_ring["pred_A"] == 1).sum())
    fp_b = int((non_ring["pred_B"] == 1).sum())

    # --------------------------------------------------------
    # Per ring type metrics
    # --------------------------------------------------------

    ring_members = merged[merged[TARGET_COL] == 1].copy()

    results = {}

    for ring_type in RING_TYPES:
        subset = ring_members[ring_members[RING_TYPE_COL] == ring_type]

        total = len(subset)

        tp_a = int((subset["pred_A"] == 1).sum())
        tp_b = int((subset["pred_B"] == 1).sum())

        recall_a = tp_a / total if total > 0 else 0.0
        recall_b = tp_b / total if total > 0 else 0.0

        results[ring_type] = {
            "total_ring_members": total,
            "model_A": {
                "tp": tp_a,
                "recall": recall_a,
            },
            "model_B": {
                "tp": tp_b,
                "recall": recall_b,
            },
        }

    # --------------------------------------------------------
    # Model A vs B comparison per type
    # --------------------------------------------------------

    overall = {
        "non_ring_test_accounts": len(non_ring),
        "model_A_false_positives": fp_a,
        "model_B_false_positives": fp_b,
        "ring_types": results,
    }

    return overall


# ============================================================
# PRINT
# ============================================================


def print_ablation(results):
    """
    Print a clean table for the ring-type ablation.
    """

    print("\n" + "=" * 70)
    print("RING TYPE ABLATION — MODEL A vs MODEL B")
    print("=" * 70)

    print(f"\nNon-ring test accounts: {results['non_ring_test_accounts']:,}")
    print(f"Model A false positives: {results['model_A_false_positives']:,}")
    print(f"Model B false positives: {results['model_B_false_positives']:,}")

    print("\nPer ring type recall / detection rate:\n")

    print(
        f"{'Ring Type':<25}"
        f"{'Total':>7}"
        f"{'A TP':>7}"
        f"{'A Recall':>10}"
        f"{'B TP':>7}"
        f"{'B Recall':>10}"
    )
    print("-" * 70)

    for ring_type, metrics in results["ring_types"].items():
        total = metrics["total_ring_members"]
        tp_a = metrics["model_A"]["tp"]
        recall_a = metrics["model_A"]["recall"]
        tp_b = metrics["model_B"]["tp"]
        recall_b = metrics["model_B"]["recall"]

        print(
            f"{ring_type:<25}"
            f"{total:>7}"
            f"{tp_a:>7}"
            f"{recall_a:>10.4f}"
            f"{tp_b:>7}"
            f"{recall_b:>10.4f}"
        )

    print("\n" + "=" * 70)


# ============================================================
# SAVE
# ============================================================


def save_ablation_results(
    results,
    output_path,
):
    """
    Save ring-type ablation results to JSON.
    """

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nRing ablation results saved to:\n{output_path}")


# ============================================================
# MAIN
# ============================================================


def main():

    print("\n===================================")
    print("RINGWATCH RING TYPE ABLATION")
    print("===================================")

    predictions, ground_truth, model_a, model_b = load_data()

    results = ring_type_ablation(
        predictions,
        ground_truth,
    )

    print_ablation(results)

    output_path = (
        Path(MODEL_A_PATH).parent
        / "ring_type_ablation.json"
    )

    save_ablation_results(
        results,
        output_path,
    )

    print("\n===================================")
    print("RING TYPE ABLATION COMPLETED")
    print("===================================")


if __name__ == "__main__":
    main()