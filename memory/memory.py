import os
import json
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(__file__), 'memories.json')

class MemoryManager:
    def __init__(self, file_path=MEMORY_FILE):
        self.file_path = file_path
        # Ensure the memories file exists on initialization
        if not os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
            except Exception:
                # If file creation fails, proceed; load_memories will handle gracefully
                pass
        self.memories = self.load_memories()

    def load_memories(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    else:
                        return []
            except Exception as e:
                return []
        return []

    def save_memories(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_memories(self):
        return self.memories

    def add_memory(self, text):
        try:
            new_id = str(len(self.memories) + 1)
            now = datetime.now()
            memory = {
                "id": new_id,
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M'),
                "text": text
            }
            self.memories.append(memory)
            save_result = self.save_memories()
            if save_result["status"] == "success":
                return {"status": "success", "id": new_id, "memory": memory}
            else:
                return {"status": "error", "message": save_result.get("message", "Failed to save memory.")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_memory(self, memory_id, new_text):
        for memory in self.memories:
            if memory['id'] == memory_id:
                memory['text'] = new_text
                save_result = self.save_memories()
                if save_result["status"] == "success":
                    return {"status": "success", "id": memory_id, "memory": memory}
                else:
                    return {"status": "error", "id": memory_id, "message": save_result.get("message", "Failed to save memory.")}
        return {"status": "error", "id": memory_id, "message": "Memory id not found."}

    def delete_memories(self, ids):
        found = set()
        for id_ in ids:
            if any(m['id'] == id_ for m in self.memories):
                found.add(id_)
        self.memories = [m for m in self.memories if m['id'] not in found]
        # Renumber IDs after deletion
        for idx, memory in enumerate(self.memories, start=1):
            memory['id'] = str(idx)
        save_result = self.save_memories()
        results = []
        for id_ in ids:
            if id_ in found:
                if save_result["status"] == "success":
                    results.append({"status": "success", "id": id_})
                else:
                    results.append({"status": "error", "id": id_, "message": save_result.get("message", "Failed to save memory.")})
            else:
                results.append({"status": "error", "id": id_, "message": "Memory id not found."})
        return results
