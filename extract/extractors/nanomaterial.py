import re
from typing import Optional

from extract.extractors.characterization import extract_characterization_fields
from extract.extractors.characterization_regex import extract_characterization_regex



NANOMATERIAL_DEFAULTS = {
    # identity (existing)
    "nanoparticle_name": None,
    "core_compositions": [],
    "nm_category": None,
    "physical_phase": None,
    "crystallinity": None,
    "cas_number": None,
    "catalog_or_batch": None,
    # "evidence": None,

    # your new descriptors
    "particle_size": None,
    "zeta_potential": None,
    "morphology": None,
    "pdi": None,

    # characterization-sheet fields
    "crystal_phase": None,
    "purity_percent": None,
    "impurities": None,
    "supplier_manufacturer": None,
    "address": None,
    "supplier_code": None,
    "batch_or_lot_no": None,
    "nominal_diameter_nm": None,
    "nominal_length_micron": None,
    "nominal_specific_surface_area_m2_g": None,
    "dispersant": None,
    "tem_diameter_nm": None,
    "tem_width_nm_median": None,
    "tem_length_nm_median": None,
    "no_of_walls": None,
    "bet_surface_area_m2_g": None,
    "dls_mean_diameter_water_nm": None,
    "pdi_water": None,
    "dls_mean_diameter_medium_nm": None,
    "pdi_medium": None,
    "zeta_potential_water_mV": None,
    "zeta_potential_medium_mV": None,
    "description_of_dispersion": None,
    "endotoxins_EU_mg": None,
}


DASH = r"[-–—]"  # hyphen, en-dash, em-dash

SIZE_RE = re.compile(
    rf"(?:particle\s+size|hydrodynamic\s+size|diameter|mean\s+particle\s+size)\s*"
    rf"(?:was|is|of|:|=)?\s*"
    rf"([0-9]+(?:\.[0-9]+)?(?:\s*{DASH}\s*[0-9]+(?:\.[0-9]+)?)?\s*(?:nm|µm|um))",
    re.I
)

ZETA_RE = re.compile(
    rf"(?:zeta\s+potential(?:s)?|ζ)\s*(?:was|is|of|:|=)?\s*"
    rf"([-−]?\s*[0-9]+(?:\.[0-9]+)?(?:\s*{DASH}\s*[-−]?\s*[0-9]+(?:\.[0-9]+)?)?\s*mV)",
    re.I
)

PDI_RE = re.compile(
    rf"(?:\bPDI\b|polydispersity\s+index)\s*(?:was|is|of|:|=)?\s*"
    rf"([0-9]+(?:\.[0-9]+)?(?:\s*{DASH}\s*[0-9]+(?:\.[0-9]+)?)?)",
    re.I
)

MORPH_RE = re.compile(
    r"\b(spherical|sphere-like|rod[-\s]?shaped|nanorods?|cubic|cube[-\s]?shaped|"
    r"irregular|fibrous|needle[-\s]?like|plate[-\s]?like|sheet[-\s]?like)\b",
    re.I
)

# Simple "nanoparticle name" capture: grabs phrases like "Silica nanoparticles (SiNPs)"
NP_NAME_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[a-z]+){0,3}\s+nanoparticles?)\s*(?:\(([A-Za-z0-9\-]{2,12})\))?",
    re.I
)


CAS_RE = re.compile(r"\b(\d{2,7}-\d{2}-\d)\b")

# Avoid the earlier issue "lot=of" by requiring digits in the ID token
BATCH_RE = re.compile(
    r"\b(batch|lot|catalog|catalogue)\s*(?:no\.?|number)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-_/]*\d+[A-Z0-9\-_/]*)\b",
    re.I
)

# --- crystal phase / polymorph ---
POLYMORPH_RE = re.compile(r"\b(anatase|rutile|brookite)\b", re.I)

# --- crystallinity (textual + percent) ---
CRYST_RE = re.compile(
    r"\b(crystallinity|crystalline|amorphous)\b(?:\s*[:=]?\s*([0-9]{1,3}(\.[0-9]+)?)\s*%?)?",
    re.I
)

# --- nanomaterial core patterns ---
# 1) chemical formulas we care about (expand as you go)
FORMULA_PATTERNS = [
    r"\bTiO2\b", r"\bZnO\b", r"\bCeO2\b", r"\bFe3O4\b", r"\bAl2O3\b", r"\bSiO2\b",
    r"\bAg\b", r"\bAu\b", r"\bCu\b", r"\bZn\b", r"\bFe\b", r"\bAl\b"
]

# 2) carbon family
CARBON_TERMS = [
    "carbon nanotube", "carbon nanotubes", "cnt", "mwcnt", "swcnt",
    "graphene", "graphene oxide", "reduced graphene oxide", "rgo",
    "carbon black", "fullerene", "fullerenes", "c60"
]

# 3) polymer/plastics
POLYMER_TERMS = [
    "nanoplastic", "nanoplastics", "microplastic", "microplastics",
    "polystyrene", "polyethylene", "polypropylene", "pmma", "pvc", "pet",
    "plastic nanoparticle", "polymer nanoparticle"
]

# 4) QD / MOF / nanocellulose / liposome / LNP
OTHER_TERMS = {
    "quantum_dot": ["quantum dot", "quantum dots", "qd", "qds"],
    "mof": ["mof", "metal-organic framework", "metal organic framework"],
    "nanocellulose": ["nanocellulose", "cellulose nanocrystal", "cnc", "cellulose nanofiber", "cnf"],
    "liposome": ["liposome", "liposomes", "lipid nanoparticle", "lipid nanoparticles", "lnp", "lipid nanocarrier"],
}

# short/ambiguous tokens (avoid false positives unless context exists)
AMBIGUOUS_SHORT = {"ag", "au", "cu", "zn", "fe", "al", "qd", "lnp", "cnc", "cnf", "go", "ps", "pet", "pvc", "pmma"}

# context words that suggest "this token is actually a nanomaterial mention"
CONTEXT_WORDS = [
    "nanoparticle", "nanoparticles", "nano-particle", "nano particles",
    "nanomaterial", "nanomaterials", "nps", "np", "nanosphere", "nanospheres",
    "oxide", "quantum", "framework", "lipid", "liposome", "nanotube", "graphene",
]

def _has_context_near(text_lower: str, token_lower: str, window: int = 90) -> bool:
    # Search all occurrences of token and check nearby context words
    for m in re.finditer(rf"\b{re.escape(token_lower)}\b", text_lower):
        start = max(0, m.start() - window)
        end = min(len(text_lower), m.end() + window)
        chunk = text_lower[start:end]
        if any(w in chunk for w in CONTEXT_WORDS):
            return True
    return False

def extract_cas(text: str) -> Optional[str]:
    m = CAS_RE.search(text)
    return m.group(1) if m else None

def extract_catalog_or_batch(text: str) -> Optional[str]:
    m = BATCH_RE.search(text)
    if not m:
        return None
    return f"{m.group(1).lower()}={m.group(2)}"

def extract_polymorph(text: str) -> Optional[str]:
    hits = sorted(set(h.lower() for h in POLYMORPH_RE.findall(text)))
    return "; ".join(hits) if hits else None

def extract_crystallinity(text: str) -> Optional[str]:
    # Return a compact descriptor like "crystalline" or "crystallinity=85%"
    m = CRYST_RE.search(text)
    if not m:
        return None
    word = m.group(1).lower()
    val = m.group(2)
    if val:
        return f"{word}={val}%"
    return word

def extract_core_compositions(text: str) -> list[str]:
    t = text
    low = t.lower()
    cores = set()

    # chemical formulas
    for pat in FORMULA_PATTERNS:
        for m in re.finditer(pat, t):
            token = m.group(0)
            tl = token.lower()
            if tl in AMBIGUOUS_SHORT:
                if _has_context_near(low, tl):
                    cores.add(token)
            else:
                cores.add(token)

    # carbon terms
    for term in CARBON_TERMS:
        tl = term.lower()
        if tl in AMBIGUOUS_SHORT:
            if _has_context_near(low, tl):
                cores.add(term.upper() if term == "cnt" else term)
        else:
            if tl in low:
                cores.add(term.upper() if term == "cnt" else term)

    # polymer terms
    for term in POLYMER_TERMS:
        if term in low:
            cores.add(term)

    # other groups
    for _, terms in OTHER_TERMS.items():
        for term in terms:
            tl = term.lower()
            if tl in AMBIGUOUS_SHORT:
                if _has_context_near(low, tl):
                    cores.add(term.upper() if term in {"qd", "lnp", "cnc", "cnf"} else term)
            else:
                if tl in low:
                    cores.add(term)

    return sorted(cores, key=lambda x: x.lower())

def infer_nm_category(core_compositions: list[str]) -> str:
    """
    Decide a dominant category from the extracted cores/terms.
    Priority rules: explicit families win.
    """
    low = " ".join(c.lower() for c in core_compositions)

    # explicit families first
    if any(k in low for k in ["liposome", "lipid nanoparticle", "lnp"]):
        return "liposome"
    if any(k in low for k in ["quantum dot", "qd"]):
        return "quantum_dot"
    if "mof" in low or "metal-organic framework" in low:
        return "mof"
    if "nanocellulose" in low or "cellulose nano" in low or "cnc" in low or "cnf" in low:
        return "nanocellulose"

    if any(k in low for k in ["nanoplastic", "microplastic", "polystyrene", "polyethylene", "polypropylene", "pmma", "pvc", "pet", "polymer nanoparticle"]):
        return "polymer_plastic"

    if any(k in low for k in ["graphene", "graphene oxide", "rgo", "carbon black", "fullerene", "cnt", "nanotube", "c60"]):
        return "carbon"

    if "sio2" in low:
        return "silica"

    # metals vs oxides
    if any(k in low for k in ["tio2", "zno", "ceo2", "fe3o4", "al2o3"]):
        return "metal_oxide"

    if any(re.fullmatch(r"(ag|au|cu|zn|fe|al)", k) for k in low.split()):
        return "metal"

    return "other"

def pick_evidence(text: str, cores: list[str], max_len: int = 250) -> Optional[str]:
    """
    Prefer evidence snippets that include nanomaterial context.
    Also avoid picking author affiliation blocks by preferring matches after 'Abstract' if present.
    """
    low = text.lower()
    start_search = 0
    abs_idx = low.find("abstract")
    if abs_idx != -1:
        start_search = abs_idx

    for c in cores:
        cl = c.lower()
        idx = low.find(cl, start_search)
        if idx == -1:
            idx = low.find(cl)  # fallback anywhere
        if idx != -1:
            s = max(0, idx - 90)
            e = min(len(text), idx + 180)
            snippet = text[s:e].strip().replace("\n", " ")
            return snippet[:max_len]
    return None


def extract_particle_size(text: str) -> Optional[str]:
    m = SIZE_RE.search(text)
    return m.group(1).strip() if m else None

def extract_zeta_potential(text: str) -> Optional[str]:
    m = ZETA_RE.search(text)
    if not m:
        return None
    # normalize spaces; keep minus sign
    return re.sub(r"\s+", "", m.group(1)).strip()

def extract_pdi(text: str) -> Optional[str]:
    m = PDI_RE.search(text)
    return m.group(1).strip() if m else None

def extract_morphology(text: str) -> Optional[str]:
    m = MORPH_RE.search(text)
    return m.group(1).strip().lower() if m else None

def extract_nanoparticle_name(text: str) -> Optional[str]:
    """
    Best-effort: returns a surface name like 'Silica nanoparticles (SiNPs)' or 'Silver nanoparticles (AgNPs)'.
    """
    m = NP_NAME_RE.search(text)
    if not m:
        return None
    base = " ".join(m.group(1).split())
    abbr = m.group(2)
    if abbr:
        return f"{base} ({abbr})"
    return base

def extract_nanomaterial_identity(text: str) -> dict:
    cores = extract_core_compositions(text)

    out = dict(NANOMATERIAL_DEFAULTS)
    out["core_compositions"] = cores
    out["nm_category"] = infer_nm_category(cores)
    out["physical_phase"] = extract_polymorph(text)
    out["crystallinity"] = extract_crystallinity(text)
    out["cas_number"] = extract_cas(text)
    out["catalog_or_batch"] = extract_catalog_or_batch(text)
    # out["evidence"] = pick_evidence(text, cores) if cores else None

    out.update(extract_characterization_regex(text))

    return out