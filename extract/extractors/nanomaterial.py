import re
from typing import Optional

# --- IDs for reproducibility ---
CAS_RE = re.compile(r"\bCAS\s*(?:No\.?|Number)?\s*[:\-]?\s*([0-9]{2,7}-[0-9]{2}-[0-9])\b", re.I)

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

def extract_nanomaterial_identity(text: str) -> dict:
    cores = extract_core_compositions(text)
    return {
        "core_compositions": cores,
        "nm_category": infer_nm_category(cores),
        "physical_phase": extract_polymorph(text),
        "crystallinity": extract_crystallinity(text),
        "cas_number": extract_cas(text),
        "catalog_or_batch": extract_catalog_or_batch(text),
        "evidence": pick_evidence(text, cores) if cores else None,
    }
