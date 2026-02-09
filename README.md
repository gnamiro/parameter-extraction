# Rule-Based PDF Metadata & Nanomaterial Extraction

This project implements a rule-based pipeline to extract structured information from scientific PDF papers, with a focus on:

    - Paper metadata
    - Nanomaterial identity

⚠️ Note:
LLM-based extraction is intentionally disabled / experimental and not documented here.
This README describes only the deterministic, rule-based extraction.

-------------------

## What this pipeline extracts (rule-based)

**Paper metadata**

- Title (layout-aware, font-size based)

- Year

- DOI

- Source URL (if present in PDF)

- Article type
(`review`, `in vitro`, `in vivo`, `field`, `modelling`, `method`)

- Author-provided keywords (cleaned, bounded, no paragraph leakage)

- MeSH / indexed keywords (only if explicitly present in PDF text)

**Nanomaterial identity**
- Core composition(s)
(Ag, Au, TiO₂, ZnO, CNT, graphene, SiO₂, nanoplastics, MOF, liposomes, etc.)

- Nanomaterial category
(`metal`, `metal_oxide`, `carbon`, `silica`, `polymer_plastic`, `quantum_dot`, `mof`, `nanocellulose`, `liposome`, `other`)

- Physical phase / polymorph
(anatase, rutile, brookite)
- Crystallinity (textual or percentage if stated)
- Reproducibility identifiers:

    - CAS number

    - Catalog / batch / lot number (validated, no false matches)

----------------
## Project structure

```text
keyword_extractor/
│
├── run.py                      # Entry point
├── requirements.txt
├── README.md
│
├── extract/
│   ├── cli.py                  # CLI argument parsing
│   │
│   ├── pipeline/
│   │   └── runner.py            # Orchestrates extraction flow
│   │
│   ├── io/
│   │   ├── pdf_reader.py        # PDF text + layout extraction
│   │   └── excel_writer.py      # Excel output
│   │
│   ├── extractors/
│   │   ├── metadata.py          # Title, DOI, year, keywords, article type
│   │   └── nanomaterial.py      # Nanomaterial identity rules
│   │
│   └── utils/
│       └── text.py              # Helpers (reference removal, cleanup)
│
└── pdfs/                        # Input PDFs

```

## Installation

1. Create and activate a virtual environment (recommended)
```bash
python -m venv .venv
```

windows
```bash
.venv\Scripts\activate
```
MacOS/Linux
```bash
source .venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

`requirements.txt`
```bash
pymupdf
pandas
openpyxl

requests
```

## How to run (rule-based only)

Basic usage:
```bash
python run.py --pdf_dir ./pdfs
```

Optional flags
```bash
python run.py \
  --pdf_dir ./pdfs \
  --max_pages 3 \
  --excel results.xlsx
```

- `--pdf_dir` : directory containing PDFs

- `--max_pages` : number of pages used for metadata (default: 3)

- `--excel` : output Excel file path

⚠️ Do not use --llm for now (LLM path is experimental).