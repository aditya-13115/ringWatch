from typing import Any
from fastapi import HTTPException

import numpy as np
import pandas as pd

from backend.repositories.explainability_repository import ExplainabilityRepository
from backend.repositories.feature_repository import FeatureRepository
from backend.services.graph_service import GraphService
from backend.services.evidence_service import EvidenceService
from backend.services.action_service import ActionService
from backend.services.report_service import ReportService
from backend.services.action_service import ACTION_MAP, risk_tier_for_rank

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

        result: dict[str, Any] = {
            "account_id": str(account_id),
            "rank": rank,
            "rank_total": rank_total,
            "model_version": model_version,
            "proba": float(row["proba"]),
            "risk_tier": risk_tier_for_rank(rank),
            "recommended_action": ACTION_MAP[risk_tier_for_rank(rank)]["action_description"],
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