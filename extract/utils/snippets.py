import re
from typing import List, Tuple

DESCRIPTOR_PATTERNS: List[Tuple[str, str]] = [
    ("particle_size", r"(particle\s+size|hydrodynamic\s+size|diameter|\bDLS\b|\bTEM\b|[0-9]\s*(?:\.\d+)?\s*nm)"),
    ("zeta_potential", r"(zeta\s+potential|ζ|\bmV\b)"),
    ("pdi", r"(\bPDI\b|polydispersity\s+index|polydispersity)"),
    ("cas", r"(\bCAS\b|\b\d{2,7}-\d{2}-\d\b)"),
]

def extract_descriptor_snippets(text: str, window: int = 180, max_snips: int = 12) -> str:
    """
    Returns a compact, labeled snippet bundle that contains the highest-signal
    evidence for size / zeta / PDI / CAS from anywhere in the paper.
    """
    out = []
    for name, pattern in DESCRIPTOR_PATTERNS:
        rgx = re.compile(pattern, re.I)
        count = 0
        for m in rgx.finditer(text):
            start = max(0, m.start() - window)
            end = min(len(text), m.end() + window)
            snip = text[start:end].replace("\n", " ").strip()
            out.append((name, snip))
            count += 1
            if count >= max(1, max_snips // len(DESCRIPTOR_PATTERNS)):
                break

    # Deduplicate
    seen = set()
    final = []
    for name, snip in out:
        key = (name, snip[:120])
        if key not in seen:
            seen.add(key)
            final.append(f"[{name}] {snip}")

    return "\n".join(final[:max_snips])
