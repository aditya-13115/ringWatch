"""V4 realism / anti-shortcut audit.

This module audits single-feature discriminability on both raw aggregate signals
and the final Day-4/Day-5 feature matrices.

It is intentionally independent of the model-training pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .config import PATHS
from .features_config import PREDICTION_CUTOFF, FEATURES_PATH, FEATURES_GRAPH_PATH, GROUND_TRUTH_PATH


def _auc_safe(y_true, scores):
    """Compute |AUC| safely; returns 0.5 if not enough positive/negative samples."""
    if len(np.unique(y_true)) < 2:
        return 0.5
    try:
        auc = roc_auc_score(y_true, scores)
        return max(auc, 1 - auc)
    except ValueError:
        return 0.5


def audit_feature_matrix(features_df, ground_truth_df, feature_cols_to_ignore=None):
    """Compute single-feature AUC for all numeric columns in features_df."""
    if feature_cols_to_ignore is None:
        feature_cols_to_ignore = {"account_id", "true_ring_member", "population_type"}
    y = ground_truth_df.set_index("account_id")["true_ring_member"].astype(int)
    df = features_df.copy()
    # Ensure alignment
    df = df[df["account_id"].isin(y.index)]
    df = df.set_index("account_id")
    df = df.reindex(y.index)
    df["true_ring_member"] = y
    candidates = [c for c in df.columns if c not in feature_cols_to_ignore and c != "true_ring_member"]
    rows = []
    for col in candidates:
        if df[col].dtype not in [np.float64, np.int64, np.float32, np.int32]:
            # try to convert
            try:
                vals = pd.to_numeric(df[col], errors="coerce").fillna(0)
            except Exception:
                continue
        else:
            vals = df[col].fillna(0)
        if vals.nunique() < 2:
            continue
        auc = _auc_safe(y.values, vals.values)
        rows.append({"feature": col, "single_feature_auc": round(auc, 6), "unique_values": int(vals.nunique())})
    out = pd.DataFrame(rows).sort_values("single_feature_auc", ascending=False)
    return out


def build_raw_signals():
    """Compute a set of raw aggregate signals (as in current version)."""
    cutoff = pd.Timestamp(PREDICTION_CUTOFF)
    accounts = pd.read_csv(PATHS["accounts"])
    # Load private population labels
    private_accounts = pd.read_csv(PATHS["accounts"].parent / "account_population_labels_private.csv")
    accounts = accounts.merge(private_accounts, on="account_id", how="left")

    orders = pd.read_csv(PATHS["orders"], low_memory=False)
    orders["order_timestamp"] = pd.to_datetime(orders["order_timestamp"], errors="coerce")
    orders = orders[orders.order_timestamp <= cutoff].copy()
    gt = pd.read_csv(PATHS["ring_ground_truth"])
    g = orders.groupby("account_id")
    s = g.agg(
        total_orders=("order_id", "count"),
        total_amount=("amount", "sum"),
        avg_order_value=("amount", "mean"),
        return_rate=("return_flag", "mean"),
        refund_rate=("refund_flag", "mean"),
        dispute_rate=("dispute_flag", "mean"),
        distinct_devices=("device_id", "nunique"),
        distinct_addresses=("address_id", "nunique"),
        distinct_phones=("phone_hash", "nunique"),
        distinct_instruments=("instrument_id", "nunique"),
    ).reset_index()
    coupon_usage = g["coupon_code"].apply(lambda x: x.notna().mean()).rename("coupon_usage_rate")
    s = s.merge(coupon_usage, on="account_id", how="left")
    s = accounts[["account_id", "population_type"]].merge(s, on="account_id", how="left").fillna(0)
    s = s.merge(gt[["account_id", "true_ring_member"]], on="account_id", how="left")
    return s


def run():
    # 1. Raw signals audit (as before)
    raw_df = build_raw_signals()
    y = raw_df.true_ring_member.astype(int)
    candidates = [c for c in raw_df.columns if c not in {"account_id", "population_type", "true_ring_member"}]
    rows = []
    for c in candidates:
        vals = pd.to_numeric(raw_df[c], errors="coerce").fillna(0)
        if vals.nunique() < 2:
            continue
        auc = _auc_safe(y.values, vals.values)
        rows.append({"feature": c, "single_feature_auc": round(auc, 6), "unique_values": int(vals.nunique())})
    raw_audit = pd.DataFrame(rows).sort_values("single_feature_auc", ascending=False)

    # 2. Final feature audits
    gt = pd.read_csv(GROUND_TRUTH_PATH)
    final_audits = {}
    for name, path in [("Day4", FEATURES_PATH), ("Day5", FEATURES_GRAPH_PATH)]:
        if Path(path).exists():
            feats = pd.read_csv(path)
            audit_df = audit_feature_matrix(feats, gt)
            final_audits[name] = audit_df
            print(f"\n{name} features single-feature AUC (top 10):")
            print(audit_df.head(10).to_string(index=False))
            print(f"{name} max AUC: {audit_df.single_feature_auc.max():.4f}")
        else:
            final_audits[name] = None
            print(f"{name} feature file not found, skipped.")

    # Determine overall max AUC across raw and final features
    all_aucs = [raw_audit.single_feature_auc.max()] if len(raw_audit) else [0.5]
    for df in final_audits.values():
        if df is not None and len(df) > 0:
            all_aucs.append(df.single_feature_auc.max())
    max_auc = max(all_aucs)

    # Decision threshold: maximum single-feature AUC should be <= 0.80
    threshold = 0.80
    passed = max_auc <= threshold

    payload = {
        "cutoff": str(PREDICTION_CUTOFF),
        "raw_signal_audit": raw_audit.to_dict("records"),
        "day4_feature_audit": final_audits.get("Day4").to_dict("records") if final_audits.get("Day4") is not None else None,
        "day5_feature_audit": final_audits.get("Day5").to_dict("records") if final_audits.get("Day5") is not None else None,
        "max_single_feature_auc": float(max_auc),
        "threshold": threshold,
        "anti_shortcut_passed": bool(passed),
    }

    # Save report
    report_path = Path(PATHS["accounts"]).parent / "processed" / "v4_quality_audit_extended.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\nV4 extended quality audit")
    print("=" * 45)
    print(f"Raw signals max AUC: {raw_audit.single_feature_auc.max():.4f}" if len(raw_audit) else "Raw signals: no features")
    if final_audits.get("Day4") is not None:
        print(f"Day4 features max AUC: {final_audits['Day4'].single_feature_auc.max():.4f}")
    if final_audits.get("Day5") is not None:
        print(f"Day5 features max AUC: {final_audits['Day5'].single_feature_auc.max():.4f}")
    print(f"Overall max single-feature AUC: {max_auc:.4f}")
    print(f"Anti-shortcut check (threshold {threshold}): {'PASSED' if passed else 'FAILED'}")
    return payload


if __name__ == "__main__":
    run()