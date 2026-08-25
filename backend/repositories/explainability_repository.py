from pathlib import Path

import pandas as pd


class ExplainabilityRepository:

    def __init__(self, explainability_dir: Path):
        self.explainability_dir = explainability_dir

        self.actions = pd.read_csv(
            explainability_dir / "bounded_actions_test.csv"
        )

        self.reports = pd.read_csv(
            explainability_dir / "case_reports_test.csv"
        )

        self.evidence = pd.read_csv(
            explainability_dir / "evidence_gap_test.csv"
        )

        self.graph_evidence = pd.read_csv(
            explainability_dir / "graph_evidence_test.csv"
        )

        self.audit = pd.read_csv(
            explainability_dir / "investigation_audit_log.csv"
        )

        self.shap = pd.read_csv(
            explainability_dir / "shap_values_test.csv"
        )

    def get_actions(self) -> pd.DataFrame:
        return self.actions.copy()

    def get_reports(self) -> pd.DataFrame:
        return self.reports.copy()

    def get_evidence(self) -> pd.DataFrame:
        return self.evidence.copy()

    def get_graph_evidence(self) -> pd.DataFrame:
        return self.graph_evidence.copy()

    def get_audit(self) -> pd.DataFrame:
        return self.audit.copy()

    def get_shap(self) -> pd.DataFrame:
        return self.shap.copy()