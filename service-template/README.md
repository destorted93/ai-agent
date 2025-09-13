# Service Template

Starter template for new Flask microservices in this repo.

## Layout

- `app.py` — Minimal Flask app with `/health`.
- `config.py` — Centralized config using Pydantic Settings (env-driven, typed).
- `requirements.txt` — Python dependencies for the service.
  

## Getting Started

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PORT = 7001
$env:SERVICE_NAME = "my-service"
python app.py
```

## Conventions

- Expose `GET /health` returning `{ "status": "ok" }` at minimum.
- Use `PORT` env var to set the listen port (via Pydantic Settings).
- Prefer JSON errors with shape `{ "error": "message", "details": {...} }`.
- Respect `MAX_CONTENT_LENGTH` for upload limits when applicable.
- Include a `README.md` and `requirements.txt` in each service.
