import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import SAGEConv
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
)
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from .config import SEED
from .features_config import (
    FEATURES_PATH,
    GROUND_TRUTH_PATH,
    GRAPH_EDGES_PATH,
    PROCESSED_DIR,
)

# ============================================================
# CONSTANTS
# ============================================================
RANDOM_STATE = SEED
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

TARGET_COL = "true_ring_member"
ID_COL = "account_id"
RING_ID_COL = "abuse_ring_id"

GNN_MODEL_PATH = PROCESSED_DIR / "model" / "gnn_model.pt"
GNN_METRICS_PATH = PROCESSED_DIR / "model" / "gnn_metrics.json"

COST_FALSE_POSITIVE = 2_000.0
COST_FALSE_NEGATIVE = 15_000.0

# ============================================================
# DATA LOADING (with undirected edges and scaling)
# ============================================================


def load_graph_data():
    features = pd.read_csv(FEATURES_PATH)
    account_ids = features[ID_COL].astype(str).tolist()
    id_to_idx = {acc: i for i, acc in enumerate(account_ids)}

    # Prepare node features (numerical only)
    drop_cols = [ID_COL, "population_type", "community_id"]
    node_feats = features.drop(columns=[c for c in drop_cols if c in features.columns])
    node_feats = node_feats.select_dtypes(include=[np.number]).astype(np.float32)

    # Standardize features
    scaler = StandardScaler()
    node_feats_scaled = scaler.fit_transform(node_feats)

    # Load edges and build undirected edge_index
    edges = pd.read_csv(GRAPH_EDGES_PATH)
    src = edges["account_id_1"].map(id_to_idx).values
    dst = edges["account_id_2"].map(id_to_idx).values
    weights = edges["weight"].values

    # Undirected: add both directions
    full_src = np.concatenate([src, dst])
    full_dst = np.concatenate([dst, src])
    full_weights = np.concatenate([weights, weights])

    # Add self-loops with weight 1.0 (or a small value) to allow node's own features
    self_loop_src = np.arange(len(account_ids))
    self_loop_dst = np.arange(len(account_ids))
    self_loop_weights = np.ones(len(account_ids), dtype=np.float32)

    final_src = np.concatenate([full_src, self_loop_src])
    final_dst = np.concatenate([full_dst, self_loop_dst])
    final_weights = np.concatenate([full_weights, self_loop_weights])

    edge_index = torch.tensor(np.stack([final_src, final_dst]), dtype=torch.long)
    edge_attr = torch.tensor(final_weights, dtype=torch.float32).unsqueeze(1)

    # Labels
    gt = pd.read_csv(GROUND_TRUTH_PATH)
    gt[ID_COL] = gt[ID_COL].astype(str)
    labels = gt.set_index(ID_COL)[TARGET_COL].astype(int)
    y = torch.tensor([labels.loc[acc] for acc in account_ids], dtype=torch.long)

    data = Data(
        x=torch.tensor(node_feats_scaled, dtype=torch.float32),
        edge_index=edge_index,
        edge_attr=edge_attr,
        y=y,
    )
    data.num_nodes = len(account_ids)
    data.id_to_idx = id_to_idx
    data.account_ids = account_ids
    return data


# ============================================================
# RING-AWARE SPLIT (same as before)
# ============================================================


def ring_aware_split(ground_truth, random_state=RANDOM_STATE):
    rng = np.random.default_rng(random_state)
    ring_members = ground_truth[ground_truth[TARGET_COL] == True].copy()
    non_ring = ground_truth[ground_truth[TARGET_COL] == False].copy()

    ring_ids = ring_members[RING_ID_COL].dropna().unique()
    ring_ids = rng.permutation(ring_ids)

    n_rings = len(ring_ids)
    n_train = int(n_rings * 0.70)
    n_val = int(n_rings * 0.15)

    train_rings = set(ring_ids[:n_train])
    val_rings = set(ring_ids[n_train : n_train + n_val])
    test_rings = set(ring_ids[n_train + n_val :])

    train_ring_ids = ring_members[ring_members[RING_ID_COL].isin(train_rings)][ID_COL]
    val_ring_ids = ring_members[ring_members[RING_ID_COL].isin(val_rings)][ID_COL]
    test_ring_ids = ring_members[ring_members[RING_ID_COL].isin(test_rings)][ID_COL]

    non_ring_ids = non_ring[ID_COL].tolist()
    normal_train, normal_remain = train_test_split(
        non_ring_ids, test_size=(0.15 + 0.15), random_state=random_state, shuffle=True
    )
    normal_val, normal_test = train_test_split(
        normal_remain,
        test_size=0.15 / (0.15 + 0.15),
        random_state=random_state,
        shuffle=True,
    )

    train_ids = (
        pd.concat([train_ring_ids, pd.Series(normal_train)]).astype(str).tolist()
    )
    val_ids = pd.concat([val_ring_ids, pd.Series(normal_val)]).astype(str).tolist()
    test_ids = pd.concat([test_ring_ids, pd.Series(normal_test)]).astype(str).tolist()
    return train_ids, val_ids, test_ids


def create_masks(data, ground_truth):
    train_ids, val_ids, test_ids = ring_aware_split(ground_truth)
    id_to_idx = data.id_to_idx
    train_idx = [id_to_idx[acc] for acc in train_ids if acc in id_to_idx]
    val_idx = [id_to_idx[acc] for acc in val_ids if acc in id_to_idx]
    test_idx = [id_to_idx[acc] for acc in test_ids if acc in id_to_idx]

    data.train_mask = torch.zeros(data.num_nodes, dtype=torch.bool)
    data.val_mask = torch.zeros(data.num_nodes, dtype=torch.bool)
    data.test_mask = torch.zeros(data.num_nodes, dtype=torch.bool)
    data.train_mask[train_idx] = True
    data.val_mask[val_idx] = True
    data.test_mask[test_idx] = True
    return data


# ============================================================
# GNN MODEL (GraphSAGE)
# ============================================================


class FraudSAGE(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels=64, num_layers=2, dropout=0.3):
        super().__init__()
        self.convs = torch.nn.ModuleList()
        self.convs.append(SAGEConv(in_channels, hidden_channels))
        for _ in range(num_layers - 1):
            self.convs.append(SAGEConv(hidden_channels, hidden_channels))
        self.lin = torch.nn.Linear(hidden_channels, 2)
        self.dropout = dropout

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        for conv in self.convs:
            x = F.relu(conv(x, edge_index))
            x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.lin(x)
        return F.log_softmax(x, dim=1)


# ============================================================
# TRAINING
# ============================================================


def train(model, data, optimizer, epochs=200, patience=15):
    best_val_pr_auc = 0.0
    best_state = None
    patience_counter = 0

    # Class weights for imbalanced loss
    pos_weight = (data.y[data.train_mask] == 0).sum().float() / (
        data.y[data.train_mask] == 1
    ).sum().float()
    class_weights = torch.tensor([1.0, pos_weight.item()], device=data.x.device)

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        out = model(data)
        loss = F.nll_loss(
            out[data.train_mask], data.y[data.train_mask], weight=class_weights
        )
        loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_out = model(data)
            val_proba = val_out[data.val_mask].exp()[:, 1].cpu().numpy()
            val_true = data.y[data.val_mask].cpu().numpy()
            val_pr_auc = average_precision_score(val_true, val_proba)

        if val_pr_auc > best_val_pr_auc:
            best_val_pr_auc = val_pr_auc
            best_state = model.state_dict().copy()
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(
                    f"Early stopping at epoch {epoch} (best val PR-AUC: {best_val_pr_auc:.4f})"
                )
                break

    model.load_state_dict(best_state)
    return model


# ============================================================
# EVALUATION
# ============================================================


@torch.no_grad()
def evaluate(model, data, mask, threshold=0.5):
    model.eval()
    out = model(data)
    proba = out[mask].exp()[:, 1].cpu().numpy()
    true = data.y[mask].cpu().numpy()

    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(true, pred, labels=[0, 1]).ravel()

    return {
        "roc_auc": roc_auc_score(true, proba),
        "pr_auc": average_precision_score(true, proba),
        "precision": precision_score(true, pred, zero_division=0),
        "recall": recall_score(true, pred, zero_division=0),
        "f1": f1_score(true, pred, zero_division=0),
        "cost": float(fp * COST_FALSE_POSITIVE + fn * COST_FALSE_NEGATIVE),
        "threshold": float(threshold),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }


def select_threshold(model, data, val_mask):
    model.eval()
    with torch.no_grad():
        out = model(data)
        val_proba = out[val_mask].exp()[:, 1].cpu().numpy()
        val_true = data.y[val_mask].cpu().numpy()

    best_thr = 0.5
    best_cost = np.inf
    for thr in np.linspace(0.01, 0.99, 199):
        pred = (val_proba >= thr).astype(int)
        fp = ((pred == 1) & (val_true == 0)).sum()
        fn = ((pred == 0) & (val_true == 1)).sum()
        cost = fp * COST_FALSE_POSITIVE + fn * COST_FALSE_NEGATIVE
        if cost < best_cost:
            best_cost = cost
            best_thr = thr
    return best_thr


# ============================================================
# MAIN
# ============================================================


def main():
    print("Loading graph data...")
    data = load_graph_data()

    ground_truth = pd.read_csv(GROUND_TRUTH_PATH)
    ground_truth[ID_COL] = ground_truth[ID_COL].astype(str)

    data = create_masks(data, ground_truth)
    data = data.to(DEVICE)

    model = FraudSAGE(
        in_channels=data.x.size(1),
        hidden_channels=64,
        num_layers=2,
        dropout=0.3,
    ).to(DEVICE)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=5e-4)

    print("Training GNN...")
    model = train(model, data, optimizer, epochs=200, patience=15)

    best_thr = select_threshold(model, data, data.val_mask)
    print(f"Optimal threshold from validation: {best_thr:.3f}")

    train_metrics = evaluate(model, data, data.train_mask, threshold=best_thr)
    val_metrics = evaluate(model, data, data.val_mask, threshold=best_thr)
    test_metrics = evaluate(model, data, data.test_mask, threshold=best_thr)

    torch.save(model.state_dict(), GNN_MODEL_PATH)
    metrics_summary = {
        "train": {k: v for k, v in train_metrics.items()},
        "val": {k: v for k, v in val_metrics.items()},
        "test": {k: v for k, v in test_metrics.items()},
    }
    with open(GNN_METRICS_PATH, "w") as f:
        json.dump(metrics_summary, f, indent=2)

    print("\nGNN Results:")
    for split_name, m in [
        ("Train", train_metrics),
        ("Val", val_metrics),
        ("Test", test_metrics),
    ]:
        print(f"\n{split_name}:")
        print(f"  Precision: {m['precision']:.4f}")
        print(f"  Recall:    {m['recall']:.4f}")
        print(f"  F1:        {m['f1']:.4f}")
        print(
            f"  Accuracy:  {(m['tp'] + m['tn']) / (m['tp'] + m['tn'] + m['fp'] + m['fn']):.4f}"
        )
        print(f"  ROC-AUC:   {m['roc_auc']:.4f}")
        print(f"  PR-AUC:    {m['pr_auc']:.4f}")
        print(f"  Cost:      ₹{m['cost']:,.0f}")
        print(f"  Threshold: {m['threshold']:.3f}")
        print(
            f"  Confusion Matrix: [[TN={m['tn']}, FP={m['fp']}], [FN={m['fn']}, TP={m['tp']}]]"
        )


if __name__ == "__main__":
    main()
