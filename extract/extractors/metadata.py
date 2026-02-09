import re
from typing import Optional

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

# URLs in text (publisher / PubMed / journal)
URL_RE = re.compile(r"\bhttps?://[^\s<>()]+\b", re.I)
WWW_RE = re.compile(r"\bwww\.[^\s<>()]+\b", re.I)

# Keywords blocks in papers
KEYWORDS_HEADER_RE = re.compile(r"(?:^|\n)\s*(key\s*words|keywords)\s*[:\-]\s*", re.I)

SECTION_HEADER_RE = re.compile(
    r"(?:\n|^)\s*(INTRODUCTION|MATERIALS?\s+AND\s+METHODS?|METHODS?|RESULTS?|DISCUSSION|CONCLUSIONS?|BACKGROUND|REFERENCES|ACKNOWLEDGMENTS?)\s*(?:\n|$)",
    re.I
)

# paragraph starters that often immediately follow keywords in PDFs
PARA_START_RE = re.compile(
    r"\b(In the past|In this|Here,|Here we|This (review|study|paper)|From the|We (performed|present|investigate)|Our (results|study))\b",
    re.I
)

# Sometimes MeSH / indexed terms appear explicitly
MESH_BLOCK_RE = re.compile(
    r"(?:^|\n)\s*(mesh\s*terms?|mesh)\s*[:\-]\s*(.+?)(?:\n\s*\n|\n[A-Z][A-Za-z ]{2,}\n)",
    re.I | re.S
)

BAD_TITLE_EXACT = {
    "review article", "research article", "original article",
    "short communication", "editorial", "erratum"
}

BAD_TITLE_CONTAINS = [
    "elsevier", "springer", "wiley", "copyright", "all rights reserved",
    "received", "accepted", "available online", "doi:", "journal"
]

BAD_TITLE_EXACT = {
    "review article", "research article", "original article",
    "short communication", "editorial", "erratum"
}

BAD_TITLE_CONTAINS = [
    "elsevier", "springer", "wiley",
    "nanomedicine", "nanomedjournal.com",
    "potential clinical significance",
    "crossmark",
]

def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_title_from_first_page_layout(page_dict: dict) -> Optional[str]:
    """
    largest font size -> title
    """
    # Collect lines with their font-size score and y-position
    candidates = []

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:  # 0 = text block
            continue

        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue

            text = _clean("".join(s.get("text", "") for s in spans))
            if not text:
                continue

            low = text.lower()

            # Hard filters
            if low in BAD_TITLE_EXACT:
                continue
            if any(b in low for b in BAD_TITLE_CONTAINS):
                continue

            # Reject likely author line: many commas and degrees
            if text.count(",") >= 3 or "phd" in low:
                continue

            # Font size: take max span size in the line
            max_size = max(s.get("size", 0) for s in spans)

            # y-position: smaller y means closer to top; use line bbox if available
            # Each span has bbox [x0,y0,x1,y1]
            y0 = min((s.get("bbox", [0, 1e9, 0, 0])[1]) for s in spans)

            # Prefer “title-like length”
            if len(text) < 12 or len(text) > 250:
                continue

            # Score: mostly by font size; slightly prefer near-top
            score = max_size * 10.0 - (y0 * 0.01)

            candidates.append((score, y0, max_size, text))

    if not candidates:
        return None

    # Sort by score descending
    candidates.sort(reverse=True, key=lambda x: x[0])

    # Often titles are 2 lines with same large font; merge top lines with similar size and close y.
    best_score, best_y, best_size, best_text = candidates[0]
    title_lines = [best_text]

    for score, y0, size, text in candidates[1:8]:
        # same font size (within tolerance) and close below the first line
        if abs(size - best_size) <= 1.0 and 0 < (y0 - best_y) < 60:
            # avoid duplicates
            if text not in title_lines:
                title_lines.append(text)

    # Keep lines in visual order (top to bottom)
    # We didn’t store y0 per line in title_lines, so rebuild from candidates quickly
    title_with_y = []
    for t in title_lines:
        for _, y0, size, text in candidates:
            if text == t:
                title_with_y.append((y0, text))
                break
    title_with_y.sort(key=lambda x: x[0])

    final_title = _clean(" ".join(t for _, t in title_with_y))
    return final_title[:300] if final_title else None

def extract_doi(text: str) -> Optional[str]:
    m = DOI_RE.search(text)
    return m.group(0) if m else None

def extract_year(text: str) -> Optional[int]:
    m = YEAR_RE.search(text)
    return int(m.group(1)) if m else None

def extract_source_url(text: str) -> Optional[str]:
    # Prefer explicit http(s) URLs
    m = URL_RE.search(text)
    if m:
        return m.group(0)
    # Sometimes only "www." is present
    m2 = WWW_RE.search(text)
    if m2:
        return "http://" + m2.group(0)
    return None

def _split_keywords(raw: str) -> list[str]:
    # Split by common separators: ; , • ·
    parts = re.split(r"[;,\u2022\u00b7]\s*", raw.strip())
    cleaned = []
    for p in parts:
        p2 = re.sub(r"\s+", " ", p).strip()
        if p2:
            cleaned.append(p2)
    # de-dup
    seen = set()
    out = []
    for k in cleaned:
        kl = k.lower()
        if kl not in seen:
            seen.add(kl)
            out.append(k)
    return out


def extract_author_keywords(text: str) -> list[str]:
    m = KEYWORDS_HEADER_RE.search(text)
    if not m:
        return []

    start = m.end()
    window = text[start : start + 800]

    # 1) cut at section header if present
    mh = SECTION_HEADER_RE.search(window)
    cut_positions = []
    if mh:
        cut_positions.append(mh.start())

    # 2) cut at paragraph starter if present
    mp = PARA_START_RE.search(window)
    if mp:
        cut_positions.append(mp.start())

    # 3) cut at double newline if present
    nn = window.find("\n\n")
    if nn != -1:
        cut_positions.append(nn)

    if cut_positions:
        window = window[:min(cut_positions)]

    # Normalize
    window = window.replace("-\n", "")
    window = re.sub(r"\s+", " ", window).strip()

    # Split into candidate keywords
    parts = re.split(r"[;,\u2022\u00b7]\s*", window)

    keywords = []
    for p in parts:
        p = p.strip()
        if not p:
            continue

        # extra guard: if a paragraph starter slipped into the same token, cut it off
        p = PARA_START_RE.split(p)[0].strip()

        # keyword-like filters
        if len(p) > 80:
            continue
        if len(p.split()) > 6:
            continue

        keywords.append(p)

    # De-dup preserve order
    seen = set()
    out = []
    for k in keywords:
        kl = k.lower()
        if kl not in seen:
            seen.add(kl)
            out.append(k)

    # Cap count (author keywords rarely exceed ~10)
    return out[:12]

def extract_mesh_keywords(text: str) -> list[str]:
    m = MESH_BLOCK_RE.search(text)
    if not m:
        return []
    raw = m.group(2)
    raw = raw[:1000]
    return _split_keywords(raw)

def infer_article_type(text: str) -> Optional[str]:
    """
    Heuristic classifier from the front pages text.
    Priority: review/modelling/method, then in vitro/in vivo, then field.
    """
    t = text.lower()

    # review
    if "review" in t or "systematic review" in t or "meta-analysis" in t or "metaanalysis" in t:
        return "review"

    # modelling / simulation
    if any(w in t for w in ["modeling", "modelling", "simulation", "in silico", "qsar", "qspr", "computational"]):
        return "modelling"

    # method / protocol
    if any(w in t for w in ["method", "protocol", "workflow", "we propose a method", "a novel method"]):
        return "method"

    # in vitro / in vivo
    if "in vitro" in t or "cell line" in t or "cytotoxic" in t:
        return "in vitro"

    if "in vivo" in t or any(w in t for w in ["mouse", "mice", "rat", "zebrafish", "wistar", "sprague-dawley"]):
        return "in vivo"

    # field / environmental
    if any(w in t for w in ["field study", "field experiment", "in the field", "mesocosm", "lake", "river sampling"]):
        return "field"

    return None

def extract_paper_metadata(text: str, pages: list[dict], file_path: str, file_hash: str) -> dict:
    author_kws = extract_author_keywords(text)
    mesh_kws = extract_mesh_keywords(text)

    return {
        "file_path": file_path,
        "file_hash": file_hash,
        # "title": extract_title_from_first_page_layout(pages),
        "year": extract_year(text),
        "doi": extract_doi(text),
        "source_url": extract_source_url(text),

        "article_type": infer_article_type(text),
        "author_keywords": "; ".join(author_kws) if author_kws else None,
        "mesh_keywords": "; ".join(mesh_kws) if mesh_kws else None,

        "extraction_method": None,  # pipeline sets this
    }
