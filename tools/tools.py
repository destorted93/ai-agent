import os
import json
from memory.memory import MemoryManager
from datetime import datetime
import matplotlib.pyplot as plt
import uuid

# Tool class definitions

class GetUserMemoriesTool:
    schema = {
        "type": "function",
        "name": "get_user_memories",
        "description": (
            "Retrieve a list of the user's long-term and emotional memories. These memories are concise (50-150 words), and include important facts, preferences, explicit requests, ideas, and emotional states or patterns detected over past interactions. "
            "Use this tool especially at the start of a new interaction or session, or whenever you lack information about the user. "
            "You may also call this tool at any time to refresh your knowledge of the user's current available memories."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }

    def run(self, **kwargs):
        memory_manager = MemoryManager()
        return {"status": "success", "memories": memory_manager.get_memories()}

class CreateUserMemoryTool:
    schema = {
        "type": "function",
        "name": "create_user_memory",
        "description": (
            "Create one or more memory entries for the user. Call this tool with a list of texts, each to be saved as a separate memory. "
            "Use this tool only for long-term or emotional memories: important facts, preferences, explicit requests, ideas, emotional states or patterns over multiple interactions. "
            "You may use this tool multiple times in a single response if needed, or provide multiple memories at once. "
            "Memory format rules: "
            "- Always output memory in English, regardless of chat language. "
            "- One line, compact, precise, understandable. "
            "- Start with 'User ...' "
            "- One fact per memory. "
            "- Aim for 50-150 characters when possible; shorter is fine if clear. "
            "Safety & Privacy: "
            "- Never store secrets: passwords, full credit cards, government IDs, API keys. "
            "Core principles: "
            "- Store only what truly matters: stable preferences, enduring facts, long-term goals, ongoing projects, constraints, repeatable workflows, strong dislikes, and user-specific context the assistant should consistently honor. "
            "- Never spam memories. "
            "- Prefer precision over verbosity. "
            "- Don't duplicate. "
            "- If a user explicitly asks 'remember this', and it meets value criteria, save it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string", "description": "Each text is one memory. Must follow all format, safety, and value rules above."},
                    "description": "A list of memory texts to save. Each text is one memory."
                }
            },
            "required": ["texts"],
        },
    }

    def run(self, texts):
        memory_manager = MemoryManager()
        results = []
        for text in texts:
            result = memory_manager.add_memory(text)
            results.append(result)
        return results

class UpdateUserMemoryTool:
    schema = {
        "type": "function",
        "name": "update_user_memory",
        "description": (
            "Update one or more existing user memories. Call this tool with a list of entries, each containing an id and the new text for the memory. "
            "This tool is used to revise or correct long-term or emotional memories previously stored. "
            "Rules for updating: "
            "- Only update memories that truly need revision (e.g., factual corrections, improved clarity, or user-requested changes). "
            "- Do not use for trivial edits or to spam updates. "
            "- Updated text must follow all memory format, safety, and value rules: English, one line, compact, precise, start with 'User ...', one fact per memory, 50-150 characters, no secrets, no duplicates. "
            "- If a memory id does not exist, return an error for that id. "
            "- If a user explicitly asks to update a memory and it meets value criteria, update it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "The id of the memory to update."},
                            "text": {"type": "string", "description": "The new text for the memory. Must follow all format, safety, and value rules."}
                        },
                        "required": ["id", "text"],
                    },
                    "description": "A list of memory updates, each with id and new text."
                }
            },
            "required": ["entries"],
        },
    }

    def run(self, entries):
        memory_manager = MemoryManager()
        results = []
        for entry in entries:
            result = memory_manager.update_memory(entry["id"], entry["text"])
            results.append(result)
        return results

class DeleteUserMemoryTool:
    schema = {
        "type": "function",
        "name": "delete_user_memory",
        "description": (
            "Delete one or more existing user memories. Call this tool with a list of memory ids to delete. "
            "Use this tool when you detect from context that certain memories should be removed, either due to explicit user request or when there are conflicts (e.g., new memories contradict existing ones and deletion is the only solution). "
            "After successful deletion, the ids of the remaining memories will be updated to be consecutive, starting from 1. "
            "Rules for deletion: "
            "- Only delete memories when truly necessary (explicit user request, irreconcilable conflict, or outdated/incorrect information). "
            "- Do not use for trivial or frequent deletions. "
            "- Always confirm the ids to be deleted are correct and relevant. "
            "- Never delete memories that are still valuable or needed for future interactions. "
            "- Return success for each deleted id, and error for each id not found or if deletion fails."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string", "description": "The id of the memory to delete."},
                    "description": "A list of memory ids to delete."
                }
            },
            "required": ["ids"],
        },
    }

    def run(self, ids):
        memory_manager = MemoryManager()
        results = memory_manager.delete_memories(ids)
        return results

class ReadFolderContentTool:
    schema = {
        "type": "function",
        "name": "read_folder_content",
        "description": (
            "List all files and folders in a specified folder. "
            "Provide the folder path relative to the project root (where main.py is called). "
            "This tool returns both files and directories. "
            "Use this tool to explore available resources, scripts, data files, and subfolders in a given folder. "
            "Do not use for reading file contents; use only to get names of items in the folder. "
            "Safety: Never use this tool to access system or hidden folders. Only use for project-relevant paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "The folder path relative to the project root (where main.py is called)."
                }
            },
            "required": ["relative_path"],
        },
    }

    def __init__(self, root_path):
        self.root_path = root_path

    def run(self, relative_path):
        folder_path = os.path.join(self.root_path, relative_path)
        if not os.path.isdir(folder_path):
            return {"status": "error", "message": "Folder not found."}
        items = os.listdir(folder_path)
        return {"status": "success", "items": items}

class ReadFileContentTool:
    schema = {
        "type": "function",
        "name": "read_file_content",
        "description": (
            "Read and return the content of a specified file as a string. "
            "Provide the file path relative to the project root (where main.py is called). "
            "Use this tool to access the contents of project files, scripts, or data files. "
            "Safety: Never use this tool to access system or hidden files. Only use for project-relevant paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "The file path relative to the project root (where main.py is called)."
                }
            },
            "required": ["relative_path"],
        },
    }

    def __init__(self, root_path):
        self.root_path = root_path

    def run(self, relative_path):
        file_path = os.path.join(self.root_path, relative_path)
        if not os.path.isfile(file_path):
            return {"status": "error", "message": "File not found."}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"status": "success", "content": content}
        except Exception as e:
            return {"status": "error", "message": str(e)}

class WriteFileContentTool:
    schema = {
        "type": "function",
        "name": "write_file_content",
        "description": (
            "Write string content to a specified file. Creates the file if it does not exist. "
            "Provide the file path relative to the project root (where main.py is called) and the content as a string. "
            "Use this tool to save or update project files, scripts, or data files. "
            "Safety: Never use this tool to access system or hidden files. Only use for project-relevant paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "The file path relative to the project root (where main.py is called)."
                },
                "content": {
                    "type": "string",
                    "description": "The string content to write to the file."
                }
            },
            "required": ["relative_path", "content"],
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, relative_path, content):
        file_path = os.path.join(self.root_path, relative_path)
        abs_file_path = os.path.abspath(file_path)
        abs_root_path = os.path.abspath(self.root_path)
        if not abs_file_path.startswith(abs_root_path):
            return {"status": "error", "message": "File path is outside the project scope."}
        folder = os.path.dirname(abs_file_path)
        # Always ask permission before writing
        if self.permission_required:
            permission = input(f"Write to file '{relative_path}'? This may create or overwrite files. Proceed? (y/n): ")
            if permission.lower() != 'y':
                return {"status": "error", "message": "File write cancelled by user."}
        if not os.path.exists(folder):
            os.makedirs(folder)
        try:
            with open(abs_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "message": f"File '{relative_path}' written successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

class CreateFolderTool:
    schema = {
        "type": "function",
        "name": "create_folder",
        "description": (
            "Create a folder at the specified path relative to the project root (where main.py is called). "
            "If the folder already exists, do nothing. "
            "Use this tool to organize project files and resources. "
            "Safety: Never use this tool to access system or hidden folders. Only use for project-relevant paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "The folder path relative to the project root (where main.py is called)."
                }
            },
            "required": ["relative_path"],
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, relative_path):
        folder_path = os.path.join(self.root_path, relative_path)
        abs_folder_path = os.path.abspath(folder_path)
        abs_root_path = os.path.abspath(self.root_path)
        if not abs_folder_path.startswith(abs_root_path):
            return {"status": "error", "message": "Folder path is outside the project scope."}
        # Always ask permission before creating folder
        if self.permission_required:
            permission = input(f"Create folder '{relative_path}'? Proceed? (y/n): ")
            if permission.lower() != 'y':
                return {"status": "error", "message": "Folder creation cancelled by user."}
        try:
            os.makedirs(abs_folder_path, exist_ok=True)
            return {"status": "success", "message": f"Folder '{relative_path}' created successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

class WebSearchTool:

    def __init__(self):
        self.schema = {
            "type": "web_search_preview"
        }

    def run(self, query):
        # Placeholder for actual web search implementation
        return {"status": "success"}

class ImageGenerationTool:    
    def __init__(self, quality="medium"):
        self.schema = {
            "type": "image_generation",
            "background": 'auto',
            "model": "gpt-image-1",
            "output_format": "png",
            "partial_images": 3,
            "quality": quality,
            "size": "auto",
        }

    def run(self, query):
        # Placeholder for actual image generation implementation
        return {"status": "success"}

class MultiXYPlotTool:
    schema = {
        "type": "function",
        "name": "generate_multi_xy_plot",
        "description": (
            "Generate a 2D plot with multiple datasets, each drawn as a line or dots. "
            "Each dataset must specify its type ('line' or 'dot'), label, and x/y as lists of objects with 'value' and 'label'. "
            "All datasets are drawn on the same plot, with a legend. "
            "Axis labels are combined from all datasets, so all values and labels are shown. "
            "Saves the generated image in the 'images' folder and returns the filename. "
            "Use this tool to visualize multiple series or collections of 2D data, with custom axis labels for each value."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "datasets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["line", "dot"],
                                "description": "Type of plot for this dataset: 'line' or 'dot'."
                            },
                            "label": {
                                "type": "string",
                                "description": "Label for this dataset (used in legend)."
                            },
                            "x": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "value": {"type": "number"},
                                        "label": {"type": "string"}
                                    },
                                    "required": ["value", "label"]
                                },
                                "description": "List of x objects: {value, label}."
                            },
                            "y": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "value": {"type": "number"},
                                        "label": {"type": "string"}
                                    },
                                    "required": ["value", "label"]
                                },
                                "description": "List of y objects: {value, label}."
                            }
                        },
                        "required": ["type", "label", "x", "y"],
                    },
                    "description": "List of datasets to plot. Each must specify type, label, x, y as lists of objects with value and label."
                },
                "title": {
                    "type": "string",
                    "description": "Optional title for the plot."
                }
            },
            "required": ["datasets"],
        },
    }

    def __init__(self, images_folder="images"):
        self.images_folder = images_folder
        if not os.path.exists(images_folder):
            os.makedirs(images_folder)

    def run(self, datasets, title=None):
        try:
            import matplotlib.pyplot as plt
            fig = plt.figure()
            ax = fig.add_subplot(111)
            # Build global x and y ticks/labels
            x_tick_map = {}
            y_tick_map = {}
            for dataset in datasets:
                for obj in dataset["x"]:
                    x_tick_map[obj["value"]] = obj["label"]
                for obj in dataset["y"]:
                    y_tick_map[obj["value"]] = obj["label"]
            x_ticks = sorted(x_tick_map.keys())
            x_labels = [x_tick_map[val] for val in x_ticks]
            y_ticks = sorted(y_tick_map.keys())
            y_labels = [y_tick_map[val] for val in y_ticks]
            # Draw all datasets
            for dataset in datasets:
                plot_type = dataset["type"]
                label = dataset["label"]
                x_vals = [obj["value"] for obj in dataset["x"]]
                y_vals = [obj["value"] for obj in dataset["y"]]
                if plot_type == "line":
                    ax.plot(x_vals, y_vals, label=label)
                elif plot_type == "dot":
                    ax.scatter(x_vals, y_vals, label=label)
            ax.set_xticks(x_ticks)
            ax.set_xticklabels(x_labels)
            ax.set_yticks(y_ticks)
            ax.set_yticklabels(y_labels)
            if title:
                ax.set_title(title)
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.legend()
            filename = f"{self.images_folder}/multi_xy_plot_{uuid.uuid4().hex[:8]}.png"
            plt.tight_layout()
            plt.savefig(filename)
            plt.close(fig)
            return {"status": "success", "filename": filename}
        except Exception as e:
            return {"status": "error", "message": str(e)}

class RunTerminalCommandsTool:
    schema = {
        "type": "function",
        "name": "run_terminal_commands",
        "description": (
            "Run one or more terminal commands in the Windows environment, starting from the project root directory. "
            "Provide a list of commands to execute. The tool will concatenate them using '&&' and run them as a single command. "
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "commands": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of terminal commands to run from the project root directory."
                }
            },
            "required": ["commands"],
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, commands):
        if not isinstance(commands, list) or not commands:
            print("No commands provided.")
            return {"status": "error", "message": "No commands provided."}
        command_str = " && ".join(commands)
        # If permission is required, ask user before running commands
        if self.permission_required:
            permission = input(f"Run the following command(s) from project root?\n{command_str}\nProceed? (y/n): ")
            if permission.lower() != 'y':
                print("Command execution cancelled by user.")
                return {"status": "error", "message": "Command execution cancelled by user."}
        try:
            import subprocess
            print(f"Executing: {command_str}")
            result = subprocess.run(command_str, shell=True, cwd=self.root_path, capture_output=True, text=True)
            print(f"Return code: {result.returncode}")
            print(f"Output:\n{result.stdout}")
            if result.stderr:
                print(f"Error:\n{result.stderr}")
            return {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            print(f"Exception: {str(e)}")
            return {"status": "error", "message": str(e)}
        
class CreateWordDocumentTool:
    schema = {
        "type": "function",
        "name": "create_word_document",
        "description": (
            "Create a Microsoft Word (.docx) document at the specified path relative to the project root (where main.py is called). "
            "Provide the filename (ending with .docx) and a list of paragraphs as strings. "
            "The tool will create the document, add each paragraph, and save it. "
            "Use this tool to generate reports, notes, or formatted documents for project use. "
            "Safety: Only create documents within the project scope. Never overwrite system or hidden files."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "The file path (ending with .docx) relative to the project root."
                },
                "paragraphs": {
                    "type": "array",
                    "items": {"type": "string", "description": "Paragraph text to add to the document."},
                    "description": "A list of paragraphs to add to the document."
                }
            },
            "required": ["relative_path", "paragraphs"],
        },
    }

    def __init__(self, root_path, permission_required=True):
        self.root_path = root_path
        self.permission_required = permission_required

    def run(self, relative_path, paragraphs):
        file_path = os.path.join(self.root_path, relative_path)
        abs_file_path = os.path.abspath(file_path)
        abs_root_path = os.path.abspath(self.root_path)
        if not abs_file_path.startswith(abs_root_path):
            return {"status": "error", "message": "File path is outside the project scope."}
        folder = os.path.dirname(abs_file_path)
        # Always ask permission before creating Word document
        if self.permission_required:
            permission = input(f"Create Word document '{relative_path}'? Proceed? (y/n): ")
            if permission.lower() != 'y':
                return {"status": "error", "message": "Word document creation cancelled by user."}
        if not os.path.exists(folder):
            os.makedirs(folder)
        try:
            from docx import Document
        except ImportError:
            return {"status": "error", "message": "python-docx package not installed."}
        try:
            document = Document()
            for para in paragraphs:
                document.add_paragraph(para)
            document.save(abs_file_path)
            return {"status": "success", "message": f"Word document '{relative_path}' created successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

