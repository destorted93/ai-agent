import os
import json
from datetime import datetime

TODOS_FILE = os.path.join(os.path.dirname(__file__), 'todos.json')
LEGACY_PLANS_FILE = os.path.join(os.path.dirname(__file__), 'plans.json')

class TodoManager:
    def __init__(self, file_path=TODOS_FILE):
        self.file_path = file_path
        self.todos = self.load_todos()

    def load_todos(self):
        # Prefer new todos.json; fall back to legacy plans.json for migration
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                return []
        elif os.path.exists(LEGACY_PLANS_FILE):
            try:
                with open(LEGACY_PLANS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Save migrated data into todos.json
                    if isinstance(data, list):
                        self.todos = data
                        self.save_todos()
                        return data
            except Exception:
                pass
        return []

    def save_todos(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.todos, f, ensure_ascii=False, indent=2)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_todos(self):
        return self.todos

    def add_todo(self, text, status="new"):
        try:
            new_id = str(len(self.todos) + 1)
            now = datetime.now()
            todo = {
                "id": new_id,
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M'),
                "text": text,
                "status": status  # 'new' or 'done'
            }
            self.todos.append(todo)
            save_result = self.save_todos()
            if save_result["status"] == "success":
                return {"status": "success", "id": new_id, "todo": todo}
            else:
                return {"status": "error", "message": save_result.get("message", "Failed to save todo.")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_todo(self, todo_id, new_text=None, new_status=None):
        for todo in self.todos:
            if todo['id'] == todo_id:
                updated = False
                if new_text is not None:
                    todo['text'] = new_text
                    updated = True
                if new_status is not None:
                    # Accept boolean or string; normalize boolean to 'done'/'new'
                    if isinstance(new_status, bool):
                        todo['status'] = 'done' if new_status else 'new'
                    else:
                        todo['status'] = new_status
                    updated = True
                if not updated:
                    return {"status": "error", "id": todo_id, "message": "No updates provided."}
                save_result = self.save_todos()
                if save_result["status"] == "success":
                    return {"status": "success", "id": todo_id, "todo": todo}
                else:
                    return {"status": "error", "id": todo_id, "message": save_result.get("message", "Failed to save todo.")}
        return {"status": "error", "id": todo_id, "message": "To-Do id not found."}

    def delete_todos(self, ids):
        found = set()
        for id_ in ids:
            if any(t['id'] == id_ for t in self.todos):
                found.add(id_)
        self.todos = [t for t in self.todos if t['id'] not in found]
        # Renumber IDs after deletion
        for idx, todo in enumerate(self.todos, start=1):
            todo['id'] = str(idx)
        save_result = self.save_todos()
        results = []
        for id_ in ids:
            if id_ in found:
                if save_result["status"] == "success":
                    results.append({"status": "success", "id": id_})
                else:
                    results.append({"status": "error", "id": id_, "message": save_result.get("message", "Failed to save todos.")})
            else:
                results.append({"status": "error", "id": id_, "message": "To-Do id not found."})
        return results
    
    def clear_todos(self):
        self.todos = []
        return self.save_todos()


class GetTodosTool:
    schema = {
        "type": "function",
        "name": "get_todos",
        "description": (
            "Retrieve the current ordered to-do items (id, date, time, text, status). Call before: (a) creating a new to-do batch; (b) revising/deleting items when state may have changed; always re-fetch after deletion. "
            "Use to synchronize internal reasoning with persisted to-do state so you never act on stale assumptions."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    }

    def run(self, **kwargs):
        todo_manager = TodoManager()
        return {"status": "success", "todos": todo_manager.get_todos()}


class CreateTodoTool:
    schema = {
        "type": "function",
        "name": "create_todo",
        "description": (
            "Add one or more atomic to-do items. Provide an ordered list of item texts (each one executable without further decomposition). "
            "Call only after inspecting existing items with get_todos and only for items not already present. Newly created items start with status='new'."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string", "description": "Each text is one to-do item."},
                    "description": "A list of to-do item texts to save. Each text is one to-do item.",
                }
            },
            "required": ["texts"],
            "additionalProperties": False,
        },
    }

    def run(self, texts):
        todo_manager = TodoManager()
        results = []
        for text in texts:
            result = todo_manager.add_todo(text)
            results.append(result)
        return results


class UpdateTodoTool:
    schema = {
        "type": "function",
        "name": "update_todo",
        "description": (
            "Revise existing to-do items or mark them complete. Typical usage: after executing an item, set status='done'. You may also refine the wording of future items to reflect new context. "
            "Provide a list of entries each with an 'id' plus optional 'text' and/or 'status'. If a provider requires sending all fields, resend unchanged text/status values."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "The id of the to-do to update."},
                            "text": {"type": "string", "description": "(Optional) The new text for the to-do item."},
                            "status": {"type": "string", "enum": ["new", "done"], "description": "(Optional) 'new' = not executed; 'done' = executed."},
                        },
                        "required": ["id", "text", "status"],
                        "additionalProperties": False,
                    },
                    "description": "A list of to-do updates, each with id and optional new text/status.",
                }
            },
            "required": ["entries"],
            "additionalProperties": False,
        },
    }

    def run(self, entries):
        todo_manager = TodoManager()
        results = []
        for entry in entries:
            result = todo_manager.update_todo(entry["id"], entry.get("text"), entry.get("status"))
            results.append(result)
        return results


class DeleteTodoTool:
    schema = {
        "type": "function",
        "name": "delete_todo",
        "description": (
            "Remove obsolete or superseded to-do items by id. Use this when re-prioritization makes certain items irrelevant, or after splitting/merging items. Remaining items are re-numbered consecutively starting at 1—always re-fetch with get_todos after deletion before further updates."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string", "description": "The id of the to-do to delete."},
                    "description": "A list of to-do ids to delete.",
                }
            },
            "required": ["ids"],
            "additionalProperties": False,
        },
    }

    def run(self, ids):
        todo_manager = TodoManager()
        results = todo_manager.delete_todos(ids)
        return results


class ClearTodosTool:
    schema = {
        "type": "function",
        "name": "clear_todos",
        "description": (
            "Delete all to-do items. Use when switching to a new, unrelated task or when resetting planning."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    }

    def run(self, **kwargs):
        todo_manager = TodoManager()
        result = todo_manager.clear_todos()
        return result
