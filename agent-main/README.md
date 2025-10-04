# Agent Main

The main conversational AI agent with tool capabilities.

## Features

- Interactive chat interface with chat history management
- Memory system for persistent user information
- Todo list management
- File system operations (read, write, create, delete, search)
- Web search capabilities
- Image generation (optional)
- Document creation (optional)
- Terminal command execution (optional)
- Data visualization tools (optional)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the agent from the project root:

```bash
python agent-main/main.py
```

Or from within the agent-main directory:

```bash
cd agent-main
python main.py
```

## Configuration

The agent uses the following configuration:
- Model: gpt-5
- Temperature: 1.0
- Reasoning effort: medium
- Streaming: enabled

You can modify these settings in the `AgentConfig` initialization within `main.py`.

## Tools

The agent comes with various tools that can be enabled or disabled by commenting/uncommenting them in the `selected_tools` list:

- **Memory Tools**: Store and retrieve user information
- **Todo Tools**: Manage task lists
- **File System Tools**: Read, write, and manipulate files and folders
- **Web Search**: Search the internet
- **Image Generation**: Generate images (requires API access)
- **Document Tools**: Create Word documents
- **Visualization Tools**: Create plots and charts
- **Terminal Tools**: Execute shell commands (use with caution)

## Chat History

On startup, you can choose to:
- Load previous chat history (y/n)
- Start fresh with cleared history and todos

Chat history is automatically saved after each interaction.
