import argparse
from extract.pipeline.runner import run_pipeline

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Extract paper metadata + nanomaterial identity from PDFs (prototype)."
    )
    ap.add_argument("--pdf_dir", type=str, required=True, help="Directory containing PDF files")
    ap.add_argument("--llm", action="store_true", help="Enable hybrid extraction (rules -> LLM refine)")
    ap.add_argument("--llm_model", type=str, default="stub-model", help="LLM model name (used if --llm)")
    ap.add_argument("--database", type=str, default=None, help="SQLite DB path. If set, results saved to SQLite.")
    ap.add_argument("--excel", type=str, default="results.xlsx", help="Excel output path if SQLite is not used.")
    ap.add_argument("--max_pages", type=int, default=3, help="Max PDF pages to read for prototype extraction.")
    return ap

def main():
    args = build_parser().parse_args()
    run_pipeline(
        pdf_dir=args.pdf_dir,
        use_llm=args.llm,
        llm_model=args.llm_model,
        sqlite_db_path=args.database,
        excel_path=args.excel,
        max_pages=args.max_pages,
    )
