from dataclasses import dataclass
from pathlib import Path

from backend.core.config import get_settings


@dataclass
class DataStore:
    """Container for all paths and loaded data used by services."""

    explainability_dir: Path
    features_graph_path: Path
    model_metrics_path: Path
    addresses_path: Path

    # You can add more paths as needed
    account_graph_edges_path: Path
    features_accounts_path: Path


def load_data() -> DataStore:
    """Validate and load required data paths.

    This function does NOT read all CSVs into memory yet.
    Repositories will load what they need lazily.

    However, we do check that the required files exist so the API
    fails fast at startup if something is missing.
    """
    settings = get_settings()

    required_files = [
        settings.explainability_dir / "bounded_actions_test.csv",
        settings.explainability_dir / "case_reports_test.csv",
        settings.explainability_dir / "evidence_gap_test.csv",
        settings.explainability_dir / "graph_evidence_test.csv",
        settings.explainability_dir / "investigation_audit_log.csv",
        settings.explainability_dir / "shap_values_test.csv",
        settings.model_predictions_path,
        settings.model_metrics_path,
        settings.features_graph_path,
        settings.addresses_path,
    ]

    missing = [f for f in required_files if not f.exists()]
    if missing:
        raise FileNotFoundError(
            "Required RingWatch data files missing: "
            + ", ".join(str(f) for f in missing)
        )

    return DataStore(
        explainability_dir=settings.explainability_dir,
        features_graph_path=settings.features_graph_path,
        model_metrics_path=settings.model_metrics_path,
        addresses_path=settings.addresses_path,
        account_graph_edges_path=settings.account_graph_edges_path,
        features_accounts_path=settings.features_accounts_path,
    )
