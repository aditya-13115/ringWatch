import json
from pathlib import Path

import pandas as pd
import numpy as np

from backend.core.config import get_settings
from backend.repositories.explainability_repository import ExplainabilityRepository


COST_FP = 2000.0
COST_FN = 15000.0


class MetricsService:
    def __init__(
        self,
        model_metrics_path: Path,
        explainability_repo: ExplainabilityRepository,
    ):
        self.model_metrics_path = model_metrics_path
        self.explainability_repo = explainability_repo
        self.settings = get_settings()

    async def get_metrics(self) -> dict:
        with open(self.model_metrics_path, "r") as f:
            model_metrics = json.load(f)

        actions_df = self.explainability_repo.get_actions()
        tier_counts = actions_df["risk_tier"].value_counts().to_dict()

        return {
            "model_metrics": model_metrics,
            "investigation_summary": {
                "total": len(actions_df),
                "tier_counts": tier_counts,
            },
        }

    async def get_curves(self) -> dict:
        """
        Compute top-K PR curves and cost curves for Model A and Model B
        from the saved test predictions.

        Each point k = flag top-k accounts by descending model score.
        """
        preds_path = self.settings.model_predictions_path
        df = pd.read_csv(preds_path)

        true = df["true_label"].astype(int).to_numpy()

        curves = {}

        for model_key, proba_col in [
            ("model_A", "proba_A"),
            ("model_B", "proba_B"),
        ]:
            if proba_col not in df.columns:
                continue

            proba = df[proba_col].to_numpy()
            order = np.argsort(-proba)  # highest risk first
            sorted_true = true[order]

            n = len(df)
            precision_curve = []
            recall_curve = []
            cost_curve = []

            tp = 0
            fp = 0
            fn = int(sorted_true.sum())

            for k in range(1, n + 1):
                label = sorted_true[k - 1]
                if label == 1:
                    tp += 1
                    fn -= 1
                else:
                    fp += 1

                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                cost = fp * COST_FP + fn * COST_FN

                precision_curve.append(
                    {"k": k, "value": round(precision, 4)}
                )
                recall_curve.append(
                    {"k": k, "value": round(recall, 4)}
                )
                cost_curve.append(
                    {"k": k, "value": round(cost, 2)}
                )

            curves[model_key] = {
                "precision": precision_curve,
                "recall": recall_curve,
                "cost": cost_curve,
            }

        return curves