import os
from memory import MemoryManager

class GetUserMemoriesTool:
    schema = {
        "type": "function",
        "name": "get_user_memories",
        "description": (
            "Retrieve the user's long-term and emotional memories. Entries are concise (typically 50–150 characters) and include important facts, preferences, explicit requests, ideas, and patterns over past interactions. "
            "Use at session start, when uncertain about the user, or to refresh current memories."
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
        memory_manager = MemoryManager()
        return {"status": "success", "memories": memory_manager.get_memories()}

class CreateUserMemoryTool:
    schema = {
        "type": "function",
        "name": "create_user_memory",
        "description": (
            "Create one or more memory entries for the user. Each text becomes a separate memory. "
            "Use only for durable facts: preferences, goals, constraints, ongoing projects, repeatable workflows, strong dislikes, or explicit 'remember this' requests. "
            "Format: English; one line; start with 'User ...'; one fact per memory; aim for 50–150 characters. "
            "Never store secrets (passwords, credit cards, IDs, API keys). Avoid duplication and spam. Prefer precision over verbosity."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string", "description": "Each text is one memory. Must follow the format and safety rules."},
                    "description": "A list of memory texts to save. Each text is one memory.",
                }
            },
            "required": ["texts"],
            "additionalProperties": False,
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
            "Update existing user memories. Use only for necessary corrections or clarity improvements, or when the user requests changes. "
            "Updated text must follow all memory rules: English, one line, start with 'User ...', one fact, 50–150 characters, no secrets, no duplicates."
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
                            "id": {"type": "string", "description": "The id of the memory to update."},
                            "text": {"type": "string", "description": "The new text for the memory (must follow rules)."},
                        },
                        "required": ["id", "text"],
                        "additionalProperties": False,
                    },
                    "description": "A list of memory updates, each with id and new text.",
                }
            },
            "required": ["entries"],
            "additionalProperties": False,
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
            "Delete one or more existing user memories by id. Use for explicit user requests or irreconcilable conflicts/outdated info. "
            "After successful deletion, remaining memory ids are re-numbered starting at 1. Avoid deleting still-valuable memories."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string", "description": "The id of the memory to delete."},
                    "description": "A list of memory ids to delete.",
                }
            },
            "required": ["ids"],
            "additionalProperties": False,
        },
    }

    def run(self, ids):
        memory_manager = MemoryManager()
        results = memory_manager.delete_memories(ids)
        return results
