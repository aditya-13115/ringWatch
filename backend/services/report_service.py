from backend.repositories.explainability_repository import ExplainabilityRepository


class ReportService:
    def __init__(self, explainability_repo: ExplainabilityRepository):
        self.explainability_repo = explainability_repo

    async def get_case_report(self, account_id: str) -> str:
        reports_df = self.explainability_repo.get_reports()
        row = reports_df[reports_df["account_id"] == account_id]

        if row.empty:
            return "No case report available."

        return str(row.iloc[0]["case_report_text"])