import os
from memory import MemoryManager

class GetUserMemoriesTool:
    schema = {
        "type": "function",
        "name": "get_user_memories",
        "description": (
            "Retrieve a list of the user's long-term and emotional memories. These memories are concise (50-150 words), and include important facts, preferences, explicit requests, ideas, and emotional states or patterns detected over past interactions. "
            "Use this tool especially at the start of a new interaction or session, or whenever you lack information about the user. "
            "You may also call this tool at any time to refresh your knowledge of the user's current available memories."
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
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string", "description": "Each text is one memory. Must follow all format, safety, and value rules above."},
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
            "Update one or more existing user memories. Call this tool with a list of entries, each containing an id and the new text for the memory. "
            "This tool is used to revise or correct long-term or emotional memories previously stored. "
            "Rules for updating: "
            "- Only update memories that truly need revision (e.g., factual corrections, improved clarity, or user-requested changes). "
            "- Do not use for trivial edits or to spam updates. "
            "- Updated text must follow all memory format, safety, and value rules: English, one line, compact, precise, start with 'User ...', one fact per memory, 50-150 characters, no secrets, no duplicates. "
            "- If a memory id does not exist, return an error for that id. "
            "- If a user explicitly asks to update a memory and it meets value criteria, update it."
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
                            "text": {"type": "string", "description": "The new text for the memory. Must follow all format, safety, and value rules."},
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
