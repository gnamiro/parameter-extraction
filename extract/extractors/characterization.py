import re
from typing import Dict, Optional

DASH = r"[-–—]"

BET_RE = re.compile(r"(?:BET\s*(?:surface\s*area)?|surface\s*area)\s*(?:=|:|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*(m2/g|m²/g)", re.I)
ENDOTOX_RE = re.compile(r"endotoxin(?:s)?\s*(?:=|:|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*(EU/mg|EU\/mg)", re.I)

TEM_DIAM_RE = re.compile(r"(?:TEM\s*(?:mean\s*)?diameter)\s*(?:=|:|of)?\s*([0-9]+(?:\.[0-9]+)?(?:\s*"+DASH+r"\s*[0-9]+(?:\.[0-9]+)?)?)\s*nm", re.I)
TEM_LEN_RE  = re.compile(r"(?:TEM\s*(?:mean\s*)?length)\s*(?:=|:|of)?\s*([0-9]+(?:\.[0-9]+)?(?:\s*"+DASH+r"\s*[0-9]+(?:\.[0-9]+)?)?)\s*(nm|µm|um)", re.I)

DLS_WATER_RE  = re.compile(r"(?:DLS.*?\(water\)|DLS.*?water).*?([0-9]+(?:\.[0-9]+)?)\s*nm", re.I)
DLS_MEDIUM_RE = re.compile(r"(?:DLS.*?\(medium\)|DLS.*?medium).*?([0-9]+(?:\.[0-9]+)?)\s*nm", re.I)

ZETA_WATER_RE  = re.compile(r"(?:zeta\s+potential.*?\(water\)|zeta.*?water).*?([-−]?\s*[0-9]+(?:\.[0-9]+)?)\s*mV", re.I)
ZETA_MEDIUM_RE = re.compile(r"(?:zeta\s+potential.*?\(medium\)|zeta.*?medium).*?([-−]?\s*[0-9]+(?:\.[0-9]+)?)\s*mV", re.I)

PDI_RE = re.compile(r"\bPDI\b\s*(?:=|:|of)?\s*([0-9]+(?:\.[0-9]+)?)", re.I)

def _m(rex, text) -> Optional[str]:
    m = rex.search(text)
    return m.group(1).strip() if m else None

def extract_characterization_fields(text: str) -> Dict[str, Optional[str]]:
    out = {
        "bet_surface_area_m2_g": None,
        "endotoxins_EU_mg": None,
        "tem_diameter_nm": None,
        "tem_length_nm_median": None,
        "dls_mean_diameter_water_nm": None,
        "dls_mean_diameter_medium_nm": None,
        "zeta_potential_water_mV": None,
        "zeta_potential_medium_mV": None,
        "pdi_water": None,
        "pdi_medium": None,
    }

    bet = BET_RE.search(text)
    if bet:
        out["bet_surface_area_m2_g"] = bet.group(1).strip()

    endo = ENDOTOX_RE.search(text)
    if endo:
        out["endotoxins_EU_mg"] = endo.group(1).strip()

    out["tem_diameter_nm"] = _m(TEM_DIAM_RE, text)
    out["tem_length_nm_median"] = _m(TEM_LEN_RE, text)

    out["dls_mean_diameter_water_nm"] = _m(DLS_WATER_RE, text)
    out["dls_mean_diameter_medium_nm"] = _m(DLS_MEDIUM_RE, text)

    out["zeta_potential_water_mV"] = _m(ZETA_WATER_RE, text)
    out["zeta_potential_medium_mV"] = _m(ZETA_MEDIUM_RE, text)

    # If the paper does not separate PDI by medium, store first one in pdi_water
    pdi = _m(PDI_RE, text)
    if pdi:
        out["pdi_water"] = pdi

    return out
