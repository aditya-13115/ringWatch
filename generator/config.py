from pathlib import Path
import os

SEED = 42
START_DATE = "2026-01-01"
END_DATE = "2026-03-01"

DATASET_VERSION = "v3_scaled_30k"
DATA_VERSION = os.getenv("RINGWATCH_DATASET_VERSION", DATASET_VERSION)

N_ACCOUNTS = 30_000

# Exact ring configuration
N_RING_TYPES = {
    "wardrobing": 40,
    "promo_refund_farming": 30,
    "friendly_fraud": 30,
    "subtle_distributed": 40,
}

RING_ACCOUNTS_PER_TYPE = {
    "wardrobing": 8,
    "promo_refund_farming": 20,
    "friendly_fraud": 6,
    "subtle_distributed": 10,
}

N_RING_ACCOUNTS = sum(
    N_RING_TYPES[rt] * RING_ACCOUNTS_PER_TYPE[rt] for rt in N_RING_TYPES
)

NORMAL_ACCOUNT_PCT = 0.80
HARD_NEGATIVE_ACCOUNT_PCT = 0.15

N_NORMAL_ACCOUNTS = int(N_ACCOUNTS * NORMAL_ACCOUNT_PCT)
N_HARD_NEGATIVE_ACCOUNTS = N_ACCOUNTS - N_NORMAL_ACCOUNTS - N_RING_ACCOUNTS

NORMAL_ACCOUNT_START = 0
NORMAL_ACCOUNT_END = N_NORMAL_ACCOUNTS - 1

RING_ACCOUNT_START = N_NORMAL_ACCOUNTS
RING_ACCOUNT_END = RING_ACCOUNT_START + N_RING_ACCOUNTS - 1

HARD_NEGATIVE_ACCOUNT_START = RING_ACCOUNT_END + 1
HARD_NEGATIVE_ACCOUNT_END = N_ACCOUNTS - 1

N_DEVICES = int(N_ACCOUNTS * 1.2)
N_ADDRESSES = int(N_ACCOUNTS * 0.6)
N_PHONES = int(N_ACCOUNTS * 0.9)
N_INSTRUMENTS = int(N_ACCOUNTS * 1.4)

RING_START_MIN = "2026-01-05"
RING_START_MAX = "2026-02-10"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / DATA_VERSION
DATA_DIR.mkdir(parents=True, exist_ok=True)

PATHS = {
    "accounts": DATA_DIR / "accounts.csv",
    "devices": DATA_DIR / "devices.csv",
    "addresses": DATA_DIR / "addresses.csv",
    "phones": DATA_DIR / "phones.csv",
    "payment_instruments": DATA_DIR / "payment_instruments.csv",
    "orders": DATA_DIR / "orders.csv",
    "refunds": DATA_DIR / "refunds.csv",
    "disputes": DATA_DIR / "disputes.csv",
    "ring_ground_truth": DATA_DIR / "ring_ground_truth.csv",
}