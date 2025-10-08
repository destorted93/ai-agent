# Transcribe Service

FastAPI service that converts audio to text using OpenAI Whisper.

## What it does

Receives audio files and returns transcribed text with timestamps.

## Endpoints

### `GET /health`
Health check endpoint.

### `POST /upload`
Upload audio file for transcription.

**Parameters**:
- `file` - Audio file (WAV, MP3, M4A, OGG, FLAC, WebM)
- `language` - Language code (default: `en`)

**Response**:
```json
{
  "text": "transcribed text",
  "language": "en",
  "duration": 1.23,
  "processing_time_seconds": 0.45
}
```

## Configuration

Set in `config.py`:
- `PORT` - Service port (default: 6000)
- `ALLOWED_EXTENSIONS` - Supported audio formats

## Running

```bash
python transcribe/app.py
```

Or via the launcher:
```bash
START.bat
```

## Dependencies

- FastAPI
- OpenAI Python SDK
- uvicorn

Install: `pip install -r transcribe/requirements.txt`

## Integration

Used by the widget for voice-to-text conversion
- The service processes audio in-memory (no disk writes).
