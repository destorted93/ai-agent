import os
import json

CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'chat_history.json')
IMAGES_FILE = os.path.join(os.path.dirname(__file__), 'generated_images.json')

class ChatHistoryManager:
    def __init__(self, file_path=CHAT_HISTORY_FILE, images_path=IMAGES_FILE):
        self.file_path = file_path
        self.images_path = images_path
        self.history = self.load_history()
        self.generated_images = self.load_generated_images()

    def load_history(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        return []

    def save_history(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def get_history(self):
        return self.history

    def add_entry(self, entry):
        self.history.append(entry)
        self.save_history()

    def append_entries(self, entries):
        self.history.extend(entries)
        self.save_history()

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
