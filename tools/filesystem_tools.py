import os

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
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "The folder path relative to the project root (where main.py is called)."}
            },
            "required": ["relative_path"],
            "additionalProperties": False,
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
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "The file path relative to the project root (where main.py is called)."}
            },
            "required": ["relative_path"],
            "additionalProperties": False,
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
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "The file path relative to the project root (where main.py is called)."},
                "content": {"type": "string", "description": "The string content to write to the file."},
            },
            "required": ["relative_path", "content"],
            "additionalProperties": False,
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
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "The folder path relative to the project root (where main.py is called)."}
            },
            "required": ["relative_path"],
            "additionalProperties": False,
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
        if self.permission_required:
            permission = input(f"Create folder '{relative_path}'? Proceed? (y/n): ")
            if permission.lower() != 'y':
                return {"status": "error", "message": "Folder creation cancelled by user."}
        try:
            os.makedirs(abs_folder_path, exist_ok=True)
            return {"status": "success", "message": f"Folder '{relative_path}' created successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
