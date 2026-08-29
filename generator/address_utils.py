import re


def normalize_address(raw_address: str) -> str:
    text = raw_address.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    replacements = {
        r"\brd\b": "road",
        r"\bst\b": "street",
        r"\bapt\b": "apartment",
        r"\bappt\b": "apartment",
        r"\bfl\b": "flat",
        r"\bblr\b": "bengaluru",
        r"\bbangalore\b": "bengaluru",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return text
