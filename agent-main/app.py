import sys
import os

# Add parent directory to path so we can import agent, tools, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from agent import Agent, AgentConfig
from agent.agent import make_serializable

from tools import (
    GetUserMemoriesTool,
    CreateUserMemoryTool,
    UpdateUserMemoryTool,
    DeleteUserMemoryTool,
    GetTodosTool,
    CreateTodoTool,
    UpdateTodoTool,
    DeleteTodoTool,
    ReadFolderContentTool,
    ReadFileContentTool,
    WriteFileContentTool,
    CreateFolderTool,
    RemovePathsTool,
    InsertTextInFileTool,
    ReplaceTextInFileTool,
    SearchInFileTool,
    CopyPathsTool,
    RenamePathTool,
    MovePathsTool,
    PathStatTool,
    CreateWordDocumentTool,
    RunTerminalCommandsTool,
    MultiXYPlotTool,
    WebSearchTool,
    ImageGenerationTool,
)

from chat_history import ChatHistoryManager
from tools.todo_tools import TodoManager

import base64
from PIL import Image
import io
import json
import argparse
import config


def color_text(text, color_code):
    # Windows PowerShell supports ANSI escape codes in recent versions
    return f"\033[{color_code}m{text}\033[0m"


# Initialize global variables
chat_history_manager = None
todo_manager = None
agent = None
agent_name = config.AGENT_NAME
user_id = config.USER_ID
project_root = None
partial_images = {}


def initialize_agent(load_history=True):
    """Initialize the agent and managers."""
    global chat_history_manager, todo_manager, agent, project_root, partial_images
    
    chat_history_manager = ChatHistoryManager()
    todo_manager = TodoManager()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    partial_images = {}
    
    # Load or clear history
    if load_history:
        chat_history_manager.load_history()
        chat_history_manager.load_generated_images()
    else:
        chat_history_manager.clear_history()
        chat_history_manager.clear_generated_images()
        todo_manager.clear_todos()
    
    # Initialize tools
    selected_tools = [
        GetUserMemoriesTool(),
        CreateUserMemoryTool(),
        UpdateUserMemoryTool(),
        DeleteUserMemoryTool(),
        GetTodosTool(),
        CreateTodoTool(),
        UpdateTodoTool(),
        DeleteTodoTool(),
        ReadFolderContentTool(root_path=project_root),
        ReadFileContentTool(root_path=project_root),
        WriteFileContentTool(root_path=project_root, permission_required=False),
        CreateFolderTool(root_path=project_root, permission_required=False),
        RemovePathsTool(root_path=project_root, permission_required=False),
        InsertTextInFileTool(root_path=project_root, permission_required=False),
        ReplaceTextInFileTool(root_path=project_root, permission_required=False),
        SearchInFileTool(root_path=project_root),
        CopyPathsTool(root_path=project_root),
        RenamePathTool(root_path=project_root),
        MovePathsTool(root_path=project_root),
        PathStatTool(root_path=project_root),
        WebSearchTool(),
    ]
    
    # Initialize agent configuration
    agent_config = AgentConfig(
        model_name=config.MODEL_NAME,
        temperature=config.TEMPERATURE,
        reasoning={"effort": config.REASONING_EFFORT, "summary": config.REASONING_SUMMARY},
        text={"verbosity": config.TEXT_VERBOSITY},
        store=False,
        stream=True,
        tool_choice="auto",
        include=["reasoning.encrypted_content"],
    )
    
    agent = Agent(
        name=agent_name,
        tools=selected_tools,
        user_id=user_id,
        config=agent_config,
    )


def process_message(user_input_text, max_turns=None):
    """Process a message and return the event stream."""
    if max_turns is None:
        max_turns = config.MAX_TURNS
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_input = f"> **Timestamp:** `{timestamp}`\nUser's input: {user_input_text}"
    
    user_message = {
        "role": "user",
        "content": [{"type": "input_text", "text": formatted_input}]
    }
    
    chat_history_manager.add_entry(user_message)
    
    # Start the agent run
    stream = agent.run(
        input_messages=chat_history_manager.get_history(),
        max_turns=max_turns,
    )
    
    return stream


def handle_event(event, interactive_mode=True):
    """Handle an event - print to console if interactive, return for service mode."""
    global partial_images
    
    # Handle image saving for both modes
    if event["type"] == "response.image_generation_call.partial_image":
        b64_data = event['data'].partial_image_b64
        item_id = event['data'].item_id
        sequence_number = event['data'].sequence_number
        image_bytes = base64.b64decode(b64_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        if item_id not in partial_images:
            partial_images[item_id] = {}
        partial_images[item_id][sequence_number] = image
        
        images_folder = os.path.join(project_root, "images")
        os.makedirs(images_folder, exist_ok=True)
        image_path = os.path.join(images_folder, f"{item_id}_partial_{sequence_number}.png")
        image.save(image_path, format="PNG")
        
        if interactive_mode:
            image.show(title=f"Partial Image {item_id}-{sequence_number}")
            print(color_text(f"Partial image saved to {image_path}", '32'), flush=True)
    
    elif event["type"] == "response.image_generation_call.completed":
        item_id = event['data'].item_id
        sequence_number = event['data'].sequence_number
        
        if item_id in partial_images and sequence_number in partial_images[item_id]:
            images_folder = os.path.join(project_root, "images")
            os.makedirs(images_folder, exist_ok=True)
            image_path = os.path.join(images_folder, f"{item_id}_completed_{sequence_number}.png")
            partial_images[item_id][sequence_number].save(image_path, format="PNG")
            
            if interactive_mode:
                print(color_text(f"Completed image saved to {image_path}", '32'), flush=True)
    
    elif event["type"] == "response.agent.done":
        chat_history_manager.append_entries(event["chat_history"])
        chat_history_manager.save_history()
        chat_history_manager.add_generated_images(event["generated_images"])
        chat_history_manager.save_generated_images()
        
        if interactive_mode:
            print(color_text("\n[Agent Done]", '32'), event.get("message", ""), 
                  f" (duration: {event.get('duration_seconds', 0)} seconds)", flush=True)
    
    # Print to console in interactive mode
    if interactive_mode:
        if event["type"] == "response.reasoning_summary_part.added":
            print(color_text("Thinking: ", '33'), end="", flush=True)
        elif event["type"] == "response.reasoning_summary_text.delta":
            print(event["delta"], end="", flush=True)
        elif event["type"] == "response.reasoning_summary_text.done":
            print("\n", flush=True)
        elif event["type"] == "response.content_part.added":
            print(color_text("Assistant: ", '36'), end="", flush=True)
        elif event["type"] == "response.output_text.delta":
            print(event["delta"], end="", flush=True)
        elif event["type"] == "response.output_text.done":
            print("\n", flush=True)
        elif event["type"] == "response.output_item.done":
            if event["item"].type == "function_call":
                print(color_text(f"\n[Function Call] {event['item'].name} with arguments: {event['item'].arguments}", '35'), flush=True)
            elif event["item"].type == "custom_tool_call":
                print(color_text(f"\n[Custom Tool Call] {event['item'].name} with arguments: {event['item'].input}", '35'), flush=True)
        elif event["type"] == "response.image_generation_call.generating":
            print(color_text(f"\n[Image Generation]...", '34'), flush=True)
        elif event["type"] == "response.image_generation_call.partial_image":
            print(color_text(f"\n[Image Generation] Partial Image {event['data'].partial_image_index}...", '34'), flush=True)
        elif event["type"] == "response.image_generation_call.completed":
            print(color_text(f"\n[Image Generation] Completed", '34'), flush=True)
        elif event["type"] == "response.completed":
            usage = event.get("usage", {})
            if usage:
                print(color_text(f"\n[Usage] {usage}", '34'), flush=True)


def run_interactive():
    """Run in interactive CLI mode."""
    # Ask about loading history
    while True:
        choice = input(color_text("\nDo you want to load previous chat history? (y/n): ", '35')).strip().lower()
        if choice in ['y', 'yes']:
            initialize_agent(load_history=True)
            break
        elif choice in ['n', 'no']:
            initialize_agent(load_history=False)
            break
        else:
            print(color_text("Please enter 'y' or 'n'.", '31'))
    
    print(color_text(f"Starting agent '{agent_name}' with user ID '{user_id}'...", '36'))
    
    while True:
        user_input = input(color_text("You: ", '35'))
        if user_input.lower() in ('exit', 'quit', 'q'):
            print(color_text("Exiting...", '31'))
            break
        
        if not user_input.strip():
            continue
        
        # Process message and handle events
        stream = process_message(user_input)
        for event in stream:
            handle_event(event, interactive_mode=True)


def run_service(port=None):
    """Run as FastAPI service."""
    if port is None:
        port = config.DEFAULT_PORT
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    import uvicorn
    
    app = FastAPI()
    
    # Initialize agent on startup with history loaded
    initialize_agent(load_history=True)
    
    class ChatRequest(BaseModel):
        message: str
        max_turns: int = config.MAX_TURNS
    
    @app.get("/health")
    def health():
        return {"status": "ok", "service": config.SERVICE_NAME}
    
    @app.get("/chat/history")
    def get_chat_history():
        """Get the current chat history."""
        return {"history": chat_history_manager.get_history()}
    
    @app.delete("/chat/history")
    def clear_chat_history():
        """Clear the chat history."""
        try:
            chat_history_manager.clear_history()
            chat_history_manager.clear_generated_images()
            todo_manager.clear_todos()
            return {"status": "ok", "message": "Chat history cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/chat/stream")
    async def chat_stream(request: ChatRequest):
        """Streaming chat endpoint - returns ALL events as SSE."""
        try:
            async def event_generator():
                stream = process_message(request.message, request.max_turns)
                
                for event in stream:
                    # Handle the event (saves history, images, etc.)
                    handle_event(event, interactive_mode=False)
                    
                    # Stream ALL events to the client
                    # Serialize the event properly (especially event.item objects)
                    serialized_event = make_serializable(event)
                    event_json = json.dumps(serialized_event, default=str)
                    yield f"data: {event_json}\n\n"
                
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    print(color_text(f"Starting agent service on port {port}...", '36'))
    print(color_text(f"API docs: http://localhost:{port}/docs", '33'))
    
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Agent - Interactive or Service Mode")
    parser.add_argument("--mode", choices=["interactive", "service"], default="interactive",
                        help="Run mode (default: interactive)")
    parser.add_argument("--port", type=int, default=config.DEFAULT_PORT,
                        help=f"Port for service mode (default: {config.DEFAULT_PORT})")
    
    args = parser.parse_args()
    
    if args.mode == "interactive":
        run_interactive()
    else:
        run_service(args.port)
