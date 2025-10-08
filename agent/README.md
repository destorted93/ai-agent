# Agent Core

Core AI agent implementation with streaming support and tool execution.

## What it does

Wraps OpenAI's API to provide:
- Tool/function calling
- Streaming responses
- Token usage tracking
- Custom system prompts
- Stop/interrupt capability

## Key Components

### Agent Class

Main class that handles:
- Chat completions with tools
- Streaming responses
- Function call execution
- Token tracking
- History management

### AgentConfig

Configuration for:
- Model selection
- Temperature and parameters
- System prompt templates
- Response preferences

## Usage

```python
from agent import Agent, AgentConfig

config = AgentConfig(
    model="gpt-4o",
    temperature=0.7
)

agent = Agent(
    name="MyAgent",
    tools=[...],
    user_id="user123",
    config=config
)

response = agent.run(
    user_input="Hello!",
    callback=lambda text: print(text, end="")
)
```

## Features

- **Streaming**: Real-time response streaming
- **Tools**: Automatic function calling
- **Memory**: Maintains conversation context
- **Tokens**: Tracks usage per turn
- **Images**: Handles image inputs and outputs
- **Stop**: Can interrupt long-running tasks

## Integration

Used by `agent-main/app.py` for both CLI and service modes.
