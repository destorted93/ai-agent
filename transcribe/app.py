import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import io
from openai import OpenAI
import time

from config import get_settings

# Flask app
app = Flask(__name__)
settings = get_settings()
app.config["MAX_CONTENT_LENGTH"] = settings.MAX_CONTENT_LENGTH

# OpenAI client (lazy-init so health works without key)
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
    return _openai_client

ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS


def allowed_file(filename: str):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/health", methods=["GET"])  # simple health check
def health():
    return jsonify({"status": "ok", "service": settings.SERVICE_NAME})


@app.route("/upload", methods=["POST"])
def upload_and_transcribe():
    t0 = time.perf_counter()
    # Accept file under key 'file'
    if "file" not in request.files:
        return jsonify({"error": "Missing file field 'file'."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type."}), 400

    # Size check: ensure the uploaded file doesn't exceed 25 MB
    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)
    if size_bytes > app.config["MAX_CONTENT_LENGTH"]:
        return jsonify({
            "error": "File too large.",
            "limit_mb": app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
            "size_mb": round(size_bytes / (1024 * 1024), 2),
        }), 413

    # Read optional language override (ISO-639-1)
    lang = request.form.get("language", "en").lower()
    allowed_langs = settings.ALLOWED_LANGS
    if lang not in allowed_langs:
        lang = "en"

    # Read the file content in-memory
    filename = secure_filename(file.filename)
    data = file.read()

    try:
        # Call OpenAI transcription with in-memory bytes
        audio_file = io.BytesIO(data)
        audio_file.name = filename  # hint to SDK about file type
        t_oa0 = time.perf_counter()
        transcription = get_openai_client().audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
            language=lang,
            prompt=(
                "Transcribe the audio. Detect the spoken language and output the "
                "transcript in that same language with natural punctuation."
            ),
        )
        t_oa1 = time.perf_counter()

        text = getattr(transcription, "text", None)
        if not text:
            return jsonify({"error": "No text returned from transcription."}), 502

        t1 = time.perf_counter()
        return jsonify({
            "text": text,
            "filename": filename,
            "language": lang,
            "metrics": {
                "openai_ms": int((t_oa1 - t_oa0) * 1000),
                "total_ms": int((t1 - t0) * 1000),
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        pass


if __name__ == "__main__":
    # Bind to all interfaces by default for microservice usage
    port = int(os.environ.get("PORT", settings.PORT))
    app.run(host="0.0.0.0", port=port, debug=settings.DEBUG, threaded=True)

# Return JSON on payload-too-large errors triggered by MAX_CONTENT_LENGTH
@app.errorhandler(413)
def too_large(_):
    return (
        jsonify({
            "error": "Request payload too large.",
            "limit_mb": app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024),
        }),
        413,
    )
