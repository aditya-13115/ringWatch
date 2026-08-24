from pathlib import Path

# ------------------------------------------------------------
# Day 4 Feature Engineering Configuration
# ------------------------------------------------------------

PREDICTION_CUTOFF = "2026-02-20 00:00:00"

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Raw data directory
DATA_DIR = PROJECT_ROOT / "data"

# Processed feature output directory
PROCESSED_DIR = DATA_DIR / "processed"

# Create processed directory automatically
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Output paths
FEATURES_PATH = PROCESSED_DIR / "features_accounts.csv"
LEAKAGE_REPORT_PATH = PROCESSED_DIR / "leakage_report_features.txt"

# ------------------------------------------------------------
# Day 4 / Day 5 Feature Engineering Configuration
# ------------------------------------------------------------

PREDICTION_CUTOFF = "2026-02-20 00:00:00"

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Raw data directory
DATA_DIR = PROJECT_ROOT / "data"

# Processed feature output directory
PROCESSED_DIR = DATA_DIR / "processed"

# Create processed directory automatically
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DAY 4 OUTPUT PATHS
# ============================================================

FEATURES_PATH = PROCESSED_DIR / "features_accounts.csv"
LEAKAGE_REPORT_PATH = PROCESSED_DIR / "leakage_report_features.txt"


# ============================================================
# DAY 5 OUTPUT PATHS
# ============================================================

GRAPH_EDGES_PATH = PROCESSED_DIR / "account_graph_edges.csv"
COMMUNITIES_PATH = PROCESSED_DIR / "communities.csv"
FEATURES_GRAPH_PATH = PROCESSED_DIR / "features_graph.csv"
BASELINE_METRICS_PATH = PROCESSED_DIR / "baseline_metrics.json"
DAY5_LEAKAGE_REPORT_PATH = PROCESSED_DIR / "leakage_report_day5.txt"


# ============================================================
# DAY 5 EVALUATION INPUT
# ============================================================

GROUND_TRUTH_PATH = DATA_DIR / "ring_ground_truth.csv"


# ============================================================
# RAW INPUT PATHS
# ============================================================

PATHS = {
    "accounts": DATA_DIR / "accounts.csv",
    "orders": DATA_DIR / "orders.csv",
    "refunds": DATA_DIR / "refunds.csv",
    "disputes": DATA_DIR / "disputes.csv",
    "devices": DATA_DIR / "devices.csv",
    "addresses": DATA_DIR / "addresses.csv",
    "phones": DATA_DIR / "phones.csv",
    "payment_instruments": DATA_DIR / "payment_instruments.csv",
}


# ============================================================
# DAY 6–7 MODEL OUTPUTS
# ============================================================

MODEL_DIR = PROCESSED_DIR / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_A_PATH = MODEL_DIR / "model_lgbm_A.pkl"
MODEL_B_PATH = MODEL_DIR / "model_lgbm_B.pkl"

PREDICTIONS_TEST_PATH = MODEL_DIR / "model_predictions_test.csv"
MODEL_METRICS_PATH = MODEL_DIR / "model_metrics.json"
FEATURE_IMPORTANCE_PATH = MODEL_DIR / "model_feature_importance.csv"
MODEL_LEAKAGE_REPORT_PATH = MODEL_DIR / "model_leakage_report.txt"


# ============================================================
# DAY 8–9 — EXPLAINABILITY
# ============================================================

EXPLAINABILITY_DIR = PROCESSED_DIR / "explainability"
EXPLAINABILITY_DIR.mkdir(parents=True, exist_ok=True)

SHAP_VALUES_PATH = EXPLAINABILITY_DIR / "shap_values_test.csv"
SHAP_SUMMARY_PATH = EXPLAINABILITY_DIR / "shap_summary.png"

EVIDENCE_GAP_PATH = EXPLAINABILITY_DIR / "evidence_gap_test.csv"

GRAPH_EVIDENCE_PATH = EXPLAINABILITY_DIR / "graph_evidence_test.csv"

CASE_REPORTS_PATH = EXPLAINABILITY_DIR / "case_reports_test.csv"

BOUNDED_ACTIONS_PATH = EXPLAINABILITY_DIR / "bounded_actions_test.csv"

AUDIT_LOG_PATH = EXPLAINABILITY_DIR / "investigation_audit_log.csv"