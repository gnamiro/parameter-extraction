import re

ABSTRACT_RE = re.compile(
    r"\babstract\b(.*?)(\bkeywords?\b|\bkey\s*words\b|\n[A-Z][A-Z ]{3,}\n)",
    re.I | re.S
)

KEYWORDS_LINE_RE = re.compile(
    r"(?:^|\n)\s*(keywords|key\s*words)\s*[:\-]\s*(.{0,500})",
    re.I
)

def extract_abstract(text: str) -> str:
    m = ABSTRACT_RE.search(text)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(1)).strip()

def extract_keywords_hint(text: str) -> str:
    """
    Returns only a short hint following 'Keywords:' to help LLM.
    Not meant to be perfect; rules already extract keywords.
    """
    m = KEYWORDS_LINE_RE.search(text)
    if not m:
        return ""
    return re.sub(r"\s+", " ", m.group(2)).strip()
