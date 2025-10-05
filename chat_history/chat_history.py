import os
import json
import uuid
from datetime import datetime

CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'chat_history.json')
IMAGES_FILE = os.path.join(os.path.dirname(__file__), 'generated_images.json')

class ChatHistoryManager:
    def __init__(self, file_path=CHAT_HISTORY_FILE, images_path=IMAGES_FILE):
        self.file_path = file_path
        self.images_path = images_path
        self.history = self.load_history()
        self.generated_images = self.load_generated_images()

    def _wrap_entry(self, content):
        """Wrap an OpenAI message object in metadata envelope."""
        content_json = json.dumps(content, ensure_ascii=False)
        content_size = len(content_json.encode('utf-8'))
        
        # Determine entry type from content structure
        # Priority 1: Check if it has a 'type' field at the top level (reasoning, function_call, function_call_output, message)
        if 'type' in content:
            entry_type = content['type']
        # Priority 2: Check if it has a 'role' field with 'content' array (user/assistant messages)
        elif 'role' in content and isinstance(content.get('content'), list) and len(content['content']) > 0:
            # Look at the first content item's type
            first_content_item = content['content'][0]
            if isinstance(first_content_item, dict) and 'type' in first_content_item:
                entry_type = first_content_item['type']
            else:
                entry_type = 'unknown'
        else:
            entry_type = 'unknown'
        
        return {
            "id": str(uuid.uuid4()),
            "ts": datetime.now().isoformat(),
            "type": entry_type,
            "size": content_size,
            "content": content
        }

    def _unwrap_entries(self, wrapped_entries):
        """Extract OpenAI message objects from wrapped entries."""
        return [entry['content'] for entry in wrapped_entries]

    def load_history(self):
        """Load history from file. Handles both old and new format."""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Check if data is already in new wrapped format
                if data and isinstance(data, list) and len(data) > 0:
                    first_entry = data[0]
                    if isinstance(first_entry, dict) and 'id' in first_entry and 'ts' in first_entry and 'content' in first_entry:
                        # Already in new format
                        return data
                    else:
                        # Old format - migrate to new format
                        print("Migrating chat history to new wrapped format...")
                        wrapped_data = [self._wrap_entry(entry) for entry in data]
                        # Save migrated data
                        self.history = wrapped_data
                        self.save_history()
                        return wrapped_data
                
                return data
        return []

    def save_history(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def get_history(self):
        """Get OpenAI-compatible message list (unwrapped contents)."""
        return self._unwrap_entries(self.history)

    def get_wrapped_history(self):
        """Get full wrapped entries with metadata."""
        return self.history

    def add_entry(self, entry):
        """Add a single entry (wraps it automatically)."""
        wrapped = self._wrap_entry(entry)
        self.history.append(wrapped)
        self.save_history()
        return wrapped['id']

    def append_entries(self, entries):
        """Append multiple entries (wraps them automatically)."""
        wrapped_entries = [self._wrap_entry(entry) for entry in entries]
        self.history.extend(wrapped_entries)
        self.save_history()
        return [e['id'] for e in wrapped_entries]

    def delete_entries_by_ids(self, entry_ids):
        """Delete entries by their wrapped IDs."""
        if not isinstance(entry_ids, list):
            entry_ids = [entry_ids]
        
        original_count = len(self.history)
        self.history = [entry for entry in self.history if entry['id'] not in entry_ids]
        deleted_count = original_count - len(self.history)
        
        if deleted_count > 0:
            self.save_history()
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "remaining_count": len(self.history)
        }

    def get_entry_by_id(self, entry_id):
        """Get a single wrapped entry by ID."""
        for entry in self.history:
            if entry['id'] == entry_id:
                return entry
        return None

    def clear_history(self):
        self.history = []
        self.save_history()

    def load_generated_images(self):
        if self.images_path and os.path.exists(self.images_path):
            with open(self.images_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        return []

    def save_generated_images(self):
        with open(self.images_path, 'w', encoding='utf-8') as f:
            json.dump(self.generated_images, f, ensure_ascii=False, indent=2)

    def get_generated_images(self):
        return self.generated_images
    
    def add_generated_images(self, images):
        if images:
            self.generated_images.extend(images)
        self.save_generated_images()

    def clear_generated_images(self):
        self.generated_images = []
        self.save_generated_images()
