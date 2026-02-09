import sqlite3
from pathlib import Path

def init_sqlite(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    schema_path = Path(__file__).with_name("schema.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")

    conn.executescript(schema_sql)
    conn.commit()
    return conn

def upsert_paper_and_insert_nanomat(conn: sqlite3.Connection, result: dict):
    p = result["paper"]
    n = result["nanomaterial"]

    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO papers (
        file_path, file_hash, title, year, doi, source_url,
        article_type, author_keywords, mesh_keywords,
        extraction_method
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        p.get("file_path"),
        p.get("file_hash"),
        p.get("title"),
        p.get("year"),
        p.get("doi"),
        p.get("source_url"),
        p.get("article_type"),
        p.get("author_keywords"),
        p.get("mesh_keywords"),
        p.get("extraction_method"),
    ))

    conn.commit()

    cur.execute("SELECT id FROM papers WHERE file_hash = ?", (p.get("file_hash"),))
    paper_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO nanomaterials
          (paper_id, core_composition, nm_category, physical_phase, crystallinity, cas_number, catalog_or_batch, evidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        paper_id,
        "; ".join(n.get("core_compositions") or []),
        n.get("nm_category"),
        n.get("physical_phase"),
        n.get("crystallinity"),
        n.get("cas_number"),
        n.get("catalog_or_batch"),
        n.get("evidence"),
    ))
    conn.commit()
