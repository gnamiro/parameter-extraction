from __future__ import annotations

import json
import re
import requests
from typing import Any, Dict, Optional, Tuple


# ---------------------------
# Low-level helpers
# ---------------------------

def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _extract_first_json_object(s: str) -> Optional[str]:
    """
    Finds the first balanced {...} JSON object substring.
    """
    s = _strip_code_fences(s)
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return None

def _safe_json_loads(s: str) -> Optional[Dict[str, Any]]:
    """
    Parses JSON even if the model added extra text/code fences.
    Returns dict or None.
    """
    s2 = _strip_code_fences(s)
    try:
        obj = json.loads(s2)
        return obj if isinstance(obj, dict) else None
    except Exception:
        chunk = _extract_first_json_object(s2)
        if not chunk:
            return None
        try:
            obj = json.loads(chunk)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

def ollama_chat(
    model: str,
    messages: list[dict],
    host: str = "http://localhost:11434",
    timeout: int = 120,
    temperature: float = 0.0,
) -> str:
    url = f"{host}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return data["message"]["content"]


# ---------------------------
# Patch-based refinement
# ---------------------------

_ALLOWED_PAPER_FIELDS = {
    "title", "year", "doi", "source_url",
    "article_type", "author_keywords", "mesh_keywords",
}

_ALLOWED_NANO_FIELDS = {
    "core_compositions", "nm_category", "physical_phase", "crystallinity",
    "cas_number", "catalog_or_batch",
}
_ALLOWED_NANO_FIELDS |= {
    "bet_surface_area_m2_g",
    "dls_mean_diameter_water_nm",
    "dls_mean_diameter_medium_nm",
    "pdi_water",
    "pdi_medium",
    "zeta_potential_water_mV",
    "zeta_potential_medium_mV",
    "tem_diameter_nm",
    "tem_width_nm_median",
    "tem_length_nm_median",
    "no_of_walls",
    "purity_percent",
    "impurities",
    "supplier_manufacturer",
    "address",
    "supplier_code",
    "batch_or_lot_no",
    "nominal_diameter_nm",
    "nominal_length_micron",
    "nominal_specific_surface_area_m2_g",
    "dispersant",
    "description_of_dispersion",
    "endotoxins_EU_mg",
}

def _sanitize_patch(patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep only {paper, nanomaterial} top-level keys and allowed fields within them.
    """
    out: Dict[str, Any] = {}

    if "paper" in patch and isinstance(patch["paper"], dict):
        out["paper"] = {k: v for k, v in patch["paper"].items() if k in _ALLOWED_PAPER_FIELDS}

    if "nanomaterial" in patch and isinstance(patch["nanomaterial"], dict):
        out["nanomaterial"] = {k: v for k, v in patch["nanomaterial"].items() if k in _ALLOWED_NANO_FIELDS}

    # Drop empty dicts
    out = {k: v for k, v in out.items() if isinstance(v, dict) and len(v) > 0}
    return out
def refine_patch_with_ollama(
    draft_rules_result: dict,
    title_page_text: str,
    abstract_text: str,
    keywords_hint: str,
    # nanomaterial_evidence: str,
    descriptor_snippets: str,
    table_rows: list[str],    # NEW
    model: str,
    host: str = "http://localhost:11434",
    timeout: int = 120,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Returns (patch_or_none, raw_output).

    PATCH rules:
      - Output must be JSON only.
      - Top-level keys can only be: paper, nanomaterial.
      - Only include fields you are confident about.
      - If unknown: OMIT the field (do NOT output null).
    """

    # IMPORTANT: schema hint should not encourage nulls if you want omission
    schema_hint = {
        "paper": {
            "title": "string",
            "year": "int",
            "doi": "string",
            "source_url": "string",
            "article_type": "in vitro|in vivo|field|review|modelling|method",
            "author_keywords": "string (semicolon-separated)",
            "mesh_keywords": "string (semicolon-separated)",
        },
        "nanomaterial": {
            "core_compositions": "list[string] (e.g., ['TiO2','ZnO','Ag','CNT','graphene'])",
            "nm_category": "metal|metal_oxide|carbon|silica|polymer_plastic|quantum_dot|mof|nanocellulose|liposome|other",
            "physical_phase": "string (e.g., anatase; rutile)",
            "crystallinity": "string",
            "cas_number": "string (format: 1234-56-7)",
            "catalog_or_batch": "string (e.g., lot=ABC123)",

            # characterization fields (OMIT if unknown)
            "bet_surface_area_m2_g": "string",
            "dls_mean_diameter_water_nm": "string",
            "dls_mean_diameter_medium_nm": "string",
            "pdi_water": "string",
            "pdi_medium": "string",
            "zeta_potential_water_mV": "string",
            "zeta_potential_medium_mV": "string",
            "tem_diameter_nm": "string",
            "tem_width_nm_median": "string",
            "tem_length_nm_median": "string",
            "no_of_walls": "string",
            "purity_percent": "string",
            "impurities": "string",
            "supplier_manufacturer": "string",
            "address": "string",
            "supplier_code": "string",
            "batch_or_lot_no": "string",
            "nominal_diameter_nm": "string",
            "nominal_length_micron": "string",
            "nominal_specific_surface_area_m2_g": "string",
            "dispersant": "string",
            "description_of_dispersion": "string",
            "endotoxins_EU_mg": "string",

            # evidence requirement (only if setting any nanomaterial fields)
            # "evidence": "short string <=250 chars copied from snippets that supports the extracted numeric/material fields",
        }
    }

    system_msg = (
        "You are a scientific PDF information extraction engine.\n"
        "Return ONLY valid JSON. No markdown. No extra text.\n"
        "Your output MUST be a PATCH object.\n"
        "Top-level keys allowed: 'paper', 'nanomaterial'.\n"
        "Within each, include only fields you are confident are explicitly supported by the provided snippets.\n"
        "If a field is unknown, OMIT it (do NOT output null, do NOT guess).\n"
        "If you set any nanomaterial characterization fields (size/zeta/PDI/DLS/BET/TEM/etc), "
        # "also include 'evidence' as a short exact quote (<=250 chars) copied from snippets.\n"
        "Prefer 'descriptor_snippets' for numeric/material characterization fields.\n"
        "Do not rewrite the full object; output only the patch fields you are confident about.\n"
        "Schema (for reference; OMIT unknown fields):\n"
        "If table_rows contain numeric characterization data, you MAY normalize and assign values, but you MUST copy exact numbers from table_rows or descriptor_snippets. Do NOT invent measurements.\n"
        + json.dumps(schema_hint, ensure_ascii=False)
    )

    # NOTE: Put descriptor_snippets inside snippets for consistency
    payload = {
        "draft_rules_result": draft_rules_result,
        "snippets": {
            "title_page_text": (title_page_text or "")[:2500],
            "abstract_text": (abstract_text or "")[:2500],
            "keywords_hint": (keywords_hint or "")[:800],
            # "nanomaterial_evidence": (nanomaterial_evidence or "")[:1200],
            "descriptor_snippets": (descriptor_snippets or "")[:3500],
            "table_rows": table_rows[:100],   # limit size
        },
        "output_instructions": {
            "format": "PATCH JSON only",
            "top_level_keys": ["paper", "nanomaterial"],
            "paper_fields_allowed": sorted(_ALLOWED_PAPER_FIELDS),
            "nanomaterial_fields_allowed": sorted(_ALLOWED_NANO_FIELDS),
            "unknown_rule": "OMIT field if unknown (do NOT output null)",
        },
    }

    raw = ollama_chat(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        host=host,
        timeout=timeout,
        temperature=0.0,
    )

    parsed = _safe_json_loads(raw)
    if not isinstance(parsed, dict):
        return None, raw

    patch = _sanitize_patch(parsed)
    if not patch:
        return None, raw

    return patch, raw
