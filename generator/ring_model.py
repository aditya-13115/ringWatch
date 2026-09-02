"""Ring-level candidate detection layered on top of the existing account model.

This module intentionally does not replace the existing account-level LightGBM/GNN.
It creates small, model-assisted graph candidates from high-risk accounts, aggregates
account + relationship evidence into one row per candidate ring, trains a LightGBM
ring detector, and evaluates it without using ground truth as a model feature.

The candidate-generation threshold is fixed and must not be tuned on the test set.
The ring model threshold is selected on validation only.
"""

from __future__ import annotations

import json
import pickle
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import networkx as nx
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .features_config import (
    FEATURES_GRAPH_PATH,
    GROUND_TRUTH_PATH,
    MODEL_DIR,
    PREDICTIONS_TEST_PATH,
    PATHS,
)

SEED = 42
CANDIDATE_SEED_THRESHOLD = 0.70
MIN_CANDIDATE_SIZE = 2
STRONG_EDGE_MIN_WEIGHT = 0.70
COST_FP = 2_000.0
COST_FN = 15_000.0

RING_FEATURES_PATH = MODEL_DIR / "ring_features.csv"
RING_CANDIDATES_PATH = MODEL_DIR / "ring_candidates.csv"
RING_PREDICTIONS_ALL_PATH = MODEL_DIR / "ring_predictions_all.csv"
RING_PREDICTIONS_TEST_PATH = MODEL_DIR / "ring_predictions_test.csv"
RING_MODEL_PATH = MODEL_DIR / "ring_model_lgbm.pkl"
RING_METRICS_PATH = MODEL_DIR / "ring_metrics.json"
RING_FEATURE_IMPORTANCE_PATH = MODEL_DIR / "ring_feature_importance.csv"
RING_LEAKAGE_REPORT_PATH = MODEL_DIR / "ring_leakage_report.txt"

ID_COL = "account_id"
RING_ID_COL = "abuse_ring_id"
TRUE_MEMBER_COL = "true_ring_member"


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def _json_list(values: Iterable[str]) -> str:
    return json.dumps(sorted({str(v) for v in values}), separators=(",", ":"))


def load_inputs():
    features = pd.read_csv(FEATURES_GRAPH_PATH, low_memory=False)
    edges = pd.read_csv(
        PATHS["accounts"].parent / "processed" / "account_graph_edges.csv",
        low_memory=False,
    )
    communities = pd.read_csv(
        PATHS["accounts"].parent / "processed" / "communities.csv", low_memory=False
    )
    gt = pd.read_csv(GROUND_TRUTH_PATH, low_memory=False)

    features[ID_COL] = features[ID_COL].astype(str)
    edges["account_id_1"] = edges["account_id_1"].astype(str)
    edges["account_id_2"] = edges["account_id_2"].astype(str)
    communities[ID_COL] = communities[ID_COL].astype(str)
    gt[ID_COL] = gt[ID_COL].astype(str)

    with open(MODEL_DIR / "model_lgbm_B_tuned.pkl", "rb") as f:
        account_model = pickle.load(f)

    feature_columns = list(account_model.feature_name_)
    missing = [c for c in feature_columns if c not in features.columns]
    if missing:
        raise KeyError(f"features_graph.csv missing account-model columns: {missing}")

    features = features.copy()
    features["account_proba"] = account_model.predict_proba(features[feature_columns])[
        :, 1
    ]

    return features, edges, communities, gt


def build_candidate_graph(features: pd.DataFrame, edges: pd.DataFrame) -> nx.Graph:
    """Build small strong-link components from high-risk account seeds."""
    seed_ids = set(
        features.loc[
            features["account_proba"] >= CANDIDATE_SEED_THRESHOLD,
            ID_COL,
        ].astype(str)
    )

    strong = edges[edges["weight"] >= STRONG_EDGE_MIN_WEIGHT].copy()
    strong = strong[
        strong["account_id_1"].isin(seed_ids) & strong["account_id_2"].isin(seed_ids)
    ]

    graph = nx.Graph()
    graph.add_nodes_from(seed_ids)
    graph.add_edges_from(
        (
            row.account_id_1,
            row.account_id_2,
            {"edge_type": row.edge_type, "weight": float(row.weight)},
        )
        for row in strong.itertuples(index=False)
    )
    return graph


def build_candidates(
    features: pd.DataFrame,
    edges: pd.DataFrame,
    communities: pd.DataFrame,
) -> pd.DataFrame:
    graph = build_candidate_graph(features, edges)

    feature_lookup = features.set_index(ID_COL)
    community_lookup = dict(
        zip(communities[ID_COL].astype(str), communities["community_id"])
    )

    rows: list[dict] = []

    for idx, component in enumerate(
        (c for c in nx.connected_components(graph) if len(c) >= MIN_CANDIDATE_SIZE),
        start=1,
    ):
        members = sorted(map(str, component))
        sub_edges = edges[
            edges["account_id_1"].isin(members)
            & edges["account_id_2"].isin(members)
            & (edges["weight"] >= STRONG_EDGE_MIN_WEIGHT)
        ].copy()

        scores = pd.to_numeric(
            feature_lookup.loc[members, "account_proba"], errors="coerce"
        ).fillna(0.0)
        member_features = feature_lookup.loc[members]

        community_ids = sorted(
            {
                community_lookup.get(member)
                for member in members
                if community_lookup.get(member) is not None
            }
        )

        edge_counts = sub_edges["edge_type"].value_counts().to_dict()
        weights = pd.to_numeric(sub_edges["weight"], errors="coerce").fillna(0.0)

        row = {
            "candidate_id": f"RING-C{idx:04d}",
            "member_ids": _json_list(members),
            "member_count": len(members),
            "mean_account_risk": float(scores.mean()),
            "median_account_risk": float(scores.median()),
            "max_account_risk": float(scores.max()),
            "min_account_risk": float(scores.min()),
            "std_account_risk": float(scores.std(ddof=0)),
            "p90_account_risk": float(scores.quantile(0.90)),
            "internal_edge_count": int(len(sub_edges)),
            "internal_edge_density": _safe_div(
                len(sub_edges),
                len(members) * (len(members) - 1) / 2,
            ),
            "mean_edge_weight": float(weights.mean()) if len(weights) else 0.0,
            "max_edge_weight": float(weights.max()) if len(weights) else 0.0,
            "shared_device_edges": int(edge_counts.get("shares_device", 0)),
            "shared_address_edges": int(edge_counts.get("shares_address", 0)),
            "shared_phone_edges": int(edge_counts.get("shares_phone", 0)),
            "shared_payment_edges": int(
                edge_counts.get("shares_payment_instrument", 0)
            ),
            "shared_ip_edges": int(edge_counts.get("shares_ip_prefix", 0)),
            "shared_coupon_edges": int(edge_counts.get("shares_coupon", 0)),
            "candidate_community_count": int(len(community_ids)),
            "source_community_ids": _json_list(community_ids),
        }

        aggregations = {
            "total_orders": "sum",
            "total_amount": "sum",
            "avg_order_value": "mean",
            "total_returns": "sum",
            "return_rate": "mean",
            "return_rate_last_30d": "mean",
            "total_refunds": "sum",
            "total_refund_amount": "sum",
            "refund_rate": "mean",
            "total_disputes": "sum",
            "dispute_rate": "mean",
            "transaction_burst_score": "mean",
            "refund_burst_score": "mean",
            "account_creation_burst_score": "mean",
            "discount_dependency_score": "mean",
            "shared_entity_types_count": "mean",
            "shared_edge_weight_sum": "mean",
            "community_return_rate": "mean",
            "community_refund_rate": "mean",
            "community_avg_order_value": "mean",
        }
        for column, func in aggregations.items():
            values = pd.to_numeric(member_features[column], errors="coerce").fillna(0.0)
            row[f"ring_{column}_{func}"] = float(getattr(values, func)())

        rows.append(row)

    return pd.DataFrame(rows)


def _ring_label_and_ids(
    candidates: pd.DataFrame,
    gt: pd.DataFrame,
) -> pd.DataFrame:
    gt_lookup = gt.set_index(ID_COL)
    labels = []
    ring_sets = []

    for member_ids_json in candidates["member_ids"]:
        member_ids = json.loads(member_ids_json)
        member_gt = gt_lookup.reindex(member_ids)
        ring_members = member_gt[member_gt[TRUE_MEMBER_COL] == 1]
        counts = ring_members[RING_ID_COL].value_counts(dropna=True)
        counts = counts[counts >= 2]
        labels.append(int(len(counts) > 0))
        ring_sets.append(sorted(map(str, counts.index.tolist())))

    out = candidates.copy()
    out["is_abuse_ring"] = labels
    out["positive_ring_ids"] = [_json_list(v) for v in ring_sets]
    return out


def assign_groups(candidates: pd.DataFrame) -> pd.DataFrame:
    """Keep all candidates from the same true ring in one split group.

    This is used only for evaluation/training construction. Ground-truth ring IDs
    are never passed into the model as a feature.
    """
    seen_groups: dict[str, int] = {}
    group_ids = []
    next_group = 0

    for _, row in candidates.iterrows():
        rings = json.loads(row["positive_ring_ids"])
        if rings:
            existing = [seen_groups[r] for r in rings if r in seen_groups]
            if existing:
                group_id = min(existing)
            else:
                group_id = next_group
                next_group += 1
            for ring_id in rings:
                seen_groups[ring_id] = group_id
            group_ids.append(f"ring-group-{group_id}")
        else:
            group_ids.append(f"negative-{next_group}")
            next_group += 1

    out = candidates.copy()
    out["split_group"] = group_ids
    return out


def split_candidates(
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Deterministic grouped 70/15/15 split.

    Positive ring groups are assigned as indivisible groups; negative candidates
    each have an independent group. No candidate belonging to the same abuse ring
    can cross train/validation/test.
    """
    groups = pd.DataFrame(
        {
            "split_group": candidates["split_group"].unique(),
        }
    )

    rng = np.random.default_rng(SEED)
    groups = groups.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    n = len(groups)
    n_train = max(1, int(round(n * 0.70)))
    n_val = max(1, int(round(n * 0.15)))
    if n_train + n_val >= n:
        n_train = max(1, n - 2)
        n_val = 1

    train_groups = set(groups.iloc[:n_train]["split_group"])
    val_groups = set(groups.iloc[n_train : n_train + n_val]["split_group"])
    test_groups = set(groups.iloc[n_train + n_val :]["split_group"])

    train = candidates[candidates["split_group"].isin(train_groups)].copy()
    val = candidates[candidates["split_group"].isin(val_groups)].copy()
    test = candidates[candidates["split_group"].isin(test_groups)].copy()

    return train, val, test


def get_model_features(candidates: pd.DataFrame) -> list[str]:
    excluded = {
        "candidate_id",
        "member_ids",
        "is_abuse_ring",
        "positive_ring_ids",
        "split_group",
        "source_community_ids",
    }
    return [c for c in candidates.columns if c not in excluded]


def choose_threshold(y_true: np.ndarray, proba: np.ndarray) -> float:
    best_threshold = 0.5
    best_cost = float("inf")
    for threshold in np.linspace(0.01, 0.99, 197):
        pred = (proba >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
        cost = fp * COST_FP + fn * COST_FN
        if cost < best_cost:
            best_cost = float(cost)
            best_threshold = float(threshold)
    return best_threshold


def evaluate(y_true: np.ndarray, proba: np.ndarray, threshold: float) -> dict:
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    metrics = {
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "roc_auc": (
            float(roc_auc_score(y_true, proba)) if len(np.unique(y_true)) > 1 else 0.0
        ),
        "pr_auc": (
            float(average_precision_score(y_true, proba))
            if len(np.unique(y_true)) > 1
            else 0.0
        ),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "cost": float(fp * COST_FP + fn * COST_FN),
    }
    return metrics


def train_and_evaluate(candidates: pd.DataFrame):
    feature_columns = get_model_features(candidates)
    train, val, test = split_candidates(candidates)

    X_train = train[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y_train = train["is_abuse_ring"].astype(int)
    X_val = val[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y_val = val["is_abuse_ring"].astype(int)
    X_test = test[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y_test = test["is_abuse_ring"].astype(int)

    model = LGBMClassifier(
        objective="binary",
        random_state=SEED,
        n_estimators=350,
        learning_rate=0.035,
        num_leaves=31,
        max_depth=6,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        class_weight="balanced",
        verbosity=-1,
    )
    model.fit(X_train, y_train)

    val_proba = model.predict_proba(X_val)[:, 1]
    threshold = choose_threshold(y_val.to_numpy(), val_proba)

    all_X = (
        candidates[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    )
    candidates = candidates.copy()
    candidates["ring_proba"] = model.predict_proba(all_X)[:, 1]
    candidates["ring_pred"] = (candidates["ring_proba"] >= threshold).astype(int)

    test_mask = candidates["candidate_id"].isin(test["candidate_id"])
    test_out = candidates.loc[test_mask].copy()

    metrics = {
        "candidate_generation": {
            "seed_threshold": CANDIDATE_SEED_THRESHOLD,
            "strong_edge_min_weight": STRONG_EDGE_MIN_WEIGHT,
            "candidate_count": int(len(candidates)),
            "candidate_positive_count": int(candidates["is_abuse_ring"].sum()),
        },
        "split": {
            "train_candidates": int(len(train)),
            "validation_candidates": int(len(val)),
            "test_candidates": int(len(test)),
            "train_positive": int(y_train.sum()),
            "validation_positive": int(y_val.sum()),
            "test_positive": int(y_test.sum()),
        },
        "validation": evaluate(y_val.to_numpy(), val_proba, threshold),
        "test": evaluate(
            y_test.to_numpy(),
            (
                test["ring_proba"].to_numpy()
                if "ring_proba" in test.columns
                else model.predict_proba(X_test)[:, 1]
            ),
            threshold,
        ),
        "costs": {"false_positive": COST_FP, "false_negative": COST_FN},
        "model_features": feature_columns,
    }

    importance = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)

    # Ring-level coverage is evaluated against true rings, not candidate rows.
    gt_ring_ids = set(pd.read_csv(GROUND_TRUTH_PATH)[RING_ID_COL].dropna().astype(str))
    ring_detected = defaultdict(bool)
    for _, row in test_out[test_out["ring_pred"] == 1].iterrows():
        for ring_id in json.loads(row["positive_ring_ids"]):
            ring_detected[ring_id] = True
    test_true_rings = set(r for r in test["positive_ring_ids"] for r in json.loads(r))
    metrics["test_ring_coverage"] = {
        "candidate_generator_represented_true_rings": len(
            set(r for r in candidates["positive_ring_ids"] for r in json.loads(r))
        ),
        "candidate_generator_total_true_rings": len(gt_ring_ids),
        "test_true_rings": len(test_true_rings),
        "test_detected_true_rings": int(
            sum(ring_detected.get(r, False) for r in test_true_rings)
        ),
        "test_ring_recall": _safe_div(
            sum(ring_detected.get(r, False) for r in test_true_rings),
            len(test_true_rings),
        ),
    }

    return model, candidates, metrics, importance


def write_artifacts(candidates, model, metrics, importance):
    RING_CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(RING_CANDIDATES_PATH, index=False)
    candidates.to_csv(RING_FEATURES_PATH, index=False)
    candidates.to_csv(RING_PREDICTIONS_ALL_PATH, index=False)

    split_test = candidates[
        candidates["split_group"].isin(set(candidates["split_group"].unique()))
    ].copy()
    # Recompute the test split deterministically for the saved test artifact.
    _, _, test = split_candidates(candidates)
    test_ids = set(test["candidate_id"])
    candidates[candidates["candidate_id"].isin(test_ids)].to_csv(
        RING_PREDICTIONS_TEST_PATH, index=False
    )

    with open(RING_MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    importance.to_csv(RING_FEATURE_IMPORTANCE_PATH, index=False)
    with open(RING_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    forbidden = [
        "true_ring_member",
        "abuse_ring_id",
        "ring_type",
        "ring_start_time",
        "ring_end_time",
        "positive_ring_ids",
        "split_group",
    ]
    used_features = set(metrics["model_features"])
    violations = sorted(used_features.intersection(forbidden))
    report = [
        "RingWatch ring-level model leakage report",
        "===========================================",
        f"Candidate seed threshold: {CANDIDATE_SEED_THRESHOLD}",
        f"Strong-edge threshold: {STRONG_EDGE_MIN_WEIGHT}",
        f"Model features: {len(used_features)}",
        f"Forbidden feature violations: {violations or 'NONE'}",
        "Ground-truth fields are used for labels/split grouping only.",
        "Candidate ring IDs are never passed into the model.",
        "Ring model threshold is selected on validation only.",
        "Same positive ring IDs are kept inside one grouped split.",
        "",
        "Important limitation:",
        "Candidate generation is model-assisted and therefore ring-level recall is",
        "bounded by the existing account model and strong-edge candidate generator.",
    ]
    RING_LEAKAGE_REPORT_PATH.write_text("\n".join(report), encoding="utf-8")


def main():
    print("Loading inputs...")
    features, edges, communities, gt = load_inputs()
    print("Building ring candidates...")
    candidates = build_candidates(features, edges, communities)
    candidates = _ring_label_and_ids(candidates, gt)
    candidates = assign_groups(candidates)

    if candidates["is_abuse_ring"].nunique() < 2:
        raise RuntimeError(
            "Ring candidates do not contain both positive and negative examples."
        )

    print(
        f"Candidates: {len(candidates):,} | positives: {int(candidates['is_abuse_ring'].sum()):,}"
    )
    model, predictions, metrics, importance = train_and_evaluate(candidates)
    write_artifacts(predictions, model, metrics, importance)

    print("\nRing-level test metrics")
    print(json.dumps(metrics["test"], indent=2))
    print("\nRing coverage")
    print(json.dumps(metrics["test_ring_coverage"], indent=2))
    print(f"\nArtifacts written to {MODEL_DIR}")


if __name__ == "__main__":
    main()
