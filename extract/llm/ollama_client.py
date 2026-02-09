import json
import re
from typing import Any, Dict, Optional

import requests


class OllamaError(RuntimeError):
    pass


def _strip_code_fences(s: str) -> str:
    """
    Some models wrap JSON in ```json ... ``` fences. Remove them safely.
    """
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _safe_json_loads(s: str) -> Optional[Dict[str, Any]]:
    s2 = _strip_code_fences(s)
    try:
        return json.loads(s2)
    except Exception:
        return None


def ollama_chat(
    model: str,
    messages: list[dict],
    host: str = "http://localhost:11434",
    timeout: int = 120,
) -> str:
    """
    Calls Ollama chat API and returns the assistant message content as a string.
    """
    url = f"{host}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.0,
        },
    }

    r = requests.post(url, json=payload, timeout=timeout)
    if r.status_code != 200:
        raise OllamaError(f"Ollama API error {r.status_code}: {r.text}")

    data = r.json()
    return data["message"]["content"]


def refine_with_ollama(
    result: dict,
    full_text: str,
    model: str,
    host: str = "http://localhost:11434",
    timeout: int = 120,
    max_chars: int = 12000,
) -> dict:
    """
    Hybrid refine step:
      - Input: rule-based result + extracted text snippet
      - Output: JSON strictly matching expected schema
    If LLM output invalid, returns the original rule-based `result`.
    """

    # Keep prompt size under control
    text = full_text[:max_chars]

    schema_hint = {
        "paper": {
            "title": "string|null",
            "year": "int|null",
            "doi": "string|null",
            "source_url": "string|null",
            "extraction_method": "string (will be set by pipeline)"
        },
        "nanomaterial": {
            "core_compositions": "list[string] (e.g., ['TiO2','ZnO'])",
            "nm_category": "metal|metal_oxide|carbon|silica|polymer_plastic|quantum_dot|mof|nanocellulose|liposome|other",
            "physical_phase": "string|null (e.g., anatase; rutile)",
            "crystallinity": "string|null",
            "cas_number": "string|null",
            "catalog_or_batch": "string|null",
            "evidence": "string|null (short snippet proving the extraction)"
        }
    }

    system_msg = (
        "You are an information extraction engine. "
        "Your job: refine a draft extraction from a scientific PDF text. "
        "Rules:\n"
        "1) Output ONLY valid JSON. No markdown. No extra text.\n"
        "2) Do NOT guess. If not explicitly present, use null or [].\n"
        "3) Prefer exact strings from the text.\n"
        "4) Keep evidence short (<= 250 chars) and taken from the text.\n"
        "5) core_compositions must be chemical/material tokens (e.g., TiO2, ZnO, Ag, CNT, graphene).\n"
    )

    instruction = (
        "Return ONLY a JSON object with exactly two top-level keys: "
        '"paper" and "nanomaterial". Do not include "task", "schema", '
        '"draft_extraction", or "pdf_text_snippet" in the output. '
        "Do NOT guess. If missing, use null or []."
    )

    user_content = (
        instruction
        + "\n\nDRAFT_JSON:\n"
        + json.dumps(result, ensure_ascii=False)
        + "\n\nTEXT_SNIPPET:\n"
        + text
    )


    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content},
    ]

    raw = ollama_chat(model=model, messages=messages, host=host, timeout=timeout)
    parsed = _safe_json_loads(raw)
    print(f"Raw LLM output:\n{raw}\nParsed LLM output:\n{parsed}")
    if not isinstance(parsed, dict):
        # fallback to rules if parsing fails
        result["paper"]["llm_model"] = model
        result["paper"]["llm_status"] = "invalid_json_fallback_to_rules"
        return result

    # minimal sanity checks
    if "paper" not in parsed or "nanomaterial" not in parsed:
        result["paper"]["llm_model"] = model
        result["paper"]["llm_status"] = "missing_keys_fallback_to_rules"
        return result

    parsed["paper"]["llm_model"] = model
    parsed["paper"]["llm_status"] = "ok"
    print("LLM refinement successful. Parsed output:")
    print(parsed)
    return parsed
