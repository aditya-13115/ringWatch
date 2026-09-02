from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "RingWatch API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api"
    frontend_origin: str = "http://localhost:5173"

    general_concurrency: int = 10
    llm_concurrency: int = 3
    address_llm_concurrency: int = 2

    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    # Razorpay
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None

    # Anthropic
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"

    # Groq
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    # Primary operational fraud model
    # RingWatch uses the V4 Ensemble for production scoring.
    # The ensemble is LightGBM B (tuned) + GNN.
    primary_model: str = "Ensemble_LGBM_B_GNN"

    # V4 Ensemble operating threshold
    primary_model_threshold: float = 0.6831313131313131

    # LightGBM A tuned is retained only for feature-ablation
    # sensitivity analysis. It is NOT the primary operating model.
    ablation_model_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "model"
        / "model_lgbm_A_tuned.pkl"
    )

    # V4 dataset
    data_dir: Path = PROJECT_ROOT / "data" / "v4_realistic_30k"

    processed_dir: Path = PROJECT_ROOT / "data" / "v4_realistic_30k" / "processed"

    explainability_dir: Path = (
        PROJECT_ROOT / "data" / "v4_realistic_30k" / "processed" / "explainability"
    )

    model_dir: Path = PROJECT_ROOT / "data" / "v4_realistic_30k" / "processed" / "model"

    model_predictions_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "model"
        / "model_predictions_test.csv"
    )

    baseline_metrics_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "baseline_metrics.json"
    )

    # Ring-level candidate detector artifacts
    ring_model_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "model"
        / "ring_model_lgbm.pkl"
    )
    ring_candidates_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "model"
        / "ring_candidates.csv"
    )
    ring_metrics_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "model"
        / "ring_metrics.json"
    )

    feature_ablation_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "model"
        / "feature_ablation_test.json"
    )

    # V4 tuned benchmark metrics
    model_metrics_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "model"
        / "model_metrics_tuned.json"
    )

    # V4 feature matrices
    features_accounts_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "features_accounts.csv"
    )

    features_graph_path: Path = (
        PROJECT_ROOT / "data" / "v4_realistic_30k" / "processed" / "features_graph.csv"
    )

    # V4 community assignments
    communities_path: Path = (
        PROJECT_ROOT / "data" / "v4_realistic_30k" / "processed" / "communities.csv"
    )

    # V4 graph
    account_graph_edges_path: Path = (
        PROJECT_ROOT
        / "data"
        / "v4_realistic_30k"
        / "processed"
        / "account_graph_edges.csv"
    )

    # V4 addresses
    addresses_path: Path = PROJECT_ROOT / "data" / "v4_realistic_30k" / "addresses.csv"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
