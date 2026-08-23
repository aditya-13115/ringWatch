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

# Raw input paths
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
