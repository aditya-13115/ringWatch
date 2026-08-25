from typing import Any

import pandas as pd

from backend.domain.account import AccountDetail
from backend.repositories.explainability_repository import ExplainabilityRepository
from backend.repositories.feature_repository import FeatureRepository
from backend.services.graph_service import GraphService
from backend.services.evidence_service import EvidenceService
from backend.services.action_service import ActionService
from backend.services.report_service import ReportService


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

    async def get_account_detail(self, account_id: str) -> AccountDetail:
        # Fetch from repositories
        actions_df = self.explainability_repo.get_actions()
        reports_df = self.explainability_repo.get_reports()
        shap_df = self.explainability_repo.get_shap()
        features_df = self.feature_repo.get_features()

        # Filter for the account
        action_row = actions_df[actions_df["account_id"] == account_id]
        report_row = reports_df[reports_df["account_id"] == account_id]
        shap_row = shap_df[shap_df["account_id"] == account_id]
        feature_row = features_df[features_df["account_id"] == account_id]

        if action_row.empty:
            raise ValueError(f"Account {account_id} not found in actions")

        rank = int(action_row.iloc[0]["rank"])
        proba = float(action_row.iloc[0]["proba"])
        risk_tier = action_row.iloc[0]["risk_tier"]
        recommended_action = action_row.iloc[0]["recommended_action"]

        # Graph evidence
        graph_evidence = await self.graph_service.get_graph_evidence(account_id)

        # Evidence status
        evidence_status = await self.evidence_service.get_evidence_status(account_id)

        # Case report text
        case_report_text = await self.report_service.get_case_report(account_id)

        # Top SHAP features
        top_shap = self._get_top_shap_features(shap_row, top_n=5)

        # Observed behavioral facts (subset from features_graph)
        observed_facts = {}
        if not feature_row.empty:
            fact_cols = [
                "total_orders",
                "return_rate",
                "refund_rate",
                "dispute_rate",
                "shared_device_count",
                "shared_ip_prefix_count",
                "community_size",
            ]
            for col in fact_cols:
                if col in feature_row.columns:
                    observed_facts[col] = feature_row.iloc[0][col]

        return AccountDetail(
            account_id=account_id,
            rank=rank,
            proba=proba,
            risk_tier=risk_tier,
            recommended_action=recommended_action,
            observed_facts=observed_facts,
            top_shap_features=top_shap,
            graph_evidence=graph_evidence,
            evidence_status=evidence_status,
            case_report_text=case_report_text,
        )

    def _get_top_shap_features(self, shap_row: pd.DataFrame, top_n: int = 5) -> list[dict]:
        if shap_row.empty:
            return []

        # shap_row is one-row DataFrame with columns: account_id, rank, proba, top_k_flag, + feature columns
        feature_cols = [c for c in shap_row.columns if c not in ["account_id", "rank", "proba", "top_k_flag"]]
        values = shap_row.iloc[0][feature_cols]
        # Sort by absolute value descending
        sorted_features = sorted(feature_cols, key=lambda c: abs(values[c]), reverse=True)
        result = []
        for feat in sorted_features[:top_n]:
            result.append({"feature": feat, "shap_value": float(values[feat])})
        return result