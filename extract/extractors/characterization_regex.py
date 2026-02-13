import re
from typing import Dict, Optional

DASH = r"[-–—]"
NUM = r"[0-9]+(?:\.[0-9]+)?"
RANGE = rf"{NUM}(?:\s*{DASH}\s*{NUM})?"
UNIT_NM = r"(?:nm)"
UNIT_MV = r"(?:mV)"
UNIT_M2G = r"(?:m2/g|m²/g)"
UNIT_EU_MG = r"(?:EU/mg|EU\/mg)"

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def _first(rex: re.Pattern, text: str) -> Optional[str]:
    m = rex.search(text)
    return _clean(m.group(1)) if m else None

# --- Core descriptors ---
RE_MORPH = re.compile(
    r"\b(spherical|sphere-like|rod[-\s]?shaped|nanorods?|cubic|irregular|fibrous|needle[-\s]?like|plate[-\s]?like|sheet[-\s]?like)\b",
    re.I,
)

RE_PARTICLE_SIZE = re.compile(
    rf"(?:particle\s+size|hydrodynamic\s+size|diameter|mean\s+particle\s+size)\s*(?:was|is|of|:|=)?\s*({RANGE}\s*{UNIT_NM})",
    re.I,
)

RE_PDI = re.compile(
    rf"(?:\bPDI\b|polydispersity\s+index)\s*(?:was|is|of|:|=)?\s*({RANGE})",
    re.I,
)

RE_ZETA = re.compile(
    rf"(?:zeta\s+potential(?:s)?|ζ)\s*(?:was|is|of|:|=)?\s*([-−]?\s*{RANGE}\s*{UNIT_MV})",
    re.I,
)

# --- BET surface area ---
RE_BET = re.compile(
    rf"\bBET\b.*?(?:surface\s*area)?\s*(?:was|is|of|:|=)?\s*({NUM})\s*({UNIT_M2G})",
    re.I,
)

# --- TEM fields ---
RE_TEM_DIAM = re.compile(rf"TEM.*?(?:diameter|size)\s*(?:was|is|of|:|=)?\s*({RANGE})\s*{UNIT_NM}", re.I)
RE_TEM_WIDTH = re.compile(rf"TEM.*?width.*?(?:median)?\s*(?:was|is|of|:|=)?\s*({RANGE})\s*{UNIT_NM}", re.I)
RE_TEM_LENGTH = re.compile(rf"TEM.*?length.*?(?:median)?\s*(?:was|is|of|:|=)?\s*({RANGE})\s*(?:nm|µm|um)", re.I)

# --- DLS mean diameter by medium ---
RE_DLS_WATER = re.compile(rf"DLS.*?(?:water).*?(?:diameter|size).*?(?:was|is|of|:|=)?\s*({RANGE})\s*{UNIT_NM}", re.I)
RE_DLS_MEDIUM = re.compile(rf"DLS.*?(?:medium|DMEM|RPMI|PBS).*?(?:diameter|size).*?(?:was|is|of|:|=)?\s*({RANGE})\s*{UNIT_NM}", re.I)

# --- Zeta by medium ---
RE_ZETA_WATER = re.compile(rf"zeta.*?(?:water).*?(?:was|is|of|:|=)?\s*([-−]?\s*{RANGE})\s*{UNIT_MV}", re.I)
RE_ZETA_MEDIUM = re.compile(rf"zeta.*?(?:medium|DMEM|RPMI|PBS).*?(?:was|is|of|:|=)?\s*([-−]?\s*{RANGE})\s*{UNIT_MV}", re.I)

# --- Endotoxins ---
RE_ENDOTOX = re.compile(rf"endotoxin(?:s)?\s*(?:was|is|of|:|=)?\s*({NUM})\s*({UNIT_EU_MG})", re.I)

# --- “Description of dispersion” (best-effort: capture sentence containing 'dispers' keyword) ---
RE_DISP_SENT = re.compile(r"([^.]{0,160}\bdispers(?:ed|ion|ant)?\b[^.]{0,160}\.)", re.I)

def extract_characterization_regex(text: str) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {}

    # core
    m = RE_MORPH.search(text)
    if m:
        out["morphology"] = m.group(1).lower()

    out["particle_size"] = _first(RE_PARTICLE_SIZE, text)
    out["pdi"] = _first(RE_PDI, text)
    out["zeta_potential"] = _first(RE_ZETA, text)

    # BET
    bet = RE_BET.search(text)
    if bet:
        out["bet_surface_area_m2_g"] = bet.group(1)

    # TEM
    out["tem_diameter_nm"] = _first(RE_TEM_DIAM, text)
    out["tem_width_nm_median"] = _first(RE_TEM_WIDTH, text)
    out["tem_length_nm_median"] = _first(RE_TEM_LENGTH, text)

    # DLS
    out["dls_mean_diameter_water_nm"] = _first(RE_DLS_WATER, text)
    out["dls_mean_diameter_medium_nm"] = _first(RE_DLS_MEDIUM, text)

    # PDI split (best-effort): if we see multiple PDIs nearby water/medium later, LLM will handle; rules keep one
    out["pdi_water"] = out.get("pdi")
    # leave pdi_medium empty by default; LLM may fill
    out.setdefault("pdi_medium", None)

    # zeta split
    out["zeta_potential_water_mV"] = _first(RE_ZETA_WATER, text)
    out["zeta_potential_medium_mV"] = _first(RE_ZETA_MEDIUM, text)

    # endotoxins
    endo = RE_ENDOTOX.search(text)
    if endo:
        out["endotoxins_EU_mg"] = endo.group(1)

    # dispersion description
    d = RE_DISP_SENT.search(text)
    if d:
        out["description_of_dispersion"] = _clean(d.group(1))[:250]

    # Drop None values (keeps your defaults intact)
    return {k: v for k, v in out.items() if v}
