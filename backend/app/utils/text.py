import re


def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[\s]+", " ", s)
    s = re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿñæœ\-\s]", "", s)
    return s


def tokenize(s: str) -> list[str]:
    s = normalize_text(s)
    return [t for t in re.split(r"[\s\-/]", s) if t]

