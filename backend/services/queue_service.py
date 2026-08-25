from typing import Any

import pandas as pd

from backend.domain.account import AccountRisk
from backend.repositories.explainability_repository import ExplainabilityRepository


class QueueService:
    def __init__(self, repository: ExplainabilityRepository):
        self.repository = repository

    async def get_queue(self) -> list[AccountRisk]:
        actions_df = self.repository.get_actions()

        # Assume columns: account_id, rank, proba, risk_tier, recommended_action
        # Sort by rank to maintain priority order
        actions_df = actions_df.sort_values("rank")

        queue: list[AccountRisk] = []
        for _, row in actions_df.iterrows():
            queue.append(
                AccountRisk(
                    account_id=row["account_id"],
                    rank=int(row["rank"]),
                    proba=float(row["proba"]),
                    risk_tier=row["risk_tier"],
                    recommended_action=row["recommended_action"],
                )
            )
        return queue