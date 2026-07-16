# AI Document Formatter

**Location:** `IPT Project June 2026/AIDocumentFormatter`

Enterprise document compliance platform that analyses, validates, rewrites, and formats Microsoft Word documents against a user-provided style guide.

## Features

- Single-step upload: DOCX + Style Guide PDF → analyse in one click
- **Local Ollama LLM** — no cloud API keys required
- **CSS-based formatting rules** (font, size, margins) — deterministic, not AI-guessed
- **Ollama semantic rules** (voice, terminology, structure) from style guide PDF
- 16+ violation types across formatting, writing, and structure
- Centralized AI rewrite engine with validation layer
- Formatted DOCX output + PDF compliance report
- Compliance dashboard, preview, change log, and rules viewer

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally
- Recommended model: `llama3.1:8b` (optimal for RTX 4060 8GB + 32GB RAM)

## Quick Start

```bash
# 1. Install Ollama from https://ollama.com and pull the model
ollama pull llama3.1:8b

# 2. Quick setup (Windows)
setup.bat
start.bat

# OR manual setup:
cd AIDocumentFormatter
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000** → upload DOCX + PDF → click **Analyse & Format Document**.

## Project Structure

```
FinFormatterAI/
├── app.py                      # Flask entry point
├── run_pipeline_test.py        # CLI test (no server)
├── requirements.txt
├── style_rules.json            # Semantic rules (voice, terminology, structure)
├── static/css/document_formatting.css  # Hardcoded font/size/margin rules
├── .env                        # Your secrets (not committed)
├── .env.example
│
├── modules/
│   ├── ollama_client.py        # Local Ollama LLM client
│   ├── formatting_css_loader.py # Parses document_formatting.css
│   ├── pipeline_runner.py      # Shared compliance pipeline
│   ├── results_store.py        # Disk-backed results (fixes session limit)
│   ├── ai_rewriter.py          # Centralized rewrite engine
│   ├── ai_style_interpreter.py # AI rule extraction
│   ├── change_logger.py        # Change audit trail
│   ├── compliance_checker.py   # Violation orchestrator
│   ├── compliance_report.py    # PDF report generator
│   ├── compliance_score.py     # Scoring engine
│   ├── document_analyser.py    # DOCX parser
│   ├── document_formatter.py   # Formatting applicator
│   ├── recommendation_engine.py
│   ├── rewrite_validator.py    # Rewrite safety checks
│   ├── rule_loader.py          # Central rule store
│   ├── structure_checker.py
│   ├── structure_detector.py
│   ├── styleguide_parser.py    # PDF text extraction
│   └── violation_classifier.py # Centralized classifier
│
├── templates/                  # HTML pages
│   ├── base.html
│   ├── index.html              # Upload page
│   ├── results.html            # Compliance dashboard
│   ├── preview.html            # Side-by-side comparison
│   ├── changelog.html          # Change audit trail
│   └── rules.html              # Extracted style guide rules
│
├── static/
│   ├── css/main.css
│   ├── css/document_formatting.css  # DOCX formatting rules
│   └── js/main.js
│
├── test_data/
│   ├── create_test_files.py    # Generate sample files
│   ├── sample_document.docx
│   └── style_guide.pdf
│
├── uploads/                    # User uploads (runtime)
└── outputs/
    ├── formatted_<id>.docx     # Formatted documents
    ├── report_<id>.pdf         # Compliance reports
    └── sessions/<id>.json      # Results cache (not in cookie)
```

## Test Without the Web UI

```bash
python test_data/create_test_files.py   # Generate sample files
python run_pipeline_test.py           # Run full pipeline
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama API URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model name | `llama3.1:8b` |
| `OLLAMA_ENABLED` | Enable/disable Ollama | `true` |
| `OLLAMA_TIMEOUT` | Request timeout (seconds) | `180` |
| `FLASK_SECRET_KEY` | Session signing secret | dev default |
| `FLASK_ENV` | Set to `development` for debug mode | `production` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `50` |
| `SIMILARITY_THRESHOLD` | Rewrite similarity threshold (0–1) | `0.70` |

## Rule Sources

| Rule type | Source | Editable in |
|-----------|--------|-------------|
| Font, size, margins, alignment | CSS variables | `static/css/document_formatting.css` |
| Voice, terminology, structure | JSON + Ollama AI | `style_rules.json` + style guide PDF |

### Recommended Ollama models (RTX 4060 + 32GB RAM)

| Model | Command | Notes |
|-------|---------|-------|
| **llama3.1:8b** (default) | `ollama pull llama3.1:8b` | Best balance of speed + quality |
| qwen2.5:7b | `ollama pull qwen2.5:7b` | Strong instruction following |
| mistral:7b | `ollama pull mistral:7b` | Fast, good for rewrites |

## Web Pages

| Page | URL | Description |
|------|-----|-------------|
| Upload | `/` | Select DOCX + PDF, run analysis |
| Results | `/results` | Scores, violations, recommendations |
| Preview | `/preview` | Side-by-side original vs formatted |
| Changes | `/changelog` | Before/after audit trail |
| Rules | `/rules` | AI-extracted style guide rules |
| New | `/new` | Clear session, start fresh |

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/process` | POST | Upload files + run pipeline |
| `/api/results` | GET | JSON results for current session |
| `/download/<filename>` | GET | Download formatted DOCX |
| `/download/report/<filename>` | GET | Download PDF report |

## Architecture Notes

- **Single `/process` endpoint** — no double upload; files sent once with analysis.
- **Disk-backed results** — full results saved to `outputs/sessions/` because Flask session cookies are limited to ~4 KB.
- **Session stores only `run_id`** — prevents crashes and lost results after redirect.
