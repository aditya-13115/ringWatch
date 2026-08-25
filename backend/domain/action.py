from dataclasses import dataclass


@dataclass
class BoundedAction:
    account_id: str
    risk_tier: str
    action_code: str
    action_description: str
    requires_human_review: bool