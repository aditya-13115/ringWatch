import uuid
from datetime import datetime, timezone

from backend.core.config import get_settings
from backend.core.concurrency import LLM_SEMAPHORE
from backend.repositories.explainability_repository import ExplainabilityRepository
from backend.repositories.feature_repository import FeatureRepository
from backend.services.action_service import ActionService


class LLMInvestigatorService:
    def __init__(self, explainability_repo, feature_repo, action_service):
        self.explainability_repo = explainability_repo
        self.feature_repo = feature_repo
        self.action_service = action_service
        self.settings = get_settings()

    async def investigate(self, account_id: str) -> dict:
        async with LLM_SEMAPHORE:
            # Check if API key exists
            if not self.settings.anthropic_api_key:
                # Fallback deterministic report
                return self._fallback_deterministic(account_id)

            # Real LLM implementation would go here.
            # For now, we return a stub with deterministic content.
            return self._fallback_deterministic(account_id)

    def _fallback_deterministic(self, account_id: str) -> dict:
        # Gather data from repositories
        actions_df = self.explainability_repo.get_actions()
        reports_df = self.explainability_repo.get_reports()
        evidence_df = self.explainability_repo.get_evidence()
        graph_df = self.explainability_repo.get_graph_evidence()
        shap_df = self.explainability_repo.get_shap()
        features_df = self.feature_repo.get_features()

        row = actions_df[actions_df["account_id"] == account_id].iloc[0]
        report_row = reports_df[reports_df["account_id"] == account_id].iloc[0]
        evidence_row = evidence_df[evidence_df["account_id"] == account_id].iloc[0]
        graph_row = graph_df[graph_df["account_id"] == account_id].iloc[0]
        shap_row = shap_df[shap_df["account_id"] == account_id].iloc[0]
        feat_row = features_df[features_df["account_id"] == account_id].iloc[0]

        # Generate simple summary from deterministic data
        summary = f"Account {account_id} is ranked #{row['rank']} with risk tier {row['risk_tier']}."
        key_findings = [
            f"Graph links: {graph_row['total_graph_links']}",
            f"Risk score: {row['proba']:.6f}",
        ]
        evidence_gaps = []
        if not evidence_row["has_dispute_at_cutoff"]:
            evidence_gaps.append("No dispute observed at cutoff; no evidence required yet.")
        else:
            # Add missing fields
            missing = [f for f, v in evidence_row.items() if v == "MISSING"]
            evidence_gaps.extend(missing)

        uncertainties = [
            "Model score is not a calibrated probability.",
            "SHAP values indicate model contribution, not causality.",
        ]

        tool_calls = []  # In real implementation, list tool calls with timestamps.

        return {
            "account_id": account_id,
            "source": "deterministic",
            "summary": summary,
            "key_findings": key_findings,
            "evidence_gaps": evidence_gaps,
            "uncertainties": uncertainties,
            "tool_calls": tool_calls,
            "recommended_action": row["recommended_action"],
            "action_source": "deterministic_policy",
        }