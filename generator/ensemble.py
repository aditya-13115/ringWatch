import json
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)

from .config import SEED
from .features_config import (
    FEATURES_PATH,
    FEATURES_GRAPH_PATH,
    GROUND_TRUTH_PATH,
    GRAPH_EDGES_PATH,
    PROCESSED_DIR,
)
from .lightgbm_tuned import (
    ring_aware_split,
    prepare_features,
    ID_COL,
    TARGET_COL,
    RING_ID_COL,
)
from .gnn_model import load_graph_data, create_masks, FraudSAGE  # changed import

# ============================================================
# CONSTANTS
# ============================================================
RANDOM_STATE = SEED
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
COST_FALSE_POSITIVE = 2_000.0
COST_FALSE_NEGATIVE = 15_000.0

ENSEMBLE_METRICS_PATH = PROCESSED_DIR / "model" / "ensemble_metrics.json"

# ============================================================
# MAIN
# ============================================================


def main():
    print("Loading data and models...")

    # Load ground truth and features
    ground_truth = pd.read_csv(GROUND_TRUTH_PATH)
    ground_truth[ID_COL] = ground_truth[ID_COL].astype(str)

    features_b = pd.read_csv(FEATURES_GRAPH_PATH)
    features_b[ID_COL] = features_b[ID_COL].astype(str)

    # Split (same as used in training)
    train_ids, val_ids, test_ids = ring_aware_split(
        ground_truth, random_state=RANDOM_STATE
    )

    # Load LightGBM Model B (tuned)
    lgb_model_path = PROCESSED_DIR / "model" / "model_lgbm_B_tuned.pkl"
    with open(lgb_model_path, "rb") as f:
        lgb_model = pickle.load(f)

    # Prepare LightGBM features for validation/test
    X_val_b, y_val_lgb, feature_cols, val_account_ids = prepare_features(
        features_b, ground_truth, val_ids
    )
    X_test_b, y_test_lgb, _, test_account_ids = prepare_features(
        features_b, ground_truth, test_ids
    )

    proba_b_val = lgb_model.predict_proba(X_val_b)[:, 1]
    proba_b_test = lgb_model.predict_proba(X_test_b)[:, 1]

    # Load GNN model and graph data
    data = load_graph_data()
    data = create_masks(data, ground_truth)
    data = data.to(DEVICE)

    # Instantiate the SAME GNN architecture used in training (FraudSAGE with hidden_channels=64, num_layers=2, dropout=0.3)
    gnn_model = FraudSAGE(
        in_channels=data.x.size(1),
        hidden_channels=64,
        num_layers=2,
        dropout=0.3,
    ).to(DEVICE)

    gnn_model_path = PROCESSED_DIR / "model" / "gnn_model.pt"
    gnn_model.load_state_dict(torch.load(gnn_model_path, map_location=DEVICE))
    gnn_model.eval()

    # Get GNN probabilities for validation and test nodes
    with torch.no_grad():
        out = gnn_model(data)
        proba_gnn_val = out[data.val_mask].exp()[:, 1].cpu().numpy()
        proba_gnn_test = out[data.test_mask].exp()[:, 1].cpu().numpy()

    # Align probabilities by account ID
    # LightGBM returns probabilities for val_account_ids, test_account_ids in the order of those lists.
    # GNN returns probabilities in the order of nodes that have val_mask/test_mask True.
    val_node_account_ids = [
        data.account_ids[i] for i in range(data.num_nodes) if data.val_mask[i]
    ]
    test_node_account_ids = [
        data.account_ids[i] for i in range(data.num_nodes) if data.test_mask[i]
    ]

    # Create mapping from account_id to LightGBM probability
    proba_b_val_dict = dict(zip(val_account_ids, proba_b_val))
    proba_b_test_dict = dict(zip(test_account_ids, proba_b_test))

    # Align LightGBM probabilities to GNN order
    proba_b_val_aligned = np.array(
        [proba_b_val_dict[acc] for acc in val_node_account_ids]
    )
    proba_b_test_aligned = np.array(
        [proba_b_test_dict[acc] for acc in test_node_account_ids]
    )

    # Ensemble (average)
    ensemble_proba_val = (proba_b_val_aligned + proba_gnn_val) / 2.0
    ensemble_proba_test = (proba_b_test_aligned + proba_gnn_test) / 2.0

    # Ground truth for GNN masks
    y_val = data.y[data.val_mask].cpu().numpy()
    y_test = data.y[data.test_mask].cpu().numpy()

    # Select threshold on validation set (cost‑optimal)
    thresholds = np.linspace(0.01, 0.99, 199)
    best_thr = 0.5
    best_cost = np.inf
    for thr in thresholds:
        pred = (ensemble_proba_val >= thr).astype(int)
        fp = ((pred == 1) & (y_val == 0)).sum()
        fn = ((pred == 0) & (y_val == 1)).sum()
        cost = fp * COST_FALSE_POSITIVE + fn * COST_FALSE_NEGATIVE
        if cost < best_cost:
            best_cost = cost
            best_thr = thr

    # Save canonical ensemble test predictions after the validation threshold
    # has been selected. This file is also useful to the Metrics API.
    ensemble_predictions = pd.DataFrame(
        {
            "account_id": test_node_account_ids,
            "true_label": y_test.astype(int),
            "proba_ensemble": ensemble_proba_test,
            "pred_ensemble": (ensemble_proba_test >= best_thr).astype(int),
        }
    )

    ensemble_predictions_path = (
        PROCESSED_DIR / "model" / "ensemble_predictions_test.csv"
    )
    ensemble_predictions.to_csv(ensemble_predictions_path, index=False)

    print(f"\nEnsemble test predictions saved to:" f"\n{ensemble_predictions_path}")

    # Final evaluation on test set
    pred_test = (ensemble_proba_test >= best_thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred_test, labels=[0, 1]).ravel()

    precision = precision_score(y_test, pred_test, zero_division=0)
    recall = recall_score(y_test, pred_test, zero_division=0)
    f1 = f1_score(y_test, pred_test, zero_division=0)
    roc_auc = roc_auc_score(y_test, ensemble_proba_test)
    pr_auc = average_precision_score(y_test, ensemble_proba_test)
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    cost = fp * COST_FALSE_POSITIVE + fn * COST_FALSE_NEGATIVE

    metrics = {
        "threshold": float(best_thr),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "cost": cost,
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }

    print("\nEnsemble (LightGBM B + GNN) Test Results:")
    for k, v in metrics.items():
        if k != "confusion_matrix":
            print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    print(f"  Confusion Matrix: [[TN={tn}, FP={fp}], [FN={fn}, TP={tp}]]")

    with open(ENSEMBLE_METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nMetrics saved to {ENSEMBLE_METRICS_PATH}")


if __name__ == "__main__":
    main()
