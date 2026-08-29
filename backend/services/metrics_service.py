import json
from pathlib import Path

import numpy as np
import pandas as pd

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
        self.model_metrics_path = Path(model_metrics_path)
        self.explainability_repo = explainability_repo
        self.settings = get_settings()

        # All V4 model artifacts live in the same directory.
        self.model_dir = self.model_metrics_path.parent

        self.ensemble_metrics_path = (
            self.model_dir / "ensemble_metrics.json"
        )

        self.gnn_metrics_path = (
            self.model_dir / "gnn_metrics.json"
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _load_json(path: Path) -> dict:
        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _safe_float(value, default=None):
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    # ---------------------------------------------------------
    # Main metrics endpoint
    # ---------------------------------------------------------

    async def get_metrics(self) -> dict:
        """
        Return the complete V4 model evaluation payload.

        The backend exposes:
          - LightGBM Model A
          - LightGBM Model B
          - GNN
          - Ensemble
          - Baseline
          - Investigation summary
        """

        # Existing tuned LightGBM metrics.
        model_metrics = self._load_json(self.model_metrics_path)

        # New V4 artifacts.
        ensemble_metrics = self._load_json(
            self.ensemble_metrics_path
        )

        gnn_metrics = self._load_json(
            self.gnn_metrics_path
        )

        # -----------------------------------------------------
        # Investigation summary
        # -----------------------------------------------------

        try:
            actions_df = self.explainability_repo.get_actions()

            if "risk_tier" in actions_df.columns:
                tier_counts = (
                    actions_df["risk_tier"]
                    .value_counts()
                    .to_dict()
                )
            else:
                tier_counts = {}

            investigation_summary = {
                "total": len(actions_df),
                "tier_counts": tier_counts,
            }

        except Exception:
            investigation_summary = {
                "total": 0,
                "tier_counts": {},
            }

        # -----------------------------------------------------
        # Extract LightGBM metrics
        # -----------------------------------------------------

        model_a = model_metrics.get("model_A", {})
        model_b = model_metrics.get("model_B", {})

        model_a_test = model_a.get("test", model_a)
        model_b_test = model_b.get("test", model_b)

        baseline = (
            model_metrics.get("baseline_test")
            or model_metrics.get("baseline")
            or {}
        )

        # -----------------------------------------------------
        # Normalize ensemble metrics
        #
        # ensemble_metrics.json is already the V4 ensemble
        # evaluation object.
        # -----------------------------------------------------

        ensemble = {
            "threshold": self._safe_float(
                ensemble_metrics.get("threshold")
            ),
            "precision": self._safe_float(
                ensemble_metrics.get("precision")
            ),
            "recall": self._safe_float(
                ensemble_metrics.get("recall")
            ),
            "f1": self._safe_float(
                ensemble_metrics.get("f1")
            ),
            "accuracy": self._safe_float(
                ensemble_metrics.get("accuracy")
            ),
            "roc_auc": self._safe_float(
                ensemble_metrics.get("roc_auc")
            ),
            "pr_auc": self._safe_float(
                ensemble_metrics.get("pr_auc")
            ),
            "cost": self._safe_float(
                ensemble_metrics.get("cost")
            ),
            "confusion_matrix": ensemble_metrics.get(
                "confusion_matrix",
                {},
            ),
        }

        # -----------------------------------------------------
        # Normalize GNN metrics
        #
        # gnn_metrics.json contains train/val/test metrics.
        # The frontend uses TEST metrics for comparison.
        # -----------------------------------------------------

        gnn_test = gnn_metrics.get("test", {})

        gnn = {
            "threshold": self._safe_float(
                gnn_test.get("threshold")
            ),
            "precision": self._safe_float(
                gnn_test.get("precision")
            ),
            "recall": self._safe_float(
                gnn_test.get("recall")
            ),
            "f1": self._safe_float(
                gnn_test.get("f1")
            ),
            "accuracy": self._safe_float(
                gnn_test.get("accuracy")
            ),
            "roc_auc": self._safe_float(
                gnn_test.get("roc_auc")
            ),
            "pr_auc": self._safe_float(
                gnn_test.get("pr_auc")
            ),
            "cost": self._safe_float(
                gnn_test.get("cost")
            ),
            "tp": gnn_test.get("tp"),
            "fp": gnn_test.get("fp"),
            "tn": gnn_test.get("tn"),
            "fn": gnn_test.get("fn"),
        }

        # -----------------------------------------------------
        # Return API contract
        # -----------------------------------------------------

        return {
            "model_metrics": model_metrics,

            "models": {
                "model_A": model_a_test,
                "model_B": model_b_test,
                "gnn": gnn,
                "ensemble": ensemble,
                "baseline": baseline,
            },

            "operating_model": {
                "name": "V4 Ensemble",
                "description": (
                    "Current RingWatch operating model using "
                    "the V4 ensemble evaluation."
                ),
                "threshold": ensemble["threshold"],
            },

            "ensemble_metrics": ensemble_metrics,

            "gnn_metrics": gnn_metrics,

            "investigation_summary": investigation_summary,
        }

    # ---------------------------------------------------------
    # Curves
    # ---------------------------------------------------------

    async def get_curves(self) -> dict:
        """
        Compute top-K precision/recall/cost curves from the
        saved V4 test predictions.

        Supported models:
            - Baseline
            - LightGBM A
            - LightGBM B
            - GNN
            - V4 Ensemble

        Expected prediction columns:
            baseline:
                pred_baseline

            LightGBM A:
                proba_A

            LightGBM B:
                proba_B

            GNN:
                proba_GNN / proba_gnn

            Ensemble:
                proba_ensemble / ensemble_proba /
                proba_Ensemble
        """

        preds_path = Path(self.settings.model_predictions_path)

        if not preds_path.exists():
            return {}

        try:
            df = pd.read_csv(preds_path)
        except Exception:
            return {}

        if "true_label" not in df.columns:
            return {}

        true = (
            pd.to_numeric(
                df["true_label"],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
            .to_numpy()
        )

        # ---------------------------------------------------------
        # Prediction column aliases
        # ---------------------------------------------------------

        candidate_columns = {
            "baseline": [
                "pred_baseline",
            ],
            "model_A": [
                "proba_A",
            ],
            "model_B": [
                "proba_B",
            ],
            "gnn": [
                "proba_GNN",
                "proba_gnn",
                "gnn_proba",
                "gnn_probability",
            ],
            "ensemble": [
                "proba_ensemble",
                "ensemble_proba",
                "proba_Ensemble",
                "ensemble_probability",
            ],
        }

        curves = {}

        # ---------------------------------------------------------
        # Helper: find first available prediction column
        # ---------------------------------------------------------

        def find_prediction_column(columns):
            for column in columns:
                if column in df.columns:
                    return column
            return None

        # ---------------------------------------------------------
        # Build curves
        # ---------------------------------------------------------

        for model_key, possible_columns in candidate_columns.items():

            proba_col = find_prediction_column(
                possible_columns
            )

            if proba_col is None:
                continue

            # -----------------------------------------------------
            # Convert prediction/ranking values to numeric
            # -----------------------------------------------------

            proba = (
                pd.to_numeric(
                    df[proba_col],
                    errors="coerce",
                )
                .fillna(0.0)
                .to_numpy(dtype=float)
            )

            # -----------------------------------------------------
            # Sort accounts from highest risk to lowest risk
            # -----------------------------------------------------

            order = np.argsort(
                -proba,
                kind="stable",
            )

            sorted_true = true[order]

            n = len(sorted_true)

            # -----------------------------------------------------
            # Initialize counters
            # -----------------------------------------------------

            precision_curve = []
            recall_curve = []
            cost_curve = []

            tp = 0
            fp = 0

            total_positive = int(
                sorted_true.sum()
            )

            fn = total_positive

            # -----------------------------------------------------
            # Top-K evaluation
            # -----------------------------------------------------

            for k in range(1, n + 1):

                label = sorted_true[k - 1]

                if label == 1:
                    tp += 1
                    fn -= 1
                else:
                    fp += 1

                # Precision
                precision = (
                    tp / (tp + fp)
                    if (tp + fp) > 0
                    else 0.0
                )

                # Recall
                recall = (
                    tp / (tp + fn)
                    if (tp + fn) > 0
                    else 0.0
                )

                # Intervention cost
                cost = (
                    fp * COST_FP
                    + fn * COST_FN
                )

                precision_curve.append(
                    {
                        "k": k,
                        "value": round(
                            precision,
                            4,
                        ),
                    }
                )

                recall_curve.append(
                    {
                        "k": k,
                        "value": round(
                            recall,
                            4,
                        ),
                    }
                )

                cost_curve.append(
                    {
                        "k": k,
                        "value": round(
                            cost,
                            2,
                        ),
                    }
                )

            curves[model_key] = {
                "precision": precision_curve,
                "recall": recall_curve,
                "cost": cost_curve,
            }

        return curves