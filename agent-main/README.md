# Agent Main

Primary agent application with tool integration and dual operation modes.

## What it does

The main conversational AI agent that:
- Manages tools (filesystem, web, memory, todos, etc.)
- Handles chat history and context
- Supports both CLI and API modes
- Integrates all services and capabilities

## Operation Modes

### Interactive Mode (CLI)
Direct terminal interaction with the agent.

```bash
python agent-main/app.py --mode interactive
```

Features:
- Type messages directly
- See real-time streaming responses
- Token usage tracking
- Commands: `/clear`, `/stats`, `/quit`

### Service Mode (API)
Runs as FastAPI service for widget integration.

```bash
python agent-main/app.py --mode service --port 6002
```

Endpoints:
- `POST /chat` - Send message, get streaming response
- `POST /stop` - Interrupt current agent run
- `GET /health` - Health check
- WebSocket `/ws` - Real-time chat streaming

## Integrated Tools

- **Memory Management**: User context and preferences
- **Chat History**: Conversation persistence
- **Todo Management**: Task tracking
- **Filesystem**: Read, write, search files
- **Web Tools**: Search and scraping
- **Document Creation**: Generate Word docs
- **Visualization**: Create charts and plots
- **Terminal**: Execute commands
- **Image Generation**: AI-generated images

## Configuration

Edit `config.py`:
- `AGENT_NAME` - Agent identifier
- `USER_ID` - User identifier
- `OPENAI_API_KEY` - API key (or set env var)

## Running

### Via Launcher (Recommended)
```bash
START.bat
```

### Manual
```bash
# Interactive
python agent-main/app.py --mode interactive

# Service
python agent-main/app.py --mode service --port 6002
```

## Dependencies

Install: `pip install -r agent-main/requirements.txt`

## Integration

Service mode is used by the widget for the desktop interface
