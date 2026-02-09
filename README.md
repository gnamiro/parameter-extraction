# Rule-Based PDF Metadata & Nanomaterial Extraction

**Rule-based + Optional Ollama (LLM-Hybrid)**

This project extracts structured information from scientific PDF papers, with a focus on:

    - Paper metadata
    - Nanomaterial identity

The pipeline is designed with a rule-based core and an optional LLM refinement layer using Ollama.

    ✅ Rule-based extraction is the default and fully deterministic
    ⚠️ LLM support is optional, experimental, and used only as a refinement layer

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
├── run.py
├── requirements.txt
├── README.md
│
├── extract/
│   ├── cli.py
│   │
│   ├── pipeline/
│   │   └── runner.py
│   │
│   ├── io/
│   │   ├── pdf_reader.py
│   │   └── excel_writer.py
│   │
│   ├── extractors/
│   │   ├── metadata.py
│   │   └── nanomaterial.py
│   │
│   ├── llm/
│   │   └── ollama_client.py        # LLM refinement (PATCH-based)
│   │
│   └── utils/
│       ├── merge.py                # PATCH + merge logic
│       └── sectioning.py           # Abstract / keyword hints
│
└── pdfs/


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


### Optional: LLM-Hybrid mode with Ollama
#### 5.1 What the LLM is used for (important)
The LLM does NOT replace rule-based extraction.
Instead, the pipeline works as:
```bash
Rules → Structured baseline
      → LLM produces a PATCH (only confident fields)
      → PATCH is merged into rules
```
✅ Hybrid output can only improve or correct fields

❌ Hybrid output can never remove rule-based information

#### 5.2 Install Ollama
Download and install Ollama:
👉 https://ollama.com

#### 5.3 Pull a recommended model
I used `qwen2.5:7b`, feel free to use any model that suits your project.

```bash
ollama pull qwen2.5:7b
```
Alternatives:
- `mistral-large:123b` (better accuracy if hardware allows)
- `llama3.1:8b` (more stable)

#### 5.4 Run pipeline with LLM refinement
```bash
python run.py \
  --pdf_dir ./pdfs \
  --llm \
  --llm_model qwen2.5:7b
```

## Current limitations (known & expected)
- Tables are not yet parsed as structured tables
- Images are not OCRed
- MeSH terms only extracted if explicitly present
- LLM refinement is experimental and may be disabled safely
