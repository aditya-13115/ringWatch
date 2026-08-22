import hashlib


def make_account_id(i: int) -> str:
    return f"A{i:06d}"


def make_device_id(i: int) -> str:
    return f"D{i:06d}"


def make_address_id(i: int) -> str:
    return f"ADDR{i:06d}"


def make_phone_hash(i: int) -> str:
    value = f"ringwatch_phone_{i}"
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def make_instrument_id(i: int) -> str:
    return f"PI{i:06d}"


def make_instrument_hash(i: int) -> str:
    value = f"ringwatch_instrument_{i}"
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def make_order_id(i: int) -> str:
    return f"ORD{i:07d}"


# ============================================================
# DAY 3 IDs
# ============================================================


def make_refund_id(i: int) -> str:
    return f"REF{i:07d}"


def make_dispute_id(i: int) -> str:
    return f"DIS{i:07d}"


def make_ring_id(i: int) -> str:
    return f"R{i:03d}"
