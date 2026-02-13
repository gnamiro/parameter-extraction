import os
from extract.utils.hashing import sha256_file
from extract.utils.text import one_line, remove_references
from extract.extractors.metadata import (
    extract_paper_metadata, 
    extract_title_from_first_page_layout,
)
from extract.extractors.nanomaterial import extract_nanomaterial_identity
from extract.extractors.bio_effects import extract_bio_effects
from extract.utils.merge import merge_patch
from extract.utils.sectioning import extract_abstract, extract_keywords_hint
from extract.utils.snippets import extract_descriptor_snippets
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

        # Extract metadata from first pages (title, year, doi, keywords, etc.)
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
        descriptor_snips = extract_descriptor_snippets(text_all_clean)
        nano = extract_nanomaterial_identity(text=text_all_clean)
        bio = extract_bio_effects(text_all_clean)

        
        # Starting the LLM:
        result_rules = {"paper": meta, "nanomaterial": nano, "bio_effects": bio}
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
                            descriptor_snippets=descriptor_snips,
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
    paper = result.get("paper", {})
    nano = result.get("nanomaterial", {})
    bio = result.get("bio_effects", {})

    def join_list(v):
        if isinstance(v, list):
            return "; ".join(str(x) for x in v)
        return v

    row = {
        "file_path": paper.get("file_path"),
        "file_hash": paper.get("file_hash"),
        "title": paper.get("title"),
        "year": paper.get("year"),
        "doi": paper.get("doi"),
        "source_url": paper.get("source_url"),
        "extraction": paper.get("extraction_method"),
        "article_type": paper.get("article_type"),
        "author_keywords": paper.get("author_keywords"),
        "mesh_keywords": paper.get("mesh_keywords"),

        "nanoparticle_name": nano.get("nanoparticle_name"),
        "core_compositions": join_list(nano.get("core_compositions")),
        "nm_category": nano.get("nm_category"),
        "physical_phase": nano.get("physical_phase"),
        "crystallinity": nano.get("crystallinity"),
        "particle_size": nano.get("particle_size"),
        "zeta_potential": nano.get("zeta_potential"),
        "morphology": nano.get("morphology"),
        "pdi": nano.get("pdi"),
        "cas_number": nano.get("cas_number"),
        "catalog_or_batch": nano.get("catalog_or_batch"),
        "evidence": nano.get("evidence"),

        "cell_viability": bio.get("cell_viability"),
        "ros": bio.get("ros"),
        "bio_evidence": bio.get("bio_evidence"),

        "llm_model": paper.get("llm_model"),
        "llm_status": paper.get("llm_status"),
    }
    return row
