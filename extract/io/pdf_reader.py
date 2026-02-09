import fitz  # pymupdf


def extract_first_page_dict(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    page = doc[0]
    d = page.get_text("dict")
    doc.close()
    return d

def extract_pdf_text_first_pages(pdf_path: str, max_pages: int = 3) -> list[dict]:
    doc = fitz.open(pdf_path)
    n = min(len(doc), max_pages)
    pages = []
    for i in range(n):
        pages.append({"page": i + 1, "text": doc[i].get_text("text")})
    doc.close()
    return pages

def extract_pdf_text_all_pages(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(len(doc)):
        pages.append({"page": i + 1, "text": doc[i].get_text("text")})
    doc.close()
    return pages

def join_pages(pages: list[dict]) -> str:
    return "\n\n".join(p["text"] for p in pages)

def remove_references(text: str) -> str:
    low = text.lower()
    idx = low.find("\nreferences\n")
    if idx == -1:
        idx = low.find("\nreference\n")
    return text[:idx] if idx != -1 else text