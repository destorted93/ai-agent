# ai-agent
General purpose AI Agent with OpenAI Python SDK

## 🚀 One-Click Launch

**Double-click `START.bat`** to launch everything you need:
- Transcribe Service (voice-to-text)
- Agent Service (AI chat)
- Widget (desktop interface with chat window)

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Project Structure

- **agent-main/** - Main conversational AI agent with tool capabilities and service mode
- **agent/** - Core agent implementation with streaming support
- **tools/** - Various tool implementations (filesystem, web, memory, todos, etc.)
- **chat_history/** - Chat history management and persistence
- **memory/** - Persistent memory system for user context
- **transcribe/** - Audio transcription service using OpenAI Whisper (FastAPI)
- **widget/** - Desktop widget with voice recording and chat window
- **service-template/** - Template for creating new services

## Features

### 🎤 Voice Input
- Record audio with desktop widget
- Automatic transcription using OpenAI Whisper
- Multi-language support (English, Romanian, Russian, German, French, Spanish)

### 💬 Chat Window
- Persistent chat interface with AI agent
- Real-time streaming responses
- Voice and text input support
- Color-coded display (thinking, responses, function calls)
- Chat history preserved across sessions

### 🛠️ Tools & Capabilities
- File system operations (read, write, search)
- Web search and scraping
- Memory management
- Todo list management
- Document creation
- Data visualization
- Terminal command execution

## Quick Start

### 🎯 Recommended: One-Click Launch

Simply run:
```bash
START.bat
```

This launches all three services with proper configuration.

### Alternative: Individual Components

#### Main Agent (Interactive CLI)
```bash
python agent-main/app.py --mode interactive
```

#### Agent Service (API)
```bash
python agent-main/app.py --mode service --port 6002
```

#### Services (Transcribe + Agent + Widget)
```bash
run_services.bat [OPENAI_API_KEY]
```

## Installation

### Quick Install (Recommended)

Run the installer to set up all dependencies at once:
```bash
INSTALL.bat
```

### Manual Install

Each service has its own `requirements.txt`. Install dependencies as needed:

```bash
# For the main agent
pip install -r agent-main/requirements.txt

# For transcription service
pip install -r transcribe/requirements.txt

# For widget
pip install -r widget/requirements.txt
```

### Environment Setup

Set your OpenAI API key:
```powershell
# PowerShell (permanent)
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-...', 'User')

# Or just enter it when prompted by START.bat
```

## Usage Guide

### Getting Started
1. **Install**: Run `INSTALL.bat` to install all dependencies
2. **Launch**: Double-click `START.bat` to start all services
3. **Use**: Click 💬 on the widget to open chat, or use voice recording

For detailed instructions, see [LAUNCH_GUIDE.md](LAUNCH_GUIDE.md)

### Widget Controls
- **▶ Start Recording** - Record voice input
- **⏹ Stop Recording** - Stop and transcribe
- **💬 Chat** - Open/close chat window
- **⚙ Settings** - Language selection and options

### Chat Window
- Type messages or use voice input
- Real-time streaming responses
- Persistent chat history
- Color-coded display for different response types

For detailed chat features, see [widget/CHAT_FEATURE.md](widget/CHAT_FEATURE.md)

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide
- **[LAUNCH_GUIDE.md](LAUNCH_GUIDE.md)** - Detailed launch instructions
- **[COMPLETE_SETUP.md](COMPLETE_SETUP.md)** - Complete setup summary
- **[widget/CHAT_FEATURE.md](widget/CHAT_FEATURE.md)** - Chat feature documentation
- **[CHAT_IMPLEMENTATION_SUMMARY.md](CHAT_IMPLEMENTATION_SUMMARY.md)** - Technical details

## API Documentation

When services are running, access interactive API docs:
- **Transcribe Service**: http://localhost:6001/docs
- **Agent Service**: http://localhost:6002/docs

## Services Overview

### Transcribe Service (Port 6001)
- Audio transcription using OpenAI Whisper
- Multi-language support
- FastAPI-based REST API

### Agent Service (Port 6002)
- Conversational AI with GPT-5
- Tool execution (file ops, web search, memory, todos)
- Streaming responses
- Chat history management

### Widget (Desktop App)
- Always-on-top interface
- Voice recording with transcription
- Chat window with persistent history
- Draggable, customizable position
