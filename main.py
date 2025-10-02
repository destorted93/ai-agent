from datetime import datetime
from agent import Agent, AgentConfig

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
    CreateWordDocumentTool,
    RunTerminalCommandsTool,
    MultiXYPlotTool,
    WebSearchTool,
    ImageGenerationTool,
)

from chat_history import ChatHistoryManager
from tools.todo_tools import TodoManager

import os
import base64
from PIL import Image
import io


def color_text(text, color_code):
    # Windows PowerShell supports ANSI escape codes in recent versions
    return f"\033[{color_code}m{text}\033[0m"

if __name__ == "__main__":
    # Initialize chat history manager
    chat_history_manager = ChatHistoryManager()
    todo_manager = TodoManager()

    agent_name = "Djasha"
    user_id = "user_12345"
    # Select which tools to include here
    project_root = os.path.dirname(os.path.abspath(__file__))
    selected_tools = [
        GetUserMemoriesTool(),
        CreateUserMemoryTool(),
        UpdateUserMemoryTool(),
        DeleteUserMemoryTool(),
        GetTodosTool(),
        CreateTodoTool(),
        UpdateTodoTool(),
        DeleteTodoTool(),
        # MultiXYPlotTool(),
        ReadFolderContentTool(root_path=project_root),
        ReadFileContentTool(root_path=project_root),
        WriteFileContentTool(root_path=project_root, permission_required=False),
        CreateFolderTool(root_path=project_root, permission_required=False),
        RemovePathsTool(root_path=project_root, permission_required=False),
        InsertTextInFileTool(root_path=project_root, permission_required=False),
        ReplaceTextInFileTool(root_path=project_root, permission_required=False),
        SearchInFileTool(root_path=project_root),
        # RunTerminalCommandsTool(root_path=project_root, permission_required=True),
        # CreateWordDocumentTool(root_path=project_root, permission_required=False),
        WebSearchTool(),
        # ImageGenerationTool(quality="medium"),
        # Add more tools as needed
    ]

    # Mini-loop for chat history loading
    while True:
        choice = input(color_text("\nDo you want to load previous chat history? (y/n): ", '35')).strip().lower()
        if choice in ['y', 'yes']:
            chat_history_manager.load_history()
            chat_history_manager.load_generated_images()
            break
        elif choice in ['n', 'no']:
            chat_history_manager.clear_history()
            chat_history_manager.clear_generated_images()
            todo_manager.clear_todos()
            break
        else:
            print(color_text("Please enter 'y' or 'n'.", '31'))

    # Initialize the agent with the selected tools and chat history
    # Define configuration explicitly
    config = AgentConfig(
        model_name="gpt-5",
        temperature=1.0,
        reasoning={"effort": "low", "summary": "auto"},
        text={"verbosity": "medium"},
        store=False,
        stream=True,
        tool_choice="auto",
        include=["reasoning.encrypted_content"],
    )

    agent = Agent(
        name=agent_name,
        tools=selected_tools,
        user_id=user_id,
        config=config,
    )

    print(color_text(f"Starting agent '{agent_name}' with user ID '{user_id}'...", '36'))

    partial_images = {}

    while True:
        user_input = input(color_text("You: ", '35'))
        if user_input.lower() in ('exit', 'quit', 'q'):
            print(color_text("Exiting...", '31'))
            break

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_input = f"> **Timestamp:** `{timestamp}`\nUser's input: {user_input}"
        
        user_message = {
            "role": "user",
            "content": [{ "type": "input_text", "text": user_input },]
        }
        # for img in chat_history_manager.get_generated_images():
        #     user_message["content"].append(img)

        chat_history_manager.add_entry(user_message)

        max_turns = 256

        # Start the agent run
        stream = agent.run(
            input_messages=chat_history_manager.get_history(),
            max_turns=max_turns,
        )


        # Process the stream of events from the agent
        for event in stream:
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
                b64_data = event['data'].partial_image_b64
                item_id = event['data'].item_id
                sequence_number = event['data'].sequence_number
                image_bytes = base64.b64decode(b64_data)
                image = Image.open(io.BytesIO(image_bytes))
                image.show(title=f"Partial Image {item_id}-{sequence_number}")
                # Store the partial image for saving later
                if item_id not in partial_images:
                    partial_images[item_id] = {}
                partial_images[item_id][sequence_number] = image
                # Save each partial image with sequence_number
                images_folder = os.path.join(project_root, "images")
                os.makedirs(images_folder, exist_ok=True)
                image_path = os.path.join(images_folder, f"{item_id}_partial_{sequence_number}.png")
                image.save(image_path, format="PNG")
                print(color_text(f"Partial image saved to {image_path}", '32'), flush=True)
            elif event["type"] == "response.image_generation_call.completed":
                print(color_text(f"\n[Image Generation] Completed", '34'), flush=True)
                item_id = event['data'].item_id
                sequence_number = event['data'].sequence_number
                # Save the last partial image for this item_id and sequence_number
                if item_id in partial_images and sequence_number in partial_images[item_id]:
                    images_folder = os.path.join(project_root, "images")
                    os.makedirs(images_folder, exist_ok=True)
                    image_path = os.path.join(images_folder, f"{item_id}_completed_{sequence_number}.png")
                    partial_images[item_id][sequence_number].save(image_path, format="PNG")
                    print(color_text(f"Completed image saved to {image_path}", '32'), flush=True)
            elif event["type"] == "response.agent.done":
                print(color_text("\n[Agent Done]", '32'), event.get("message", ""), f" (duration: {event.get('duration_seconds', 0)} seconds)", flush=True)
                chat_history_manager.append_entries(event["chat_history"])
                chat_history_manager.save_history()

                chat_history_manager.add_generated_images(event["generated_images"])
                chat_history_manager.save_generated_images()
            elif event["type"] == "response.completed":
                usage = event.get("usage", {})
                if usage:
                    print(color_text(f"\n[Usage] {usage}", '34'), flush=True)
