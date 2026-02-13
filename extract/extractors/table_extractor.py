import fitz  # PyMuPDF
from typing import List

TABLE_KEYWORDS = [
    "BET", "surface area", "purity", "supplier", "batch", "lot",
    "TEM", "DLS", "PDI", "zeta", "endotoxin", "nm", "mV", "m2/g"
]

def extract_table_rows(pdf_path: str, max_pages: int = 26) -> List[str]:
    """
    Returns a list of text rows that look like table rows.
    """
    doc = fitz.open(pdf_path)
    rows = []

    for page_index in range(min(len(doc), max_pages)):
        page = doc[page_index]
        blocks = page.get_text("blocks")

        for block in blocks:
            text = block[4]
            if not text:
                continue

            # Table rows often have multiple values separated by spaces
            if any(k.lower() in text.lower() for k in TABLE_KEYWORDS):
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for line in lines:
                    rows.append(line)

    return rows
