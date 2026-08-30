"""Generate a reproducible held-out feature-sensitivity benchmark.

This does not retrain the model and does not change the operational V4 Ensemble.
It uses the tuned LightGBM A component retained for model-sensitivity analysis.
"""

from pathlib import Path
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix

from .features_config import PROCESSED_DIR

COST_FP = 2_000.0
COST_FN = 15_000.0
THRESHOLD = 0.6039393939393939


def evaluate(y_true, proba):
    pred = (proba >= THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "cost": float(fp * COST_FP + fn * COST_FN),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }


def main():
    proc = PROCESSED_DIR
    model = pickle.load(open(proc / "model" / "model_lgbm_A_tuned.pkl", "rb"))
    features = pd.read_csv(proc / "features_accounts.csv")
    preds = pd.read_csv(proc / "model" / "model_predictions_test.csv")
    shap = pd.read_csv(proc / "explainability" / "shap_values_test.csv")
    features["account_id"] = features["account_id"].astype(str)
    preds["account_id"] = preds["account_id"].astype(str)
    shap["account_id"] = shap["account_id"].astype(str)

    test = (
        features[features.account_id.isin(preds.account_id)]
        .set_index("account_id")
        .loc[preds.account_id]
        .reset_index()
    )
    cols = list(model.feature_name_)
    X = test[cols].copy()
    y = preds["true_label"].astype(int).to_numpy()
    original = model.predict_proba(X)[:, 1]
    baseline = evaluate(y, original)

    ranked = []
    for col in cols:
        shap_col = f"A_{col}"
        if shap_col in shap.columns:
            ranked.append((col, float(shap[shap_col].abs().mean())))
    ranked.sort(key=lambda x: x[1], reverse=True)

    medians = X.median(numeric_only=True)
    rows = []
    for feature, mean_abs_shap in ranked[:10]:
        ablated = X.copy()
        ablated[feature] = medians[feature]
        proba = model.predict_proba(ablated)[:, 1]
        metrics = evaluate(y, proba)
        rows.append(
            {
                "feature": feature,
                "mean_abs_shap": mean_abs_shap,
                "mean_score_delta": float((proba - original).mean()),
                "mean_abs_score_delta": float(np.abs(proba - original).mean()),
                **metrics,
            }
        )

    out = {
        "model_version": "LightGBM_Model_A_Tuned",
        "threshold": THRESHOLD,
        "test_accounts": int(len(test)),
        "method": "Replace one feature at a time with its test-population median and rescore the held-out accounts. This is model sensitivity, not causal attribution.",
        "baseline": baseline,
        "features": rows,
    }
    path = proc / "model" / "feature_ablation_test.json"
    path.write_text(json.dumps(out, indent=2))
    print(path)


if __name__ == "__main__":
    main()
