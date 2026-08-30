from pathlib import Path

import pandas as pd


class ExplainabilityRepository:
    def __init__(self, explainability_dir: Path):
        self.explainability_dir = explainability_dir

        self.audit_path = explainability_dir / "investigation_audit_log.csv"

        self.actions_path = explainability_dir / "bounded_actions_test.csv"
        self.reports_path = explainability_dir / "case_reports_test.csv"
        self.evidence_path = explainability_dir / "evidence_gap_test.csv"
        self.graph_evidence_path = explainability_dir / "graph_evidence_test.csv"
        self.shap_path = explainability_dir / "shap_values_test.csv"

        # These are relatively static explainability artifacts.
        self.actions = self._read_csv(self.actions_path)
        self.reports = self._read_csv(self.reports_path)
        self.evidence = self._read_csv(self.evidence_path)
        self.graph_evidence = self._read_csv(self.graph_evidence_path)
        self.shap = self._read_csv(self.shap_path)

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()

        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()

    def get_actions(self) -> pd.DataFrame:
        return self.actions.copy()

    def get_reports(self) -> pd.DataFrame:
        return self.reports.copy()

    def get_evidence(self) -> pd.DataFrame:
        return self.evidence.copy()

    def get_graph_evidence(self) -> pd.DataFrame:
        return self.graph_evidence.copy()

    def get_shap(self) -> pd.DataFrame:
        return self.shap.copy()

    def get_audit(self) -> pd.DataFrame:
        """
        IMPORTANT:
        Audit log is dynamic because LLM investigations append new rows
        while the backend is already running.

        Therefore DO NOT return a DataFrame cached during __init__.
        Always reread the CSV.
        """
        return self._read_csv(self.audit_path)

    def append_audit_record(self, record: dict) -> None:
        """
        Append one audit record while preserving the existing CSV schema.
        """

        existing = self._read_csv(self.audit_path)

        new_row = pd.DataFrame([record])

        if existing.empty:
            new_row.to_csv(self.audit_path, index=False)
            return

        # Make sure both DataFrames have the same columns.
        all_columns = list(existing.columns)

        for column in new_row.columns:
            if column not in all_columns:
                all_columns.append(column)

        existing = existing.reindex(columns=all_columns)
        new_row = new_row.reindex(columns=all_columns)

        # Append through .loc instead of concatenating an all-NA column set.
        # This keeps legacy CSV columns stable and avoids pandas' dtype warning
        # when investigation-only fields are absent from historical rows.
        row_values = [new_row.iloc[0].get(column, pd.NA) for column in all_columns]
        existing = existing.astype(object)
        existing.loc[len(existing), all_columns] = row_values

        existing.to_csv(self.audit_path, index=False)
