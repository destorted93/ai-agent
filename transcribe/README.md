# Transcribe Microservice

A small Flask-based microservice that accepts audio uploads (WAV/MP3/M4A/OGG/FLAC), transcribes them using OpenAI's `gpt-4o-transcribe`, and returns the text as JSON.

## API

- `GET /health` → `{ "status": "ok" }`
- `POST /upload` → multipart/form-data with `file` field containing the audio file. Returns:

```json
{
  "text": "...transcription...",
  "filename": "recording.wav"
}
```

Errors return JSON with `error` and an appropriate HTTP status code.

Size limits:
- Max upload size is 25 MB. Requests larger than this return `413` with:
  `{ "error": "Request payload too large.", "limit_mb": 25 }`

## Setup

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

```
pip install -r requirements.txt
```

3. Set environment variables (PowerShell example):

```
$env:OPENAI_API_KEY = "sk-..."
$env:PORT = 6001
$env:SERVICE_NAME = "transcribe"
```

## Run

```
python app.py
```

By default, the service listens on `0.0.0.0:6001`. You can override via `PORT`. Upload limit is controlled by `MAX_CONTENT_LENGTH_MB`.

## Notes

- Ensure the calling client sends the audio file as multipart/form-data under key `file`.
- The service processes audio in-memory (no disk writes).
