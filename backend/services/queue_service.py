import pandas as pd
from typing import List

from backend.domain.account import AccountRisk
from backend.repositories.explainability_repository import ExplainabilityRepository
from backend.services.action_service import ACTION_MAP, tier_from_row


class QueueService:
    def __init__(self, repository: ExplainabilityRepository):
        self.repository = repository

    async def get_queue(self, limit: int = 10) -> List[AccountRisk]:
        actions_df = self.repository.get_actions()
        actions_df = actions_df.sort_values("rank")

        queue = []

        for _, row in actions_df.head(limit).iterrows():
            rank = int(row["rank"])

            # Always derive the operational tier/action from rank.
            # This prevents stale persisted tiers in bounded_actions_test.csv
            # from overriding the current queue policy.
            risk_tier, recommended_action = self._rank_to_action(rank)

            queue.append(
                AccountRisk(
                    account_id=row["account_id"],
                    rank=rank,
                    proba=float(row["proba"]),
                    risk_tier=risk_tier,
                    recommended_action=recommended_action,
                )
            )

        return queue

    def _rank_to_action(self, rank: int) -> tuple[str, str]:
        if rank <= 10:
            return (
                "CRITICAL",
                "Soft-hold refund pending human approval",
            )
        elif rank <= 25:
            return (
                "HIGH",
                "Route to human investigation/review",
            )
        elif rank <= 65:
            return (
                "MEDIUM",
                "Require step-up verification before processing refund",
            )
        else:
            return (
                "LOW",
                "Monitor — no immediate refund action",
            )
