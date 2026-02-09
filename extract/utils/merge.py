from __future__ import annotations
from typing import Any, Dict

def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, list) and len(v) == 0:
        return True
    if isinstance(v, dict) and len(v) == 0:
        return True
    return False

def merge_patch(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge patch into base. Only overwrite when patch value is non-empty.
    Supports nested dicts.
    """
    out = dict(base)
    for k, pv in patch.items():
        bv = out.get(k)

        if isinstance(bv, dict) and isinstance(pv, dict):
            out[k] = merge_patch(bv, pv)
        else:
            if not _is_empty(pv):
                out[k] = pv
    return out
