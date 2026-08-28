import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
import optuna
from optuna.samplers import TPESampler
from sklearn.model_selection import GroupKFold
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
    PREDICTIONS_TEST_PATH,
    MODEL_METRICS_PATH,
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

# Split proportions (same as original)
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Output paths for tuned models
MODEL_A_TUNED_PATH = MODEL_DIR / "model_lgbm_A_tuned.pkl"
MODEL_B_TUNED_PATH = MODEL_DIR / "model_lgbm_B_tuned.pkl"
MODEL_METRICS_TUNED_PATH = MODEL_DIR / "model_metrics_tuned.json"
BEST_PARAMS_PATH = MODEL_DIR / "best_params_tuned.json"


# ============================================================
# LOAD DATA (same as original lightgbm.py)
# ============================================================

def load_data():
    features_a = pd.read_csv(FEATURES_PATH)
    features_b = pd.read_csv(FEATURES_GRAPH_PATH)
    ground_truth = pd.read_csv(GROUND_TRUTH_PATH)

    # Validate required columns
    for df, name in [(features_a, "features_accounts.csv"),
                     (features_b, "features_graph.csv"),
                     (ground_truth, "ring_ground_truth.csv")]:
        if ID_COL not in df.columns:
            raise KeyError(f"{name} missing {ID_COL}")

    if TARGET_COL not in ground_truth.columns:
        raise KeyError(f"Ground truth missing {TARGET_COL}")
    if RING_ID_COL not in ground_truth.columns:
        raise KeyError(f"Ground truth missing {RING_ID_COL}")

    features_a[ID_COL] = features_a[ID_COL].astype(str)
    features_b[ID_COL] = features_b[ID_COL].astype(str)
    ground_truth[ID_COL] = ground_truth[ID_COL].astype(str)

    assert features_a[ID_COL].is_unique
    assert features_b[ID_COL].is_unique
    assert ground_truth[ID_COL].is_unique

    return features_a, features_b, ground_truth


# ============================================================
# RING-AWARE SPLIT (identical to original)
# ============================================================

def ring_aware_split(ground_truth, random_state=RANDOM_STATE):
    rng = np.random.default_rng(random_state)

    ring_members = ground_truth[ground_truth[TARGET_COL] == True].copy()
    non_ring = ground_truth[ground_truth[TARGET_COL] == False].copy()

    assert ring_members[RING_ID_COL].notna().all()

    ring_ids = ring_members[RING_ID_COL].dropna().unique()
    ring_ids = rng.permutation(ring_ids)

    n_rings = len(ring_ids)
    n_train = int(n_rings * TRAIN_RATIO)
    n_val = int(n_rings * VAL_RATIO)

    train_rings = set(ring_ids[:n_train])
    val_rings = set(ring_ids[n_train:n_train + n_val])
    test_rings = set(ring_ids[n_train + n_val:])

    train_ring_ids = ring_members[ring_members[RING_ID_COL].isin(train_rings)][ID_COL]
    val_ring_ids = ring_members[ring_members[RING_ID_COL].isin(val_rings)][ID_COL]
    test_ring_ids = ring_members[ring_members[RING_ID_COL].isin(test_rings)][ID_COL]

    # Random split non-ring accounts
    non_ring_ids = non_ring[ID_COL].tolist()
    # Use sklearn train_test_split to maintain proportions
    from sklearn.model_selection import train_test_split
    normal_train, normal_remain = train_test_split(
        non_ring_ids, test_size=(VAL_RATIO + TEST_RATIO),
        random_state=random_state, shuffle=True
    )
    normal_val, normal_test = train_test_split(
        normal_remain, test_size=TEST_RATIO / (VAL_RATIO + TEST_RATIO),
        random_state=random_state, shuffle=True
    )

    train_ids = pd.concat([train_ring_ids, pd.Series(normal_train)]).astype(str)
    val_ids = pd.concat([val_ring_ids, pd.Series(normal_val)]).astype(str)
    test_ids = pd.concat([test_ring_ids, pd.Series(normal_test)]).astype(str)

    return train_ids, val_ids, test_ids


# ============================================================
# PREPARE MODEL INPUTS (modified to accept a subset of IDs)
# ============================================================

def prepare_features(features_df, ground_truth, ids):
    df = features_df.merge(
        ground_truth[[ID_COL, TARGET_COL, RING_ID_COL]],
        on=ID_COL, how="left"
    )
    df = df[df[ID_COL].isin(ids)].copy()

    feature_cols = [c for c in df.columns if c not in META_COLUMNS and c != TARGET_COL]
    X = df[feature_cols]
    y = df[TARGET_COL].astype(int)
    account_ids = df[ID_COL].astype(str).values
    return X, y, feature_cols, account_ids


# ============================================================
# OPTUNA OBJECTIVE FUNCTION
# ============================================================

def create_objective(X, y, groups, n_splits=5, metric="pr_auc"):
    """
    groups: array-like, ring_id for ring members, account_id for non-ring.
    """
    def objective(trial):
        params = {
            "objective": "binary",
            "metric": "average_precision",
            "boosting_type": "gbdt",
            "n_estimators": trial.suggest_int("n_estimators", 200, 1000, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "max_depth": trial.suggest_int("max_depth", 5, 15),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "verbose": -1,
            "random_state": RANDOM_STATE,
        }

        gkf = GroupKFold(n_splits=n_splits)
        scores = []
        for train_idx, val_idx in gkf.split(X, y, groups=groups):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Compute scale_pos_weight per fold
            neg = (y_tr == 0).sum()
            pos = (y_tr == 1).sum()
            params["scale_pos_weight"] = neg / pos if pos > 0 else 1.0

            model = lgb.LGBMClassifier(**params)
            model.fit(X_tr, y_tr)
            proba = model.predict_proba(X_val)[:, 1]

            if metric == "pr_auc":
                score = average_precision_score(y_val, proba)
            elif metric == "roc_auc":
                score = roc_auc_score(y_val, proba)
            elif metric == "f1":
                # Use threshold 0.5 for simplicity; could also tune threshold
                pred = (proba >= 0.5).astype(int)
                score = f1_score(y_val, pred)
            else:
                raise ValueError(f"Unknown metric: {metric}")
            scores.append(score)

        return np.mean(scores)

    return objective


# ============================================================
# TUNE MODEL
# ============================================================

def tune_model(features_df, ground_truth, train_ids, n_trials=50, model_name="model"):
    X, y, feature_cols, account_ids = prepare_features(features_df, ground_truth, train_ids)

    # Create groups for GroupKFold
    groups_map = ground_truth.set_index(ID_COL)[RING_ID_COL].to_dict()
    groups = []
    for acc in account_ids:
        ring_id = groups_map.get(acc, None)
        if pd.isna(ring_id):
            groups.append(acc)  # unique for non-ring
        else:
            groups.append(ring_id)
    groups = np.array(groups)

    # X and y are already aligned with account_ids order.
    # No need to set index; just ensure they are numpy arrays or DataFrames.
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)

    objective = create_objective(X, y, groups, n_splits=5, metric="pr_auc")

    study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=RANDOM_STATE))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    best_params = study.best_params
    best_score = study.best_value

    print(f"\nBest {model_name} PR-AUC from CV: {best_score:.4f}")
    print(f"Best {model_name} params: {best_params}")

    return best_params, best_score


# ============================================================
# TRAIN FINAL MODEL & EVALUATE
# ============================================================

def train_final_and_evaluate(features_df, ground_truth, train_ids, val_ids, test_ids,
                             best_params, model_path, model_name):
    # Prepare training data (train_ids)
    X_train, y_train, _, _ = prepare_features(features_df, ground_truth, train_ids)
    X_val, y_val, _, _ = prepare_features(features_df, ground_truth, val_ids)
    X_test, y_test, _, _ = prepare_features(features_df, ground_truth, test_ids)

    # Compute scale_pos_weight from training set
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos_weight = neg / pos if pos > 0 else 1.0

    params = {
        "objective": "binary",
        "metric": "average_precision",
        "boosting_type": "gbdt",
        "scale_pos_weight": scale_pos_weight,
        "verbose": -1,
        "random_state": RANDOM_STATE,
    }
    params.update(best_params)

    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train)

    y_proba_val = model.predict_proba(X_val)[:, 1]
    thresholds = np.linspace(0.01, 0.99, 199)
    ...
    best_threshold = 0.5
    best_cost = np.inf
    for thr in thresholds:
        pred = (y_proba_val >= thr).astype(int)
        fp = ((pred == 1) & (y_val == 0)).sum()
        fn = ((pred == 0) & (y_val == 1)).sum()
        cost = fp * COST_FALSE_POSITIVE + fn * COST_FALSE_NEGATIVE
        if cost < best_cost:
            best_cost = cost
            best_threshold = thr

    # Evaluate on test set
    y_proba_test = model.predict_proba(X_test)[:, 1]
    y_pred_test = (y_proba_test >= best_threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred_test, labels=[0, 1]).ravel()
    precision = precision_score(y_test, y_pred_test, zero_division=0)
    recall = recall_score(y_test, y_pred_test, zero_division=0)
    f1 = f1_score(y_test, y_pred_test, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba_test)
    pr_auc = average_precision_score(y_test, y_proba_test)
    cost = fp * COST_FALSE_POSITIVE + fn * COST_FALSE_NEGATIVE

    metrics = {
        "threshold": float(best_threshold),
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
        "y_proba_test": y_proba_test,
        "y_pred_test": y_pred_test,
        "y_test": y_test.values,
    }

    # Save model
    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    print(f"\n{model_name} test results (tuned):")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1:        {f1:.4f}")
    print(f"  PR-AUC:    {pr_auc:.4f}")
    print(f"  ROC-AUC:   {roc_auc:.4f}")
    print(f"  Cost:      ₹{cost:,.0f}")
    print(f"  Threshold: {best_threshold:.3f}")

    return metrics


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 60)
    print("RINGWATCH DAY 6 – LIGHTGBM HYPERPARAMETER TUNING")
    print("=" * 60)

    # 1. Load data
    features_a, features_b, ground_truth = load_data()

    # 2. Split
    train_ids, val_ids, test_ids = ring_aware_split(ground_truth, random_state=RANDOM_STATE)
    print(f"\nRing-aware split:")
    print(f"Train: {len(train_ids):,}")
    print(f"Validation: {len(val_ids):,}")
    print(f"Test: {len(test_ids):,}")

    # 3. Tune Model A
    print("\nTuning Model A (behavioral + identity)...")
    best_params_a, cv_score_a = tune_model(
        features_a, ground_truth, train_ids, n_trials=50, model_name="Model A"
    )

    # 4. Tune Model B
    print("\nTuning Model B (behavioral + identity + graph)...")
    best_params_b, cv_score_b = tune_model(
        features_b, ground_truth, train_ids, n_trials=50, model_name="Model B"
    )

    # 5. Train final models and evaluate on test
    print("\nTraining final models with best hyperparameters...")
    metrics_a = train_final_and_evaluate(
        features_a, ground_truth, train_ids, val_ids, test_ids,
        best_params_a, MODEL_A_TUNED_PATH, "Model A"
    )
    metrics_b = train_final_and_evaluate(
        features_b, ground_truth, train_ids, val_ids, test_ids,
        best_params_b, MODEL_B_TUNED_PATH, "Model B"
    )

    # 6. Save best parameters and metrics
    best_params_summary = {
        "model_A": {
            "best_params": best_params_a,
            "cv_pr_auc": cv_score_a,
        },
        "model_B": {
            "best_params": best_params_b,
            "cv_pr_auc": cv_score_b,
        }
    }
    with open(BEST_PARAMS_PATH, "w") as f:
        json.dump(best_params_summary, f, indent=2)

    final_metrics = {
        "model_A": {k: v for k, v in metrics_a.items() if k not in ["y_proba_test", "y_pred_test", "y_test"]},
        "model_B": {k: v for k, v in metrics_b.items() if k not in ["y_proba_test", "y_pred_test", "y_test"]},
    }
    with open(MODEL_METRICS_TUNED_PATH, "w") as f:
        json.dump(final_metrics, f, indent=2)

    print("\n" + "=" * 60)
    print("TUNING COMPLETED")
    print("=" * 60)
    print(f"Best params saved to: {BEST_PARAMS_PATH}")
    print(f"Metrics saved to: {MODEL_METRICS_TUNED_PATH}")


if __name__ == "__main__":
    main()