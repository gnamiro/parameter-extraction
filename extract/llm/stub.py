def refine_with_llm_stub(result: dict, full_text: str, model: str) -> dict:
    """
    Stub: keeps rule-based results unchanged.
    Replace this with a real implementation later (Ollama or API).
    """
    result["paper"]["llm_model"] = model
    return result
