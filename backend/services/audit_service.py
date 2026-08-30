import hashlib
import json

import pandas as pd

from backend.repositories.explainability_repository import (
    ExplainabilityRepository,
)


class AuditService:
    @staticmethod
    def _stable_hash(payload: dict) -> str:
        canonical = json.dumps(
            payload, sort_keys=True, default=str, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def __init__(self, explainability_repo: ExplainabilityRepository):
        self.explainability_repo = explainability_repo
        from backend.core.config import get_settings

        self.settings = get_settings()

    async def clear_audit_log(self):
        audit_path = self.explainability_repo.audit_path

        try:
            # Keep the file valid CSV even when empty.
            columns = [
                "timestamp",
                "account_id",
                "model_version",
                "rank",
                "proba",
                "risk_tier",
                "recommended_action",
                "action_recommended",
                "top_k_flag",
                "case_report_generated",
                "investigation_source",
                "tool_calls",
                "summary",
                "action_source",
                "error",
                "input_data_hash",
                "threshold_used",
                "feature_snapshot",
                "evidence_subgraph",
                "human_decision",
                "outcome",
                "error_path",
            ]

            pd.DataFrame(columns=columns).to_csv(
                audit_path,
                index=False,
            )

        except Exception as e:
            raise e

    async def get_audit_log(self) -> list[dict]:
        """
        Return the CURRENT audit log.

        This deliberately rereads the CSV through the repository because
        LLM investigations can append rows while the server is running.
        """

        audit_df = self.explainability_repo.get_audit()

        if audit_df.empty:
            return []

        records = []

        for _, row in audit_df.iterrows():

            def safe_float(value, default=None):
                if value is None:
                    return default

                try:
                    if pd.isna(value):
                        return default

                    return float(value)

                except (TypeError, ValueError):
                    return default

            def safe_int(value, default=0):
                if value is None:
                    return default

                try:
                    if pd.isna(value):
                        return default

                    return int(float(value))

                except (TypeError, ValueError):
                    return default

            def safe_bool(value, default=False):
                if value is None:
                    return default

                if isinstance(value, bool):
                    return value

                if pd.isna(value):
                    return default

                if isinstance(value, str):
                    return value.strip().lower() in {
                        "true",
                        "1",
                        "yes",
                        "y",
                    }

                return bool(value)

            def safe_str(value, default=""):
                if value is None:
                    return default

                try:
                    if pd.isna(value):
                        return default
                except (TypeError, ValueError):
                    pass

                return str(value)

            # ---------------------------------------------------------
            # IMPORTANT:
            # Old prediction CSV uses "recommended_action"
            # New LLM rows use "action_recommended".
            #
            # Normalize both into the API field:
            # "action_recommended"
            # ---------------------------------------------------------

            action_recommended = ""

            if "action_recommended" in audit_df.columns:
                action_recommended = safe_str(
                    row.get("action_recommended"),
                    "",
                )

            if not action_recommended and "recommended_action" in audit_df.columns:
                action_recommended = safe_str(
                    row.get("recommended_action"),
                    "",
                )

            timestamp = safe_str(row.get("timestamp"))
            account_id = safe_str(row.get("account_id"))
            model_version = safe_str(
                row.get("model_version"),
                "Ensemble_LGBM_B_GNN",
            )
            proba = safe_float(row.get("proba"))
            rank = safe_int(row.get("rank"))
            risk_tier = safe_str(row.get("risk_tier"), "UNKNOWN")

            # Build a stable, non-PII audit reference from the decision context.
            hash_payload = {
                "timestamp": timestamp,
                "account_id": account_id,
                "model_version": model_version,
                "proba": proba,
                "rank": rank,
                "risk_tier": risk_tier,
                "action": action_recommended,
            }
            input_data_hash = self._stable_hash(hash_payload)

            feature_snapshot = {
                key: row.get(key)
                for key in row.index
                if key
                in {
                    "proba",
                    "rank",
                    "risk_tier",
                    "top_k_flag",
                    "recommended_action",
                    "action_recommended",
                }
            }
            feature_snapshot = {
                key: (None if pd.isna(value) else value)
                for key, value in feature_snapshot.items()
            }

            evidence_subgraph = None
            if account_id:
                try:
                    graph_df = self.explainability_repo.get_graph_evidence()
                    graph_row = graph_df[
                        graph_df["account_id"].astype(str) == account_id
                    ]
                    if not graph_row.empty:
                        graph_record = graph_row.iloc[0].to_dict()
                        graph_record = {
                            key: (None if pd.isna(value) else value)
                            for key, value in graph_record.items()
                        }
                        evidence_subgraph = json.dumps(
                            graph_record, default=str, sort_keys=True
                        )
                except Exception:
                    evidence_subgraph = None

            error_value = safe_str(row.get("error"), "")
            action_text = action_recommended.lower()
            human_decision = (
                "PENDING_HUMAN_REVIEW"
                if any(
                    token in action_text for token in ("review", "hold", "verification")
                )
                else "NOT_RECORDED"
            )
            outcome = (
                "ERROR"
                if error_value
                else (
                    "PENDING_REVIEW"
                    if human_decision == "PENDING_HUMAN_REVIEW"
                    else "RECORDED"
                )
            )

            record = {
                "timestamp": timestamp,
                "account_id": account_id,
                "model_version": model_version,
                "proba": proba,
                "rank": rank,
                "risk_tier": risk_tier,
                "top_k_flag": safe_bool(
                    row.get("top_k_flag"),
                    False,
                ),
                "action_recommended": action_recommended,
                "case_report_generated": safe_bool(
                    row.get("case_report_generated"),
                    False,
                ),
            }

            # ---------------------------------------------------------
            # LLM investigation fields
            # ---------------------------------------------------------

            if "investigation_source" in audit_df.columns:
                record["investigation_source"] = safe_str(
                    row.get("investigation_source"),
                    "",
                )

            if "tool_calls" in audit_df.columns:
                record["tool_calls"] = safe_str(
                    row.get("tool_calls"),
                    "",
                )

            if "summary" in audit_df.columns:
                record["summary"] = safe_str(
                    row.get("summary"),
                    "",
                )

            if "action_source" in audit_df.columns:
                record["action_source"] = safe_str(
                    row.get("action_source"),
                    "",
                )

            if "error" in audit_df.columns:
                error_value = safe_str(
                    row.get("error"),
                    "",
                )

                if error_value:
                    record["error"] = error_value

            record["input_data_hash"] = input_data_hash
            record["threshold_used"] = self.settings.primary_model_threshold
            record["feature_snapshot"] = json.dumps(
                feature_snapshot, default=str, sort_keys=True
            )
            record["evidence_subgraph"] = evidence_subgraph
            record["human_decision"] = human_decision
            record["outcome"] = outcome
            record["error_path"] = error_value or "none"

            records.append(record)

        return records
