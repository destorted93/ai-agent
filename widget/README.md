# Desktop Widget

PyQt6-based desktop interface with voice recording and chat window.

## What it does

Provides a floating desktop widget for:
- Voice recording with visual feedback
- Text input for chat
- Real-time streaming chat responses
- Screenshot capture and sharing
- Persistent chat history display

## Features

### Voice Recording
- Click microphone to record
- Visual waveform display
- Auto-upload to transcribe service
- Multi-language support

### Chat Window
- Expandable chat interface
- Color-coded messages:
  - 🔵 Blue: Thinking/reasoning
  - 🟢 Green: Agent responses
  - 🟡 Yellow: Function calls
- Markdown support
- Image display (generated or screenshots)
- Auto-scroll
- Resizable and draggable

### Screenshot Tool
- Capture screen areas
- Send directly to agent
- Visual selection overlay

## Configuration

Set in widget code:
- Transcribe service URL (default: `http://localhost:6000`)
- Agent service URL (default: `http://localhost:6002`)
- Default language for transcription

## Running

```bash
python widget/widget.py
```

Or via the launcher:
```bash
START.bat
```

## Dependencies

- PyQt6
- sounddevice
- requests
- websockets

Install: `pip install -r widget/requirements.txt`

## Integration

Connects to transcribe and agent services via HTTP/WebSocket
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
