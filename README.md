# ai-agent
General purpose AI Agent with OpenAI Python SDK

## Project Structure

- **agent-main/** - Main conversational AI agent with tool capabilities
- **agent/** - Core agent implementation
- **tools/** - Various tool implementations (filesystem, web, memory, todos, etc.)
- **chat_history/** - Chat history management
- **memory/** - Persistent memory system
- **transcribe/** - Audio transcription service (FastAPI)
- **widget/** - Desktop widget for transcription
- **service-template/** - Template for creating new services

## Quick Start

### Main Agent

Run the conversational AI agent:

```bash
python agent-main/main.py
```

Or use the batch script (Windows):

```bash
run_agent.bat
```

### Services

Run the transcription services (FastAPI + Widget):

```bash
run_services.bat [OPENAI_API_KEY] [PORT]
```

## Installation

Each service has its own `requirements.txt`. Install dependencies as needed:

```bash
# For the main agent
pip install -r agent-main/requirements.txt

# For transcription service
pip install -r transcribe/requirements.txt

# For widget
pip install -r widget/requirements.txt
```
