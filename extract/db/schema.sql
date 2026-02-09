CREATE TABLE IF NOT EXISTS papers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT UNIQUE NOT NULL,
  file_hash TEXT UNIQUE NOT NULL,
  title TEXT,
  year INTEGER,
  doi TEXT,
  source_url TEXT,

  article_type TEXT,           
  author_keywords TEXT,       
  mesh_keywords TEXT,          

  extraction_method TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);


CREATE TABLE IF NOT EXISTS nanomaterials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id INTEGER NOT NULL,
  core_composition TEXT,
  nm_category TEXT,
  physical_phase TEXT,
  crystallinity TEXT,
  cas_number TEXT,
  catalog_or_batch TEXT,
  evidence TEXT,
  FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);
