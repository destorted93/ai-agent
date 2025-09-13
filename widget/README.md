# Widget Service

A small Flask service exposing `/health` to conform with the repo's microservice conventions, plus a desktop widget (`widget.py`) that records audio and posts to the transcribe service.

## Layout
- `app.py` — Minimal Flask service with `/health`.
- `config.py` — Env-driven settings.
- `.env.example` — Example environment variables.
- `requirements.txt` — Dependencies for running the service/UI.
- `widget.py` — PyQt desktop widget for recording and sending audio.

## Run service
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PORT=6002
$env:SERVICE_NAME="widget"
python app.py
```

## Run desktop widget
```powershell
python widget.py
```

## Notes
- The widget posts to the transcribe service at `TRANSCRIBE_URL` (default `http://127.0.0.1:6001/upload`). Override via env if needed.
- This service does not proxy audio; it only provides a health check and keeps the folder consistent with service patterns.
