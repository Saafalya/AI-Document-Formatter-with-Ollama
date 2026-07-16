"""
app.py
------
AI Document Formatter — Flask application entry point.
"""

import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-prod")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_SIZE_MB", 50)) * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_DOCX = {"docx"}
ALLOWED_PDF = {"pdf"}

from modules.pipeline_runner import run_pipeline
from modules.results_store import get_summary, load_results, save_results
from modules.ollama_client import get_ollama_client


def _allowed(filename: str, allowed_set: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


def _save_upload(file, allowed_set: set, prefix: str) -> Path:
    if not file or file.filename == "":
        raise ValueError("No file provided.")
    if not _allowed(file.filename, allowed_set):
        ext = list(allowed_set)[0].upper()
        raise ValueError(f"Only {ext} files are accepted.")
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{file.filename}"
    dest = UPLOAD_DIR / filename
    file.save(str(dest))
    logger.info(f"Saved upload: {dest.name}")
    return dest


def _get_run_id() -> str:
    return session.get("run_id", "")


def _require_results():
    run_id = _get_run_id()
    results = load_results(run_id)
    if not results:
        return None, None
    return run_id, results


@app.context_processor
def inject_globals():
    run_id = _get_run_id()
    summary = get_summary(run_id) if run_id else None
    return {"run_summary": summary, "has_results": summary is not None}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    """Upload DOCX + PDF and run the full compliance pipeline in one request."""
    try:
        docx_file = request.files.get("docx_file")
        pdf_file = request.files.get("pdf_file")

        if not docx_file or not pdf_file:
            return jsonify({
                "status": "error",
                "message": "Please upload both a DOCX document and a style guide PDF.",
            }), 400

        docx_path = _save_upload(docx_file, ALLOWED_DOCX, "doc")
        pdf_path = _save_upload(pdf_file, ALLOWED_PDF, "guide")

        logger.info("Starting compliance pipeline...")
        results = run_pipeline(str(docx_path), str(pdf_path), OUTPUT_DIR)

        save_results(results["run_id"], results)
        session["run_id"] = results["run_id"]
        session.modified = True

        logger.info(f"Pipeline complete. Run ID: {results['run_id']}")
        return jsonify({
            "status": "ok",
            "run_id": results["run_id"],
            "redirect": url_for("results"),
            "scores": results["scores"],
        })

    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        logger.exception("Compliance pipeline failed")
        return jsonify({"status": "error", "message": f"Processing failed: {e}"}), 500


@app.route("/results")
def results():
    run_id, results_data = _require_results()
    if not results_data:
        return redirect(url_for("index"))
    return render_template("results.html", results=results_data, run_id=run_id)


@app.route("/preview")
def preview():
    _, results_data = _require_results()
    if not results_data:
        return redirect(url_for("index"))
    return render_template("preview.html", results=results_data)


@app.route("/changelog")
def changelog():
    _, results_data = _require_results()
    if not results_data:
        return redirect(url_for("index"))
    return render_template("changelog.html", results=results_data)


@app.route("/rules")
def rules():
    _, results_data = _require_results()
    if not results_data:
        return redirect(url_for("index"))
    return render_template("rules.html", results=results_data)


@app.route("/download/report/<filename>")
def download_report(filename: str):
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists():
        return jsonify({"error": "Report not found"}), 404
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=f"compliance_report_{safe_name}",
        mimetype="application/pdf",
    )


@app.route("/download/<filename>")
def download(filename: str):
    safe_name = Path(filename).name
    file_path = OUTPUT_DIR / safe_name
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=f"formatted_{safe_name}",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.route("/api/results")
def api_results():
    _, results_data = _require_results()
    if not results_data:
        return jsonify({"error": "No results available"}), 404
    return jsonify(results_data)


@app.route("/new")
def new_analysis():
    session.pop("run_id", None)
    session.modified = True
    return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(e):
    return jsonify({"status": "error", "message": "File too large. Maximum size is 50 MB."}), 413


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found"}), 404
    return render_template("index.html"), 404


if __name__ == "__main__":
    ollama = get_ollama_client()
    if ollama.is_available():
        logger.info(f"Ollama connected — model: {ollama.model}")
    else:
        logger.warning(
            f"Ollama not detected. Install from https://ollama.com then run: "
            f"ollama pull {ollama.model}"
        )
    debug = os.getenv("FLASK_ENV", "production") == "development"
    app.run(debug=debug, host="0.0.0.0", port=5000)
