import re

def one_line(s: str | None) -> str | None:
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s or None

def remove_references(text: str) -> str:
    low = text.lower()
    for marker in ["\nreferences\n", "\nreference\n", "\nbibliography\n"]:
        idx = low.find(marker)
        if idx != -1:
            return text[:idx]
    return text
