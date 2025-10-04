# Widget Service

A desktop widget providing voice recording, transcription, and a chat interface with the AI agent.

## Features

- **Voice Recording**: Record audio and send to transcription service
- **Chat Window**: Interactive chat interface with the AI agent
- **Always-on-top**: Widget stays visible while working
- **Multi-language**: Support for multiple transcription languages
- **Persistent Chat**: Chat history is maintained across sessions

## Layout
- `app.py` — Minimal Flask service with `/health`.
- `config.py` — Env-driven settings.
- `.env.example` — Example environment variables.
- `requirements.txt` — Dependencies for running the service/UI.
- `widget.py` — PyQt desktop widget for recording, chat, and AI interaction.
- `CHAT_FEATURE.md` — Detailed documentation for the chat feature.
- `test_chat.py` — Test script for verifying chat functionality.

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

## Widget Controls

### Main Buttons
- **▶ Start Recording**: Begin audio recording
- **⏹ Stop Recording**: Stop recording and send to transcription service
- **💬 Chat**: Open/close the chat window
- **⚙ Settings**: Language selection and close option

### Chat Window
The chat window provides a full-featured interface for interacting with the AI agent:

1. **Open Chat**: Click the 💬 button to open
2. **Send Messages**: Type in the input field and press Enter or click Send
3. **Voice Input**: If chat is open, transcribed voice is automatically sent to the agent
4. **View History**: Chat history loads automatically when opening the window
5. **Real-time Updates**: Watch AI responses stream in as they're generated

See [CHAT_FEATURE.md](CHAT_FEATURE.md) for detailed documentation.

## Service Dependencies

### Required Services
1. **Transcription Service** (port 6001): For voice-to-text conversion
   ```bash
   cd transcribe
   python app.py
   ```

2. **Agent Service** (port 6002): For AI chat interactions
   ```bash
   cd agent-main
   python app.py --mode service
   ```

### Environment Variables
- `TRANSCRIBE_URL` — Transcription service URL (default: `http://127.0.0.1:6001/upload`)
- `AGENT_URL` — Agent service URL (default: `http://127.0.0.1:6002`)

## Testing

Run the test script to verify all components are working:
```powershell
python test_chat.py
```

This will test:
- Agent service health check
- Chat history retrieval
- Message streaming

## Notes
- The widget posts to the transcribe service at `TRANSCRIBE_URL` (default `http://127.0.0.1:6001/upload`).
- The widget communicates with the agent service at `AGENT_URL` (default `http://127.0.0.1:6002`).
- Chat history persists across sessions via the agent service.
- The chat window maintains its content even when closed and reopened.
