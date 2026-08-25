import pandas as pd

from backend.repositories.explainability_repository import ExplainabilityRepository


class AuditService:
    def __init__(self, explainability_repo: ExplainabilityRepository):
        self.explainability_repo = explainability_repo

    async def get_audit_log(self) -> list[dict]:
        audit_df = self.explainability_repo.get_audit()
        records = []

        for _, row in audit_df.iterrows():
            def safe_float(value, default=0.0):
                return float(value) if pd.notna(value) else default

            def safe_int(value, default=0):
                return int(value) if pd.notna(value) else default

            def safe_str(value, default=""):
                return str(value) if pd.notna(value) else default

            record = {
                "timestamp": safe_str(row.get("timestamp")),
                "account_id": safe_str(row.get("account_id")),
                "model_version": safe_str(row.get("model_version")),
                "proba": safe_float(row.get("proba")),
                "rank": safe_int(row.get("rank")),
                "risk_tier": safe_str(row.get("risk_tier"), "UNKNOWN"),
                "top_k_flag": bool(row.get("top_k_flag", False)),
                "action_recommended": safe_str(row.get("action_recommended")),
                "case_report_generated": bool(row.get("case_report_generated", False)),
            }

            # Optional investigation fields
            if "investigation_source" in audit_df.columns:
                record["investigation_source"] = safe_str(row.get("investigation_source"))
            if "tool_calls" in audit_df.columns:
                record["tool_calls"] = safe_str(row.get("tool_calls"))
            if "summary" in audit_df.columns:
                record["summary"] = safe_str(row.get("summary"))
            if "action_source" in audit_df.columns:
                record["action_source"] = safe_str(row.get("action_source"))

            records.append(record)

        return records