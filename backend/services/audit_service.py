from backend.repositories.explainability_repository import ExplainabilityRepository


class AuditService:
    def __init__(self, explainability_repo: ExplainabilityRepository):
        self.explainability_repo = explainability_repo

    async def get_audit_log(self) -> list[dict]:
        audit_df = self.explainability_repo.get_audit()
        return audit_df.to_dict(orient="records")