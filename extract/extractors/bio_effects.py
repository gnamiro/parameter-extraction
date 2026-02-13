import re
from typing import Dict, Optional

# Very conservative regexes (prototype)
CELL_VIAB_RE = re.compile(
    r"(cell\s+viability|viability)\s*(?:was|is|:)?\s*([0-9]{1,3}\s*%|\bIC\s*50\b\s*=?\s*[0-9\.]+\s*(?:µg/mL|ug/mL|mg/L|µM|mM)?)",
    re.I
)

ROS_RE = re.compile(
    r"\bROS\b|reactive\s+oxygen\s+species",
    re.I
)

def extract_bio_effects(text: str) -> Dict[str, Optional[str]]:
    out = {
        "cell_viability": None,
        "ros": None,
        "bio_evidence": None,
    }

    m = CELL_VIAB_RE.search(text)
    if m:
        out["cell_viability"] = m.group(2).strip()
        out["bio_evidence"] = m.group(0).strip()[:250]

    # For ROS, start as boolean-ish evidence; you can refine later
    m2 = ROS_RE.search(text)
    if m2 and not out["bio_evidence"]:
        out["ros"] = "mentioned"
        out["bio_evidence"] = text[max(0, m2.start()-80):m2.start()+120].strip()[:250]
    elif m2:
        out["ros"] = "mentioned"

    return out
