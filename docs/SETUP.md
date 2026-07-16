# AI Document Formatter — Setup Guide

Location: `IPT Project June 2026/AIDocumentFormatter`

## Prerequisites

1. **Python 3.10+** — https://python.org
2. **Ollama** — https://ollama.com
3. **GPU (optional)** — RTX 4060 + 32GB RAM works well with `llama3.1:8b`

## Quick Setup (Windows)

```bat
setup.bat
start.bat
```

Open **http://localhost:5000**

## Manual Setup

```bash
# 1. Pull Ollama model
ollama pull llama3.1:8b

# 2. Python environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. Test files (optional)
python test_data\create_test_files.py

# 4. Run pipeline test (optional)
python run_pipeline_test.py

# 5. Start app
python app.py
```

## Configuration

Edit `.env`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_MODEL` | `llama3.1:8b` | Local LLM model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API |
| `FLASK_ENV` | `development` | Debug mode |

## Rule Sources

| Type | File | Edited by |
|------|------|-----------|
| Font, size, margins | `static/css/document_formatting.css` | You (CSS) |
| Voice, terminology | `style_rules.json` + PDF | Ollama AI |

## Project Layout

```
AIDocumentFormatter/
├── app.py
├── modules/           # Backend logic
├── templates/         # Web UI
├── static/css/        # UI + document_formatting.css
├── test_data/         # Sample DOCX + PDF
├── uploads/           # Runtime uploads
└── outputs/           # Formatted docs + reports
```
