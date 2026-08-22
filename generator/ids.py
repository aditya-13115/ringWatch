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


def make_order_id(i):
    return f"ORD{i:07d}"