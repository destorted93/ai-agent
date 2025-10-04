import os
import io
import time
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI

from config import get_settings

# FastAPI app
app = FastAPI()
settings = get_settings()

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


@app.get("/health")  # simple health check
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.post("/upload")
async def upload_and_transcribe(
    file: UploadFile = File(...),
    language: str = Form("en")
):
    t0 = time.perf_counter()
    
    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename.")

    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    # Read file content
    data = await file.read()
    size_bytes = len(data)
    
    # Size check: ensure the uploaded file doesn't exceed limit
    if size_bytes > settings.MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "File too large.",
                "limit_mb": settings.MAX_CONTENT_LENGTH // (1024 * 1024),
                "size_mb": round(size_bytes / (1024 * 1024), 2),
            }
        )

    # Validate language
    lang = language.lower()
    allowed_langs = settings.ALLOWED_LANGS
    if lang not in allowed_langs:
        lang = "en"

    try:
        # Call OpenAI transcription with in-memory bytes
        audio_file = io.BytesIO(data)
        audio_file.name = file.filename  # hint to SDK about file type
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
            raise HTTPException(status_code=502, detail="No text returned from transcription.")

        t1 = time.perf_counter()
        return {
            "text": text,
            "filename": file.filename,
            "language": lang,
            "metrics": {
                "openai_ms": int((t_oa1 - t_oa0) * 1000),
                "total_ms": int((t1 - t0) * 1000),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Bind to all interfaces by default for microservice usage
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
