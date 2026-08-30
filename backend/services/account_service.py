from typing import Any
from fastapi import HTTPException
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
from backend.core.config import get_settings
from backend.repositories.explainability_repository import ExplainabilityRepository
from backend.repositories.feature_repository import FeatureRepository
from backend.services.graph_service import GraphService
from backend.services.evidence_service import EvidenceService
from backend.services.action_service import ActionService
from backend.services.report_service import ReportService
from backend.services.action_service import ACTION_MAP, tier_from_row

EVIDENCE_FIELDS = [
    "proof_of_service",
    "explanation_letter",
    "refund_confirmation",
    "access_activity_log",
    "refund_cancellation_policy",
    "terms_and_conditions",
]


def _to_python(value: Any) -> Any:
    """Convert NumPy types to native Python types."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


class AccountService:
    def __init__(
        self,
        explainability_repo: ExplainabilityRepository,
        feature_repo: FeatureRepository,
        graph_service: GraphService,
        evidence_service: EvidenceService,
        action_service: ActionService,
        report_service: ReportService,
    ):
        self.explainability_repo = explainability_repo
        self.feature_repo = feature_repo
        self.graph_service = graph_service
        self.evidence_service = evidence_service
        self.action_service = action_service
        self.report_service = report_service

    def _load_ablation_model(self):
        settings = get_settings()

        if not settings.ablation_model_path.exists():
            raise FileNotFoundError(
                f"Ablation model not found: " f"{settings.ablation_model_path}"
            )

        with open(settings.ablation_model_path, "rb") as f:
            return pickle.load(f)

    async def get_feature_ablation(
        self,
        account_id: str,
    ) -> dict[str, Any]:
        """
        Perform model-faithful feature ablation for the
        LightGBM A component used for sensitivity analysis.

        This is NOT the primary RingWatch operating model.

        A feature is ablated by replacing its account value
        with the median value observed in the Model A feature
        population, then rescoring with the same trained model.

        This measures model sensitivity to the feature. It is
        not a causal claim.
        """

        settings = get_settings()

        features_path = settings.features_accounts_path

        if not features_path.exists():
            raise FileNotFoundError(
                f"Ablation feature matrix not found: " f"{features_path}"
            )

        features_df = pd.read_csv(features_path)

        if "account_id" not in features_df.columns:
            raise KeyError("features_accounts.csv missing account_id")

        features_df["account_id"] = features_df["account_id"].astype(str)

        account_rows = features_df[features_df["account_id"] == str(account_id)]

        if account_rows.empty:
            raise KeyError(
                f"Account {account_id} not found " f"in the ablation feature matrix"
            )

        model = self._load_ablation_model()

        model_features = list(
            getattr(
                model,
                "feature_name_",
                [],
            )
        )

        if not model_features:
            model_features = [
                column for column in features_df.columns if column != "account_id"
            ]

        missing_features = [
            feature for feature in model_features if feature not in features_df.columns
        ]

        if missing_features:
            raise KeyError(
                "Ablation model features missing from feature matrix: "
                + ", ".join(missing_features)
            )

        X_population = features_df[model_features].copy()

        X_account = features_df.loc[
            account_rows.index,
            model_features,
        ].copy()

        original_score = float(model.predict_proba(X_account)[0][1])

        shap_df = self.explainability_repo.get_shap()

        shap_row = shap_df[shap_df["account_id"].astype(str) == str(account_id)]

        if shap_row.empty:
            return {
                "account_id": str(account_id),
                "model_version": "LightGBM_Model_A_Tuned",
                "original_score": original_score,
                "ablations": [],
                "note": ("No SHAP explanation is available " "for this account."),
            }

        shap_row = shap_row.iloc[0]

        candidates = []

        for column in shap_df.columns:
            if not column.startswith("A_"):
                continue

            feature_name = column[2:]

            if feature_name not in model_features:
                continue

            try:
                shap_value = float(shap_row[column])
            except (TypeError, ValueError):
                continue

            if not np.isfinite(shap_value):
                continue

            candidates.append(
                {
                    "feature": feature_name,
                    "shap_value": shap_value,
                    "abs_shap": abs(shap_value),
                }
            )

        candidates.sort(
            key=lambda item: item["abs_shap"],
            reverse=True,
        )

        ablations = []

        for candidate in candidates[:5]:
            feature = candidate["feature"]

            X_ablated = X_account.copy()

            median_value = pd.to_numeric(
                X_population[feature],
                errors="coerce",
            ).median()

            if pd.isna(median_value):
                median_value = 0.0

            X_ablated.loc[
                X_ablated.index[0],
                feature,
            ] = median_value

            ablated_score = float(model.predict_proba(X_ablated)[0][1])

            delta = ablated_score - original_score

            ablations.append(
                {
                    "feature": feature,
                    "shap_value": candidate["shap_value"],
                    "original_score": original_score,
                    "ablated_score": ablated_score,
                    "score_delta": delta,
                    "absolute_score_change": abs(delta),
                    "ablation_method": "population_median",
                }
            )

        return {
            "account_id": str(account_id),
            "model_version": "LightGBM_Model_A_Tuned",
            "original_score": original_score,
            "ablations": ablations,
            "note": (
                "Feature ablation measures sensitivity of the "
                "trained model to individual features. It is "
                "not evidence of real-world causality."
            ),
        }

    async def get_account_detail(self, account_id: str) -> dict[str, Any]:
        actions_df = self.explainability_repo.get_actions()
        action_row = actions_df[actions_df["account_id"] == account_id]

        if action_row.empty:
            raise HTTPException(
                status_code=404,
                detail="Account not found",
            )

        row = action_row.iloc[0]

        # ---------------------------------------------------------
        # Queue/model metadata
        # ---------------------------------------------------------

        rank = int(row["rank"])

        # bounded_actions_test.csv contains the complete flagged
        # investigation queue.
        rank_total = int(len(actions_df))

        # Current V4 production scoring model.
        # Keep this centralized in the backend rather than hard-coding
        # the display name in React.
        model_version = "Ensemble_LGBM_B_GNN"
        risk_tier = tier_from_row(row)

        result: dict[str, Any] = {
            "account_id": str(account_id),
            "rank": rank,
            "rank_total": rank_total,
            "model_version": model_version,
            "proba": float(row["proba"]),
            "risk_tier": risk_tier,
            "recommended_action": ACTION_MAP[risk_tier]["action_description"],
            "observed_facts": {},
            "top_shap_features": [],
            "graph_evidence": {
                "total_graph_links": 0,
                "strongest_edge_type": None,
                "strongest_edge_weight": None,
                "number_of_device_links": 0,
                "number_of_ip_links": 0,
                "number_of_coupon_links": 0,
                "linked_accounts": [],
            },
            "evidence_status": {
                "has_dispute_at_cutoff": False,
                "fields": {field: "NO_DISPUTE_YET" for field in EVIDENCE_FIELDS},
                "missing_evidence_count": None,
            },
            "case_report_text": "No case report available.",
        }

        # ---------------------------------------------------------
        # Graph evidence
        # ---------------------------------------------------------

        try:
            graph_evidence = await self.graph_service.get_graph_evidence(account_id)

            result["graph_evidence"] = _to_python(graph_evidence)

        except Exception:
            pass

        # ---------------------------------------------------------
        # Evidence status
        # ---------------------------------------------------------

        try:
            evidence = await self.evidence_service.get_evidence_status(account_id)

            result["evidence_status"] = {
                "has_dispute_at_cutoff": bool(evidence.has_dispute_at_cutoff),
                "fields": {key: str(value) for key, value in evidence.fields.items()},
                "missing_evidence_count": _to_python(evidence.missing_evidence_count),
            }

        except Exception:
            pass

        # ---------------------------------------------------------
        # Case report
        # ---------------------------------------------------------

        try:
            result["case_report_text"] = await self.report_service.get_case_report(
                account_id
            )

        except Exception:
            pass

        # ---------------------------------------------------------
        # SHAP
        # ---------------------------------------------------------

        try:
            shap_df = self.explainability_repo.get_shap()

            shap_row = shap_df[shap_df["account_id"] == account_id]

            if not shap_row.empty:

                feature_cols = [
                    column
                    for column in shap_df.columns
                    if column
                    not in [
                        "account_id",
                        "rank",
                        "proba",
                        "top_k_flag",
                    ]
                ]

                values = shap_row.iloc[0][feature_cols]

                sorted_features = sorted(
                    feature_cols,
                    key=lambda column: abs(float(values[column])),
                    reverse=True,
                )

                result["top_shap_features"] = [
                    {
                        "feature": feature,
                        "shap_value": float(values[feature]),
                    }
                    for feature in sorted_features[:5]
                ]

        except Exception:
            pass

        # ---------------------------------------------------------
        # Observed facts
        # ---------------------------------------------------------

        try:
            features_df = self.feature_repo.get_features()

            feature_row = features_df[features_df["account_id"] == account_id]

            if not feature_row.empty:

                fact_cols = [
                    "total_orders",
                    "total_amount",
                    "total_refunds",
                    "total_refund_amount",
                    "return_rate",
                    "refund_rate",
                    "dispute_rate",
                    "shared_device_count",
                    "shared_ip_prefix_count",
                    "community_size",
                    "total_returns",
                ]

                for column in fact_cols:

                    if column in feature_row.columns:

                        result["observed_facts"][column] = _to_python(
                            feature_row.iloc[0][column]
                        )

        except Exception:
            pass

        return result
