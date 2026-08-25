from pathlib import Path

import pandas as pd


class FeatureRepository:
    """Provides access to the feature matrices used by the dashboard."""

    def __init__(self, features_graph_path: Path):
        self.features_graph = pd.read_csv(features_graph_path)

    def get_features(self) -> pd.DataFrame:
        """Return the graph features DataFrame."""
        return self.features_graph.copy()

    def get_account_row(self, account_id: str) -> pd.Series:
        """Return a single account's feature row."""
        row = self.features_graph[self.features_graph["account_id"] == account_id]
        if row.empty:
            raise KeyError(f"Account {account_id} not found in features")
        return row.iloc[0]
