from pathlib import Path

SEED = 42

START_DATE = "2026-01-01"
END_DATE = "2026-03-01"

# ============================================================
# DEBUG DATASET
# ============================================================

N_ACCOUNTS = 1000

# ============================================================
# ACCOUNT RESERVATION
# ============================================================

NORMAL_ACCOUNT_START = 0
NORMAL_ACCOUNT_END = 799

RING_ACCOUNT_START = 800
RING_ACCOUNT_END = 899

HARD_NEGATIVE_ACCOUNT_START = 900
HARD_NEGATIVE_ACCOUNT_END = 999

N_NORMAL_ACCOUNTS = (
    NORMAL_ACCOUNT_END - NORMAL_ACCOUNT_START + 1
)

N_RING_RESERVED = (
    RING_ACCOUNT_END - RING_ACCOUNT_START + 1
)

N_HARD_NEGATIVE_RESERVED = (
    HARD_NEGATIVE_ACCOUNT_END
    - HARD_NEGATIVE_ACCOUNT_START
    + 1
)

assert (
    N_NORMAL_ACCOUNTS
    + N_RING_RESERVED
    + N_HARD_NEGATIVE_RESERVED
    == N_ACCOUNTS
)

# ============================================================
# OTHER ENTITIES
# ============================================================

N_DEVICES = 1200
N_ADDRESSES = 600
N_PHONES = 900
N_INSTRUMENTS = 1400

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

PATHS = {
    "accounts": DATA_DIR / "accounts.csv",
    "devices": DATA_DIR / "devices.csv",
    "addresses": DATA_DIR / "addresses.csv",
    "phones": DATA_DIR / "phones.csv",
    "payment_instruments": DATA_DIR / "payment_instruments.csv",
}