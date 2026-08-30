import json
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt

from sklearn.metrics import (
    roc_curve,
    auc,
    precision_recall_curve,
    average_precision_score,
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
    META_COLUMNS,
    ID_COL,
    TARGET_COL,
    RING_ID_COL,
)
from .gnn_model import load_graph_data, create_masks, FraudSAGE

# ============================================================
# CONSTANTS
# ============================================================
RANDOM_STATE = SEED
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

PLOT_DIR = PROCESSED_DIR / "plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# UTILITY
# ============================================================


def load_models_and_data():
    """Load all models and data, and return test probabilities and labels."""
    # Load ground truth and features
    ground_truth = pd.read_csv(GROUND_TRUTH_PATH)
    ground_truth[ID_COL] = ground_truth[ID_COL].astype(str)

    features_a = pd.read_csv(FEATURES_PATH)
    features_a[ID_COL] = features_a[ID_COL].astype(str)
    features_b = pd.read_csv(FEATURES_GRAPH_PATH)
    features_b[ID_COL] = features_b[ID_COL].astype(str)

    # Split
    train_ids, val_ids, test_ids = ring_aware_split(
        ground_truth, random_state=RANDOM_STATE
    )

    # Load LightGBM models
    model_a_path = PROCESSED_DIR / "model" / "model_lgbm_A_tuned.pkl"
    model_b_path = PROCESSED_DIR / "model" / "model_lgbm_B_tuned.pkl"
    with open(model_a_path, "rb") as f:
        model_a = pickle.load(f)
    with open(model_b_path, "rb") as f:
        model_b = pickle.load(f)

    # Prepare LightGBM features for test
    X_test_a, y_test_a, _, test_account_ids_a = prepare_features(
        features_a, ground_truth, test_ids
    )
    X_test_b, y_test_b, _, test_account_ids_b = prepare_features(
        features_b, ground_truth, test_ids
    )

    # Predict probabilities
    proba_a = model_a.predict_proba(X_test_a)[:, 1]
    proba_b = model_b.predict_proba(X_test_b)[:, 1]

    # Load GNN model and data
    data = load_graph_data()
    data = create_masks(data, ground_truth)
    data = data.to(DEVICE)

    gnn_model = FraudSAGE(
        in_channels=data.x.size(1),
        hidden_channels=64,
        num_layers=2,
        dropout=0.3,
    ).to(DEVICE)
    gnn_model_path = PROCESSED_DIR / "model" / "gnn_model.pt"
    gnn_model.load_state_dict(torch.load(gnn_model_path, map_location=DEVICE))
    gnn_model.eval()

    with torch.no_grad():
        out = gnn_model(data)
        proba_gnn_test = out[data.test_mask].exp()[:, 1].cpu().numpy()

    # Align GNN test account IDs with LightGBM test account IDs
    test_node_account_ids = [
        data.account_ids[i] for i in range(data.num_nodes) if data.test_mask[i]
    ]
    # Ensure order matches LightGBM test ids (should be same order because both use same split)
    assert list(test_node_account_ids) == list(
        test_account_ids_a
    ), "Order mismatch between GNN and LightGBM test IDs"

    y_test = y_test_a  # same labels

    # Ensemble (LightGBM B + GNN)
    proba_ensemble = (proba_b + proba_gnn_test) / 2.0

    return {
        "proba_a": proba_a,
        "proba_b": proba_b,
        "proba_gnn": proba_gnn_test,
        "proba_ensemble": proba_ensemble,
        "y_test": y_test,
    }


# ============================================================
# PLOTTING FUNCTIONS
# ============================================================


def plot_roc_curves(data_dict):
    plt.figure(figsize=(8, 6))
    for name, proba in data_dict.items():
        if name == "y_test":
            continue
        fpr, tpr, _ = roc_curve(data_dict["y_test"], proba)
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"{name} (AUC = {roc_auc:.4f})")

    plt.plot([0, 1], [0, 1], "k--", alpha=0.5)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curves (Test Set)")
    plt.legend(loc="lower right")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "roc_curves.png", dpi=150)
    plt.close()


def plot_pr_curves(data_dict):
    plt.figure(figsize=(8, 6))
    for name, proba in data_dict.items():
        if name == "y_test":
            continue
        precision, recall, _ = precision_recall_curve(data_dict["y_test"], proba)
        pr_auc = average_precision_score(data_dict["y_test"], proba)
        plt.plot(recall, precision, label=f"{name} (PR-AUC = {pr_auc:.4f})")

    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curves (Test Set)")
    plt.legend(loc="upper right")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "pr_curves.png", dpi=150)
    plt.close()


def plot_score_distributions(data_dict):
    y = data_dict["y_test"]
    for name, proba in data_dict.items():
        if name == "y_test":
            continue
        pos_scores = proba[y == 1]
        neg_scores = proba[y == 0]

        plt.figure(figsize=(8, 5))
        plt.hist(neg_scores, bins=50, alpha=0.6, label="Normal", density=True)
        plt.hist(pos_scores, bins=50, alpha=0.6, label="Fraud", density=True)
        plt.xlabel("Predicted Probability")
        plt.ylabel("Density")
        plt.title(f"Score Distribution: {name}")
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(PLOT_DIR / f"score_dist_{name}.png", dpi=150)
        plt.close()


def main():
    print("Loading models and computing test probabilities...")
    data = load_models_and_data()

    print("Plotting ROC curves...")
    plot_roc_curves(data)

    print("Plotting PR curves...")
    plot_pr_curves(data)

    print("Plotting score distributions...")
    plot_score_distributions(data)

    print(f"\nAll plots saved to {PLOT_DIR}")


if __name__ == "__main__":
    main()
