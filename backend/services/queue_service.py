import pandas as pd
from typing import List

from backend.domain.account import AccountRisk
from backend.repositories.explainability_repository import ExplainabilityRepository


class QueueService:
    def __init__(self, repository: ExplainabilityRepository):
        self.repository = repository

    async def get_queue(self, limit: int = 7) -> List[AccountRisk]:
        actions_df = self.repository.get_actions()

        # Single source of truth:
        # bounded_actions_test.csv already contains:
        # account_id, rank, proba, risk_tier, recommended_action
        actions_df = actions_df.sort_values("rank")

        return [
            AccountRisk(
                account_id=row["account_id"],
                rank=int(row["rank"]),
                proba=float(row["proba"]),
                risk_tier=row["risk_tier"],
                recommended_action=row["recommended_action"],
            )
            for _, row in actions_df.head(limit).iterrows()
        ]
