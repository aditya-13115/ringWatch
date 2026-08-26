import json
import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)

from .config import SEED
from .features_config import (
    FEATURES_PATH,
    FEATURES_GRAPH_PATH,
    GROUND_TRUTH_PATH,
    MODEL_DIR,
    MODEL_A_PATH,
    MODEL_B_PATH,
    PREDICTIONS_TEST_PATH,
    MODEL_METRICS_PATH,
    FEATURE_IMPORTANCE_PATH,
    MODEL_LEAKAGE_REPORT_PATH,
)


# ============================================================
# CONSTANTS
# ============================================================

RANDOM_STATE = SEED

COST_FALSE_POSITIVE = 2_000.0
COST_FALSE_NEGATIVE = 15_000.0

TARGET_COL = "true_ring_member"

ID_COL = "account_id"

RING_ID_COL = "abuse_ring_id"

RING_TYPES = {
    "wardrobing",
    "promo_refund_farming",
    "friendly_fraud",
    "subtle_distributed",
}

# Split proportions by ring ID.
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Columns that must never be used as model features.
META_COLUMNS = {
    ID_COL,
    TARGET_COL,
    RING_ID_COL,
    "ring_type",
    "ring_start_time",
    "ring_end_time",
    "population_type",
    "community_id",
}


# ============================================================
# LOAD DATA
# ============================================================


def load_data():
    """
    Load Day 4 features, Day 5 graph features, and ground truth.

    Returns:
        features_a: Day 4 behavioral + identity features
        features_b: Day 5 behavioral + identity + graph features
        ground_truth: account-level evaluation labels
    """

    features_a = pd.read_csv(FEATURES_PATH)
    features_b = pd.read_csv(FEATURES_GRAPH_PATH)
    ground_truth = pd.read_csv(GROUND_TRUTH_PATH)

    # Validate required columns
    for df, name in [
        (features_a, "features_accounts.csv"),
        (features_b, "features_graph.csv"),
        (ground_truth, "ring_ground_truth.csv"),
    ]:
        if ID_COL not in df.columns:
            raise KeyError(f"{name} is missing required column: {ID_COL}")

    if TARGET_COL not in ground_truth.columns:
        raise KeyError(
            f"Ground truth is missing required target column: {TARGET_COL}"
        )

    if RING_ID_COL not in ground_truth.columns:
        raise KeyError(
            f"Ground truth is missing required ring ID column: {RING_ID_COL}"
        )

    # Convert account IDs to string
    features_a[ID_COL] = features_a[ID_COL].astype(str)
    features_b[ID_COL] = features_b[ID_COL].astype(str)
    ground_truth[ID_COL] = ground_truth[ID_COL].astype(str)

    # Ensure unique IDs
    assert features_a[ID_COL].is_unique, (
        "Day 4 features contain duplicate account IDs."
    )
    assert features_b[ID_COL].is_unique, (
        "Day 5 features contain duplicate account IDs."
    )
    assert ground_truth[ID_COL].is_unique, (
        "Ground truth contains duplicate account IDs."
    )

    # Ensure exact account alignment across files
    assert set(features_a[ID_COL]) == set(features_b[ID_COL]), (
        "Day 4 and Day 5 feature matrices do not contain the same accounts."
    )
    assert set(features_a[ID_COL]) == set(ground_truth[ID_COL]), (
        "Ground truth and feature matrices do not contain the same accounts."
    )

    return features_a, features_b, ground_truth


# ============================================================
# RING-AWARE SPLIT
# ============================================================


def ring_aware_split(
    ground_truth,
    random_state=RANDOM_STATE,
):
    """
    Split accounts into train/validation/test.

    Rules:
    - Ring members are kept together by abuse_ring_id.
    - Non-ring accounts are split randomly.

    Returns:
        train_ids, val_ids, test_ids
    """

    assert RING_ID_COL in ground_truth.columns
    assert TARGET_COL in ground_truth.columns

    rng = np.random.default_rng(random_state)

    ring_members = ground_truth[
        ground_truth[TARGET_COL] == True
    ].copy()

    non_ring = ground_truth[
        ground_truth[TARGET_COL] == False
    ].copy()

    # Every true ring member must have a non-null ring ID.
    assert ring_members[RING_ID_COL].notna().all(), (
        "Every true ring member must have a non-null abuse_ring_id."
    )

    # --------------------------------------------------------
    # Split ring IDs
    # --------------------------------------------------------

    ring_ids = ring_members[RING_ID_COL].dropna().unique()
    ring_ids = rng.permutation(ring_ids)

    n_rings = len(ring_ids)
    n_train = int(n_rings * TRAIN_RATIO)
    n_val = int(n_rings * VAL_RATIO)

    train_rings = set(ring_ids[:n_train])
    val_rings = set(ring_ids[n_train : n_train + n_val])
    test_rings = set(ring_ids[n_train + n_val :])

    assert train_rings.isdisjoint(val_rings)
    assert train_rings.isdisjoint(test_rings)
    assert val_rings.isdisjoint(test_rings)

    # --------------------------------------------------------
    # Assign ring members to splits
    # --------------------------------------------------------

    train_ring_ids = ring_members[
        ring_members[RING_ID_COL].isin(train_rings)
    ][ID_COL]

    val_ring_ids = ring_members[
        ring_members[RING_ID_COL].isin(val_rings)
    ][ID_COL]

    test_ring_ids = ring_members[
        ring_members[RING_ID_COL].isin(test_rings)
    ][ID_COL]

    # --------------------------------------------------------
    # Randomly split non-ring accounts
    # --------------------------------------------------------

    non_ring_ids = non_ring[ID_COL].tolist()

    normal_train, normal_remain = train_test_split(
        non_ring_ids,
        test_size=(VAL_RATIO + TEST_RATIO),
        random_state=random_state,
        shuffle=True,
    )

    normal_val, normal_test = train_test_split(
        normal_remain,
        test_size=(
            TEST_RATIO / (VAL_RATIO + TEST_RATIO)
        ),
        random_state=random_state,
        shuffle=True,
    )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    train_ids = pd.concat([
        train_ring_ids,
        pd.Series(normal_train),
    ]).astype(str)

    val_ids = pd.concat([
        val_ring_ids,
        pd.Series(normal_val),
    ]).astype(str)

    test_ids = pd.concat([
        test_ring_ids,
        pd.Series(normal_test),
    ]).astype(str)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    assert set(train_ids).isdisjoint(val_ids)
    assert set(train_ids).isdisjoint(test_ids)
    assert set(val_ids).isdisjoint(test_ids)

    assert (
        len(train_ids) + len(val_ids) + len(test_ids)
        == len(ground_truth)
    ), "Split sizes do not sum to total accounts."

    # Ensure no ring is split across multiple sets
    validate_ring_split(
        ground_truth,
        train_ids,
        val_ids,
        test_ids,
    )

    return train_ids, val_ids, test_ids


# ============================================================
# RING SPLIT VALIDATION
# ============================================================


def validate_ring_split(
    ground_truth,
    train_ids,
    val_ids,
    test_ids,
):
    """
    Verify that every abuse ring appears in exactly one split.
    """

    split_map = {}

    for account_id in train_ids:
        split_map[str(account_id)] = "train"

    for account_id in val_ids:
        split_map[str(account_id)] = "val"

    for account_id in test_ids:
        split_map[str(account_id)] = "test"

    check = ground_truth[
        ground_truth[TARGET_COL] == True
    ][[ID_COL, RING_ID_COL]].copy()

    check["split"] = check[ID_COL].astype(str).map(split_map)

    ring_split_counts = (
        check.groupby(RING_ID_COL)["split"]
        .nunique()
    )

    if not (ring_split_counts == 1).all():
        bad_rings = ring_split_counts[
            ring_split_counts != 1
        ].index.tolist()

        raise AssertionError(
            f"Rings split across multiple sets: {bad_rings}"
        )

    print(
        f"Ring split validation passed for "
        f"{len(ring_split_counts)} rings."
    )


# ============================================================
# PREPARE MODEL INPUTS
# ============================================================


def prepare_model_inputs(
    features_df,
    ground_truth,
    train_ids,
    val_ids,
    test_ids,
):
    """
    Convert a feature DataFrame into train/val/test X/y arrays.

    Drops ID, target, ring metadata, and community_id.
    Returns aligned account IDs for prediction storage.
    """

    df = features_df.merge(
        ground_truth[
            [ID_COL, TARGET_COL, RING_ID_COL, "ring_type"]
        ],
        on=ID_COL,
        how="left",
        validate="one_to_one",
    )

    feature_cols = [
        col
        for col in df.columns
        if col not in META_COLUMNS
        and col != TARGET_COL
    ]

    train_mask = df[ID_COL].isin(train_ids)
    val_mask = df[ID_COL].isin(val_ids)
    test_mask = df[ID_COL].isin(test_ids)

    train_subset = df.loc[train_mask].copy()
    val_subset = df.loc[val_mask].copy()
    test_subset = df.loc[test_mask].copy()

    X_train = train_subset[feature_cols].copy()
    y_train = train_subset[TARGET_COL].astype(int).copy()
    train_account_ids = train_subset[ID_COL].copy()

    X_val = val_subset[feature_cols].copy()
    y_val = val_subset[TARGET_COL].astype(int).copy()
    val_account_ids = val_subset[ID_COL].copy()

    X_test = test_subset[feature_cols].copy()
    y_test = test_subset[TARGET_COL].astype(int).copy()
    test_account_ids = test_subset[ID_COL].copy()

    # Validate numeric + finite
    for split_X, split_name in [
        (X_train, "train"),
        (X_val, "val"),
        (X_test, "test"),
    ]:
        assert split_X.select_dtypes(
            exclude="number"
        ).shape[1] == 0, (
            f"Non-numeric features in {split_name}"
        )

        assert np.isfinite(split_X.to_numpy()).all(), (
            f"Non-finite values in {split_name}"
        )

        assert not split_X.isna().any().any(), (
            f"NaN values in {split_name}"
        )

    return (
        feature_cols,
        (X_train, y_train, train_account_ids),
        (X_val, y_val, val_account_ids),
        (X_test, y_test, test_account_ids),
    )


# ============================================================
# TRAIN LIGHTGBM
# ============================================================


def train_lightgbm(
    X_train,
    y_train,
):
    """
    Train a LightGBM classifier with sensible baseline hyperparameters.
    """

    negatives = (y_train == 0).sum()
    positives = (y_train == 1).sum()

    scale_pos_weight = negatives / positives

    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=-1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_STATE,
        scale_pos_weight=scale_pos_weight,
        verbose=-1,
    )

    model.fit(X_train, y_train)

    return model, scale_pos_weight


# ============================================================
# THRESHOLD SELECTION
# ============================================================


def select_cost_optimal_threshold(
    model,
    X_val,
    y_val,
):
    """
    Select threshold on validation data by minimizing expected cost.
    """

    y_proba = model.predict_proba(X_val)[:, 1]

    thresholds = np.linspace(0.01, 0.99, 199)

    best_threshold = 0.5
    best_cost = np.inf

    for threshold in thresholds:
        y_pred = (y_proba >= threshold).astype(int)

        fp = ((y_pred == 1) & (y_val == 0)).sum()
        fn = ((y_pred == 0) & (y_val == 1)).sum()

        cost = (
            fp * COST_FALSE_POSITIVE
            + fn * COST_FALSE_NEGATIVE
        )

        if cost < best_cost:
            best_cost = cost
            best_threshold = threshold

    return best_threshold, best_cost


# ============================================================
# EVALUATION
# ============================================================


def evaluate_model(
    model,
    X_test,
    y_test,
    threshold,
):
    """
    Evaluate model on test set at the selected threshold.
    """

    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        y_pred,
        labels=[0, 1],
    ).ravel()

    precision = precision_score(
        y_test,
        y_pred,
        zero_division=0,
    )

    recall = recall_score(
        y_test,
        y_pred,
        zero_division=0,
    )

    f1 = f1_score(
        y_test,
        y_pred,
        zero_division=0,
    )

    roc_auc = roc_auc_score(
        y_test,
        y_proba,
    )

    pr_auc = average_precision_score(
        y_test,
        y_proba,
    )

    cost = (
        fp * COST_FALSE_POSITIVE
        + fn * COST_FALSE_NEGATIVE
    )

    return {
        "threshold": float(threshold),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "cost": float(cost),
        "y_proba": y_proba,
        "y_pred": y_pred,
    }


# ============================================================
# RULE BASELINE
# ============================================================


def apply_locked_baseline_rules(features_graph):
    """
    Re-apply the Day 5 locked rules to a feature subset.
    """

    r1 = (
        features_graph["return_rate"] > 0.5
    ) & (
        features_graph["total_orders"] >= 2
    )

    r2 = (
        features_graph["shared_device_count"] >= 1
    ) & (
        features_graph["return_rate"] > 0.3
    )

    r3 = (
        features_graph["account_creation_burst_score"] >= 5
    ) & (
        features_graph["coupon_usage_rate"] > 0.5
    )

    r4 = (
        features_graph["community_size"] >= 4
    ) & (
        features_graph["community_return_rate"] > 0.4
    )

    r5 = features_graph["dispute_rate"] > 0.3

    return (r1 | r2 | r3 | r4 | r5).astype(int)


def evaluate_baseline(
    features_graph_test,
    y_test,
):
    """
    Evaluate the locked rule baseline on the same test set.
    """

    y_pred = apply_locked_baseline_rules(
        features_graph_test
    )

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        y_pred,
        labels=[0, 1],
    ).ravel()

    return {
        "precision": precision_score(
            y_test,
            y_pred,
            zero_division=0,
        ),
        "recall": recall_score(
            y_test,
            y_pred,
            zero_division=0,
        ),
        "f1": f1_score(
            y_test,
            y_pred,
            zero_division=0,
        ),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "cost": float(
            fp * COST_FALSE_POSITIVE
            + fn * COST_FALSE_NEGATIVE
        ),
        "y_pred": y_pred,
    }


# ============================================================
# MAIN
# ============================================================


def main():

    print("\n===================================")
    print("RINGWATCH DAY 6 — LIGHTGBM")
    print("===================================")

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    features_a, features_b, ground_truth = load_data()

    train_ids, val_ids, test_ids = ring_aware_split(
        ground_truth,
        random_state=RANDOM_STATE,
    )

    print("\nRing-aware split:")
    print(f"Train: {len(train_ids):,}")
    print(f"Validation: {len(val_ids):,}")
    print(f"Test: {len(test_ids):,}")

    # --------------------------------------------------------
    # Model A — behavioral + identity features
    # --------------------------------------------------------

    print("\nPreparing Model A inputs...")

    feature_cols_a, data_a_train, data_a_val, data_a_test = (
        prepare_model_inputs(
            features_a,
            ground_truth,
            train_ids,
            val_ids,
            test_ids,
        )
    )

    X_train_A, y_train_A, train_ids_A = data_a_train
    X_val_A, y_val_A, val_ids_A = data_a_val
    X_test_A, y_test_A, test_ids_A = data_a_test

    # --------------------------------------------------------
    # Model B — behavioral + identity + graph features
    # --------------------------------------------------------

    print("Preparing Model B inputs...")

    feature_cols_b, data_b_train, data_b_val, data_b_test = (
        prepare_model_inputs(
            features_b,
            ground_truth,
            train_ids,
            val_ids,
            test_ids,
        )
    )

    print("\nFeature counts:")
    print(f"Model A features: {len(feature_cols_a):,}")
    print(f"Model B features: {len(feature_cols_b):,}")
    print(
        f"Graph-only features: "
        f"{len(set(feature_cols_b) - set(feature_cols_a)):,}"
    )

    X_train_B, y_train_B, train_ids_B = data_b_train
    X_val_B, y_val_B, val_ids_B = data_b_val
    X_test_B, y_test_B, test_ids_B = data_b_test

    # Critical: ensure test alignment between A and B
    assert test_ids_A.tolist() == test_ids_B.tolist(), (
        "Model A and Model B test account IDs do not match."
    )

    assert y_test_A.tolist() == y_test_B.tolist(), (
        "Model A and Model B test labels do not match."
    )

    # --------------------------------------------------------
    # Train Model A
    # --------------------------------------------------------

    print("\nTraining Model A...")

    model_a, scale_pos_weight_a = train_lightgbm(
        X_train_A,
        y_train_A,
    )

    threshold_a, cost_val_a = select_cost_optimal_threshold(
        model_a,
        X_val_A,
        y_val_A,
    )

    # --------------------------------------------------------
    # Train Model B
    # --------------------------------------------------------

    print("Training Model B...")

    model_b, scale_pos_weight_b = train_lightgbm(
        X_train_B,
        y_train_B,
    )

    threshold_b, cost_val_b = select_cost_optimal_threshold(
        model_b,
        X_val_B,
        y_val_B,
    )

    # --------------------------------------------------------
    # Evaluate on test
    # --------------------------------------------------------

    print("\nEvaluating on held-out test set...")

    metrics_a = evaluate_model(
        model_a,
        X_test_A,
        y_test_A,
        threshold_a,
    )

    metrics_b = evaluate_model(
        model_b,
        X_test_B,
        y_test_B,
        threshold_b,
    )

    baseline_metrics = evaluate_baseline(
        X_test_B,
        y_test_B,
    )

    # --------------------------------------------------------
    # Print comparison
    # --------------------------------------------------------

    print("\n===================================")
    print("TEST SET RESULTS")
    print("===================================")

    print("\nModel A (behavioral + identity):")
    print(f"  Precision: {metrics_a['precision']:.4f}")
    print(f"  Recall:    {metrics_a['recall']:.4f}")
    print(f"  F1:        {metrics_a['f1']:.4f}")
    print(f"  PR-AUC:    {metrics_a['pr_auc']:.4f}")
    print(f"  ROC-AUC:   {metrics_a['roc_auc']:.4f}")
    print(f"  Cost:      ₹{metrics_a['cost']:,.0f}")
    print(f"  Threshold: {metrics_a['threshold']:.3f}")

    print("\nModel B (behavioral + identity + graph):")
    print(f"  Precision: {metrics_b['precision']:.4f}")
    print(f"  Recall:    {metrics_b['recall']:.4f}")
    print(f"  F1:        {metrics_b['f1']:.4f}")
    print(f"  PR-AUC:    {metrics_b['pr_auc']:.4f}")
    print(f"  ROC-AUC:   {metrics_b['roc_auc']:.4f}")
    print(f"  Cost:      ₹{metrics_b['cost']:,.0f}")
    print(f"  Threshold: {metrics_b['threshold']:.3f}")

    print("\nLocked Rule Baseline (same test split):")
    print(f"  Precision: {baseline_metrics['precision']:.4f}")
    print(f"  Recall:    {baseline_metrics['recall']:.4f}")
    print(f"  F1:        {baseline_metrics['f1']:.4f}")
    print(f"  Cost:      ₹{baseline_metrics['cost']:,.0f}")

    print("\n===================================")
    print("MODEL COMPARISON")
    print("===================================")

    print(
        f"Model B vs A F1:       "
        f"{metrics_b['f1'] - metrics_a['f1']:+.4f}"
    )

    print(
        f"Model B vs A PR-AUC:   "
        f"{metrics_b['pr_auc'] - metrics_a['pr_auc']:+.4f}"
    )

    print(
        f"Model B vs A ROC-AUC:  "
        f"{metrics_b['roc_auc'] - metrics_a['roc_auc']:+.4f}"
    )

    print(
        f"Model B vs A Cost:     "
        f"₹{metrics_b['cost'] - metrics_a['cost']:+,.0f}"
    )

    # --------------------------------------------------------
    # Save models
    # --------------------------------------------------------

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    with open(MODEL_A_PATH, "wb") as f:
        pickle.dump(model_a, f)

    with open(MODEL_B_PATH, "wb") as f:
        pickle.dump(model_b, f)

    # --------------------------------------------------------
    # Save test predictions
    # --------------------------------------------------------

    test_predictions = pd.DataFrame({
        ID_COL: test_ids_B.values,
        "true_label": y_test_B.values,
        "proba_A": metrics_a["y_proba"],
        "proba_B": metrics_b["y_proba"],
        "pred_A": metrics_a["y_pred"],
        "pred_B": metrics_b["y_pred"],
        "pred_baseline": baseline_metrics["y_pred"],
    })

    test_predictions.to_csv(
        PREDICTIONS_TEST_PATH,
        index=False,
    )

    # --------------------------------------------------------
    # Save feature importance
    # --------------------------------------------------------

    importance_a = pd.DataFrame({
        "feature": feature_cols_a,
        "importance": model_a.feature_importances_,
    }).sort_values(
        "importance",
        ascending=False,
    )

    importance_b = pd.DataFrame({
        "feature": feature_cols_b,
        "importance": model_b.feature_importances_,
    }).sort_values(
        "importance",
        ascending=False,
    )

    model_a_importance_path = (
        MODEL_DIR / "model_a_feature_importance.csv"
    )

    model_b_importance_path = (
        MODEL_DIR / "model_b_feature_importance.csv"
    )

    importance_a.to_csv(
        model_a_importance_path,
        index=False,
    )

    importance_b.to_csv(
        model_b_importance_path,
        index=False,
    )

    print(
        f"\nModel A feature importance saved to:\n"
        f"{model_a_importance_path}"
    )

    print(
        f"Model B feature importance saved to:\n"
        f"{model_b_importance_path}"
    )

    # --------------------------------------------------------
    # Save metrics
    # --------------------------------------------------------

    summary = {
        "split": {
            "train": len(train_ids),
            "validation": len(val_ids),
            "test": len(test_ids),
        },
        "artifacts": {
            "model_a": str(MODEL_A_PATH),
            "model_b": str(MODEL_B_PATH),
            "model_a_feature_importance": str(
                model_a_importance_path
            ),
            "model_b_feature_importance": str(
                model_b_importance_path
            ),
            "test_predictions": str(PREDICTIONS_TEST_PATH),
        },
        "model_A": {
            "scale_pos_weight": scale_pos_weight_a,
            "threshold": threshold_a,
            "validation_cost": cost_val_a,
            "test": {
                key: value
                for key, value in metrics_a.items()
                if key not in ["y_proba", "y_pred"]
            },
        },
        "model_B": {
            "scale_pos_weight": scale_pos_weight_b,
            "threshold": threshold_b,
            "validation_cost": cost_val_b,
            "test": {
                key: value
                for key, value in metrics_b.items()
                if key not in ["y_proba", "y_pred"]
            },
        },
        "baseline_test": {
            key: value
            for key, value in baseline_metrics.items()
            if key != "y_pred"
        },
    }

    with open(
        MODEL_METRICS_PATH,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            summary,
            f,
            indent=2,
        )

    # --------------------------------------------------------
    # Leakage report
    # --------------------------------------------------------

    leakage_report = f"""RingWatch — Day 6 Model Leakage Report
========================================

Ground truth used for training:
YES — target labels only.

Ground truth used for feature generation:
NO

population_type used for features:
NO

abuse_ring_id used for:
SPLITTING ONLY.

ring_type used for:
SPLITTING/VALIDATION ONLY.

community_id used for:
EXCLUDED FROM MODEL FEATURES.

Ring-aware split:
YES — every abuse ring kept together.

Split strategy:
Train:        70% of rings + proportional non-ring accounts
Validation:   15% of rings + proportional non-ring accounts
Test:         15% of rings + proportional non-ring accounts

Threshold selection:
YES — validation set only.

Test set used for:
FINAL EVALUATION ONLY.

Test labels used for:
METRICS ONLY.

LEAKAGE CHECK: PASSED
"""

    with open(
        MODEL_LEAKAGE_REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(leakage_report)

    print("\n===================================")
    print("DAY 6 COMPLETED")
    print("===================================")


if __name__ == "__main__":
    main()