import json
from pathlib import Path


class MetricsService:
    def __init__(self, model_metrics_path: Path, explainability_repo):
        self.model_metrics_path = model_metrics_path
        self.explainability_repo = explainability_repo

    async def get_metrics(self) -> dict:
        with open(self.model_metrics_path, "r") as f:
            model_metrics = json.load(f)

        # Add investigation counts from actions
        actions_df = self.explainability_repo.get_actions()
        tier_counts = actions_df["risk_tier"].value_counts().to_dict()

        return {
            "model_metrics": model_metrics,
            "investigation_summary": {
                "total": len(actions_df),
                "tier_counts": tier_counts,
            },
        }
