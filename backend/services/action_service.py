from backend.domain.action import BoundedAction
from backend.repositories.explainability_repository import ExplainabilityRepository


ACTION_MAP = {
    "LOW": {
        "action_code": "NO_ACTION",
        "action_description": "Monitor — no immediate refund action",
        "requires_human_review": False,
    },
    "MEDIUM": {
        "action_code": "STEP_UP_REFUND_VERIFICATION",
        "action_description": "Require step-up verification before processing refund",
        "requires_human_review": True,
    },
    "HIGH": {
        "action_code": "ROUTE_TO_HUMAN_REVIEW",
        "action_description": "Route to human investigation/review",
        "requires_human_review": True,
    },
    "CRITICAL": {
        "action_code": "SOFT_HOLD_REFUND_PENDING_HUMAN_APPROVAL",
        "action_description": "Soft-hold refund pending human approval",
        "requires_human_review": True,
    },
}


class ActionService:
    def __init__(self, explainability_repo: ExplainabilityRepository):
        self.explainability_repo = explainability_repo

    async def get_action(self, account_id: str) -> BoundedAction:
        actions_df = self.explainability_repo.get_actions()
        row = actions_df[actions_df["account_id"] == account_id]

        if row.empty:
            raise ValueError(f"Account {account_id} not found")

        row = row.iloc[0]
        tier = row["risk_tier"]
        map_entry = ACTION_MAP.get(tier, ACTION_MAP["LOW"])

        return BoundedAction(
            account_id=account_id,
            risk_tier=tier,
            action_code=map_entry["action_code"],
            action_description=map_entry["action_description"],
            requires_human_review=map_entry["requires_human_review"],
        )