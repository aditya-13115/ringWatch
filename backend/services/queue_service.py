import pandas as pd
from typing import List
from backend.domain.account import AccountRisk
from backend.repositories.explainability_repository import ExplainabilityRepository
from backend.core.config import get_settings


class QueueService:
    def __init__(self, repository: ExplainabilityRepository):
        self.repository = repository
        self.settings = get_settings()

    async def get_queue(self, limit: int = 7) -> List[AccountRisk]:
        # Existing actions CSV has top-K accounts with full data
        actions_df = self.repository.get_actions()
        actions_df = actions_df.sort_values("rank")

        if limit <= len(actions_df):
            # Return from actions CSV directly
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

        # If limit > available actions, load all predictions and rank them
        predictions_path = self.settings.model_predictions_path
        predictions = pd.read_csv(predictions_path)
        predictions = predictions.sort_values("proba", ascending=False)
        predictions["rank"] = range(1, len(predictions) + 1)

        queue = []
        for _, row in predictions.head(limit).iterrows():
            rank = int(row["rank"])
            # Determine tier and action based on rank thresholds
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
        if rank == 1:
            return "CRITICAL", "Soft-hold refund pending human approval"
        elif rank == 2:
            return "HIGH", "Route to human review"
        elif rank <= 5:
            return "MEDIUM", "Step-up verification on refund"
        else:
            return "LOW", "Monitor — no immediate refund action"
