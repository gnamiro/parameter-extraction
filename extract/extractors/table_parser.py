import re
from typing import Dict, List

def parse_table_rows(rows: List[str]) -> Dict[str, str]:
    out = {}

    for row in rows:
        r = row.lower()

        if "bet" in r and "m2" in r:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(m2/g|m²/g)", row, re.I)
            if m:
                out["bet_surface_area_m2_g"] = m.group(1)

        if "purity" in r:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", row)
            if m:
                out["purity_percent"] = m.group(1)

        if "supplier" in r or "manufacturer" in r:
            out["supplier_manufacturer"] = row

        if "batch" in r or "lot" in r:
            out["batch_or_lot_no"] = row

        if "dls" in r and "nm" in r:
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*nm", row)
            if m:
                out.setdefault("dls_mean_diameter_water_nm", m.group(1))

        if "zeta" in r and "mv" in r:
            m = re.search(r"([-−]?[0-9]+(?:\.[0-9]+)?)\s*mV", row, re.I)
            if m:
                out.setdefault("zeta_potential_water_mV", m.group(1))

        if "pdi" in r:
            m = re.search(r"\bPDI\b\s*([0-9]+(?:\.[0-9]+)?)", row, re.I)
            if m:
                out.setdefault("pdi_water", m.group(1))

    return out
