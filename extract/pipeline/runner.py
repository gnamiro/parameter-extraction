import os
from extract.utils.hashing import sha256_file
from extract.utils.text import one_line, remove_references
from extract.extractors.metadata import (
    extract_paper_metadata, 
    extract_title_from_first_page_layout,
)
from extract.extractors.nanomaterial import extract_nanomaterial_identity
from extract.utils.merge import merge_patch
from extract.utils.sectioning import extract_abstract, extract_keywords_hint
from extract.llm.ollama_client import refine_patch_with_ollama # This can be changed with any LLM client or stub
from extract.db.sqlite import init_sqlite, upsert_paper_and_insert_nanomat
from extract.io.pdf_reader import (
    extract_pdf_text_first_pages,
    extract_pdf_text_all_pages,
    extract_first_page_dict,
    join_pages,
)
from extract.io.excel_writer import write_excel



def list_pdfs(pdf_dir: str) -> list[str]:
    return [
        os.path.join(pdf_dir, f)
        for f in os.listdir(pdf_dir)
        if f.lower().endswith(".pdf")
    ]

def run_pipeline(
    pdf_dir: str,
    use_llm: bool,
    llm_model: str,
    sqlite_db_path: str | None,
    excel_path: str,
    max_pages: int = 3,
):
    pdfs = list_pdfs(pdf_dir)
    if not pdfs:
        raise SystemExit("No PDF files found in --pdf_dir")

    conn = None
    if sqlite_db_path:
        conn = init_sqlite(sqlite_db_path)

    excel_rows = []

    for pdf_path in pdfs:
        file_hash = sha256_file(pdf_path)

        pages_meta = extract_pdf_text_first_pages(pdf_path, max_pages=max_pages)

        text_meta = join_pages(pages_meta)
        print(text_meta[:500])

        page1_dict = extract_first_page_dict(pdf_path)
        title_layout = extract_title_from_first_page_layout(page1_dict)
        print("====> TITLE FROM LAYOUT:", title_layout, " <====")
        meta = extract_paper_metadata(text=text_meta, pages=pages_meta, file_path=pdf_path, file_hash=file_hash)

        if title_layout:
            meta["title"] = title_layout

        pages_all = extract_pdf_text_all_pages(pdf_path)
        text_all = join_pages(pages_all)



        text_all_clean = remove_references(text_all)
        nano = extract_nanomaterial_identity(text=text_all_clean)


        result_rules = {"paper": meta, "nanomaterial": nano}
        result_rules["paper"]["extraction_method"] = "rules"
        result = result_rules

        if use_llm:
            title_page_text = pages_meta[0]["text"] if pages_meta else text_meta
            abstract_text = extract_abstract(text_meta)
            keywords_hint = extract_keywords_hint(text_meta)
            nano_evidence = nano.get("evidence") or ""

            patch, raw = refine_patch_with_ollama(
                draft_rules_result=result_rules,
                title_page_text=title_page_text,
                abstract_text=abstract_text,
                keywords_hint=keywords_hint,
                nanomaterial_evidence=nano_evidence,
                model=llm_model,
            )

            # Debug prints (optional)
            print(f"Raw LLM output:\n{raw}\nParsed PATCH:\n{patch}")

            if patch:
                merged = merge_patch(result_rules, patch)
                merged["paper"]["extraction_method"] = "hybrid_llm"
                merged["paper"]["llm_model"] = llm_model
                merged["paper"]["llm_status"] = "ok_patch_merged"
                result = merged
            else:
                result["paper"]["llm_model"] = llm_model
                result["paper"]["llm_status"] = "no_patch_fallback_to_rules"
        else:
            result["paper"]["extraction_method"] = "rules"


        print("SAVING TITLE:", result["paper"].get("title"))
        print("LLM STATUS:", result["paper"].get("llm_status"))

        # Save to SQLite or Excel
        if conn:
            upsert_paper_and_insert_nanomat(conn, result)
        else:
            excel_rows.append(flatten_for_excel(result))

        print(f"Processed: {os.path.basename(pdf_path)}")

    if conn:
        conn.close()
        print(f"Saved to SQLite: {sqlite_db_path}")
    else:
        write_excel(excel_rows, excel_path)
        print(f"Saved to Excel: {excel_path}")

def flatten_for_excel(result: dict) -> dict:
    p = result["paper"]
    n = result["nanomaterial"]
    return {
        "file_path": p.get("file_path"),
        "file_hash": p.get("file_hash"),
        "title": one_line(p.get("title")),
        "year": p.get("year"),
        "doi": p.get("doi"),
        "source_url": p.get("source_url"),
        "extraction_method": p.get("extraction_method"),

        "article_type": p.get("article_type"),
        "author_keywords": p.get("author_keywords"),
        "mesh_keywords": p.get("mesh_keywords"),

        "core_compositions": "; ".join(n.get("core_compositions") or []),
        "nm_category": n.get("nm_category"),
        "physical_phase": n.get("physical_phase"),
        "crystallinity": n.get("crystallinity"),
        "cas_number": n.get("cas_number"),
        "catalog_or_batch": n.get("catalog_or_batch"),
        "evidence": n.get("evidence"),
    }
