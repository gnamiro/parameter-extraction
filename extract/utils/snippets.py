import re
from typing import List, Tuple

PATTERNS: List[Tuple[str, str]] = [
    ("size", r"(particle\s+size|hydrodynamic\s+size|diameter|\bDLS\b|\bTEM\b|[0-9]\s*(?:\.\d+)?\s*nm)"),
    ("zeta", r"(zeta\s+potential|ζ|\bmV\b)"),
    ("pdi", r"(\bPDI\b|polydispersity\s+index|polydispersity)"),
    ("bet", r"(\bBET\b|surface\s+area|m2/g|m²/g)"),
    ("endotoxin", r"(endotoxin|EU/mg|EU\/mg)"),
    ("tem", r"(\bTEM\b|SEM|transmission\s+electron)"),
    ("supplier", r"(supplier|manufacturer|batch|lot|purity|impurit|address|code)"),
]

def extract_descriptor_snippets(text: str, window: int = 200, max_snips: int = 14) -> str:
    out = []
    for name, pat in PATTERNS:
        rgx = re.compile(pat, re.I)
        count = 0
        for m in rgx.finditer(text):
            start = max(0, m.start() - window)
            end = min(len(text), m.end() + window)
            snip = text[start:end].replace("\n", " ").strip()
            out.append((name, snip))
            count += 1
            if count >= 2:
                break

    # dedup
    seen = set()
    final = []
    for name, snip in out:
        key = (name, snip[:120])
        if key not in seen:
            seen.add(key)
            final.append(f"[{name}] {snip}")

    return "\n".join(final[:max_snips])
