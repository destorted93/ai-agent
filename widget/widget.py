
# Put all three controls in the same row
import sys
import os
import sounddevice as sd
import wave
import requests
import io
import time
import threading
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                              QHBoxLayout, QMenu, QTextEdit, QLineEdit, QScrollArea,
                              QLabel, QFrame, QSizePolicy)
from PyQt6.QtGui import QAction, QTextCursor, QFont, QTextOption
from PyQt6.QtCore import Qt, QPoint, QEvent, pyqtSignal, QObject, QThread, pyqtSlot, QTimer


class ChatWindow(QWidget):
    """Separate chat window that maintains its state."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("AI Chat")
        self.resize(600, 700)
        
        # Chat display area
        layout = QVBoxLayout(self)
        
        # Scrollable chat display
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(10)
        
        scroll.setWidget(self.chat_container)
        layout.addWidget(scroll)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)
        
        # Store chat history
        self.chat_history = []
        self.current_ai_widget = None
        
        # Styling
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QScrollArea {
                border: none;
            }
        """)
        
        self.parent_widget = parent
    
    def add_user_message(self, text):
        """Add user message to chat (right-aligned, max 80% width)."""
        msg_widget = QWidget()
        msg_layout = QHBoxLayout(msg_widget)
        msg_layout.setContentsMargins(0, 0, 0, 0)
        
        # Spacer for right alignment (20% of width)
        msg_layout.addStretch(1)
        
        # Message box (80% of width)
        msg_label = QLabel(text)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        msg_label.setStyleSheet("""
            QLabel {
                background-color: #0e639c;
                color: white;
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
            }
        """)
        
        msg_layout.addWidget(msg_label, 4)  # 4 parts out of 5 (80%)
        
        self.chat_layout.addWidget(msg_widget)
        self.scroll_to_bottom()
    
    def start_ai_response(self):
        """Start a new AI response section (full width, plain text)."""
        self.current_ai_widget = QLabel()
        self.current_ai_widget.setWordWrap(True)
        self.current_ai_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.current_ai_widget.setTextFormat(Qt.TextFormat.RichText)
        self.current_ai_widget.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #d4d4d4;
                border: none;
                padding: 5px;
                font-size: 13px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """)
        
        self.chat_layout.addWidget(self.current_ai_widget)
        self.scroll_to_bottom()
        return self.current_ai_widget
    
    def append_to_ai_response(self, text, color=None):
        """Append text to the current AI response."""
        if self.current_ai_widget is None:
            self.start_ai_response()
        
        # Convert text to string if it's not already
        if not isinstance(text, str):
            text = str(text)
        
        current_text = self.current_ai_widget.text()
        
        if color:
            color_map = {
                '33': '#ffcc00',  # Yellow (thinking)
                '36': '#00bfff',  # Cyan (assistant)
                '35': '#ff00ff',  # Magenta (function call)
                '34': '#1e90ff',  # Blue (usage/images)
                '32': '#00ff00',  # Green (done)
                '31': '#ff0000',  # Red (error)
            }
            html_color = color_map.get(color, '#d4d4d4')
            # Escape HTML characters in text and convert newlines to <br>
            from html import escape
            escaped_text = escape(text).replace('\n', '<br>')
            self.current_ai_widget.setText(current_text + f'<span style="color: {html_color};">{escaped_text}</span>')
        else:
            from html import escape
            escaped_text = escape(text).replace('\n', '<br>')
            self.current_ai_widget.setText(current_text + escaped_text)
        
        self.scroll_to_bottom()
    
    def finish_ai_response(self):
        """Finish the current AI response."""
        self.current_ai_widget = None
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """Scroll to the bottom of the chat."""
        # Use QTimer to ensure scroll happens after layout updates
        QTimer.singleShot(10, self._do_scroll)
    
    def _do_scroll(self):
        """Actually perform the scroll."""
        scroll = self.findChild(QScrollArea)
        if scroll:
            scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    
    def send_message(self):
        """Send message from input field."""
        text = self.input_field.text().strip()
        if text and self.parent_widget:
            self.input_field.clear()
            self.parent_widget.send_to_agent(text)
    
    def clear_chat(self):
        """Clear all chat messages."""
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.current_ai_widget = None
        self.chat_history = []
    
    def closeEvent(self, event):
        """Override close to just hide the window."""
        self.hide()
        event.ignore()


class Gadget(QWidget):
    # Signals for thread-safe UI updates
    history_loaded = pyqtSignal(list)
    agent_event_received = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()

        # Recording state
        self.is_recording = False
        self.frames = []
        self.samplerate = 44100
        self.channels = 1
        self.filename = "recording.wav"
        # Language selection (ISO-639-1); default 'en'
        self.selected_language = "en"
        
        # Chat window
        self.chat_window = None
        self.agent_url = os.environ.get("AGENT_URL", "http://127.0.0.1:6002")
        
        # Connect signals to slots for thread-safe UI updates
        self.history_loaded.connect(self.display_chat_history)
        self.agent_event_received.connect(self.handle_agent_event)

        # Transparent, always-on-top window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        row = QHBoxLayout()

        # Buttons
        self.play_btn = QPushButton("▶ Start Recording")
        self.stop_btn = QPushButton("⏹ Stop Recording")
        self.chat_btn = QPushButton("💬")
        self.menu_btn = QPushButton("⚙")

        button_style = (
            """
            QPushButton {
                background-color: rgba(50, 50, 50, 180);
                color: white;
                border-radius: 12px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 200);
            }
            """
        )
        small_button_style = (
            """
            QPushButton {
                background-color: rgba(50, 50, 50, 180);
                color: white;
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 24px;
                max-width: 28px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 200);
            }
            """
        )
        self.play_btn.setStyleSheet(button_style)
        self.stop_btn.setStyleSheet(button_style)
        self.chat_btn.setStyleSheet(small_button_style)
        self.menu_btn.setStyleSheet(small_button_style)

        # Row contents
        row.addWidget(self.play_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.chat_btn)
        row.addWidget(self.menu_btn)
        layout.addLayout(row)

        # Initially only Play visible
        self.stop_btn.hide()

        # Button actions
        self.play_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.chat_btn.clicked.connect(self.toggle_chat_window)
        self.menu_btn.clicked.connect(self.show_menu)

        # Dragging state
        self.drag_position = None  # used by top-level mouse* overrides
        self._drag_offset = None  # used by eventFilter for child widgets
        self._dragging = False
        self._press_global_pos = None

        # Allow dragging when starting on buttons too
        self.play_btn.installEventFilter(self)
        self.stop_btn.installEventFilter(self)
        self.chat_btn.installEventFilter(self)
        self.menu_btn.installEventFilter(self)

        # Default position (bottom right)
        screen = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(
            screen.width() - self.width() - 20,
            screen.height() - self.height() - 40,
        )

    # --- Dragging events ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None

    # Let dragging start from child widgets (e.g., buttons) without breaking clicks
    def eventFilter(self, obj, event):
        # Only care about mouse events on our child widgets
        if obj in (self.menu_btn, self.play_btn, self.stop_btn, self.chat_btn):
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self._press_global_pos = event.globalPosition().toPoint()
                self._drag_offset = (
                    self._press_global_pos - self.frameGeometry().topLeft()
                )
                self._dragging = False
                # Don't consume; allow normal press behavior
                return False

            if (
                event.type() == QEvent.Type.MouseMove
                and (event.buttons() & Qt.MouseButton.LeftButton)
            ):
                if self._press_global_pos is not None:
                    current = event.globalPosition().toPoint()
                    # Use Qt's standard threshold to decide between click and drag
                    if not self._dragging:
                        if (
                            current - self._press_global_pos
                        ).manhattanLength() >= QApplication.startDragDistance():
                            self._dragging = True
                    if self._dragging and self._drag_offset is not None:
                        self.move(current - self._drag_offset)
                        # Consume move while dragging so the button doesn't also handle it
                        return True
                return False

            if (
                event.type() == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
            ):
                # If a drag occurred, eat the release so button click won't fire
                was_dragging = self._dragging
                self._press_global_pos = None
                self._drag_offset = None
                self._dragging = False
                return True if was_dragging else False

        return super().eventFilter(obj, event)

    def show_menu(self):
        menu = QMenu(self)

        # Language block
        langs = [
            ("en", "English"),
            ("ro", "Romanian"),
            ("ru", "Russian"),
            ("de", "German"),
            ("fr", "French"),
            ("es", "Spanish"),
        ]

        lang_menu = QMenu("Language", self)
        self._lang_actions = {}
        for code, label in langs:
            act = QAction(f"{label} ({code})", self)
            act.setCheckable(True)
            act.setChecked(code == self.selected_language)
            act.triggered.connect(lambda checked, c=code: self._set_language(c))
            lang_menu.addAction(act)
            self._lang_actions[code] = act
        menu.addMenu(lang_menu)

        menu.addSeparator()
        close_action = QAction("Close", self)
        close_action.triggered.connect(self.quit_app)
        menu.addAction(close_action)

        # Show menu below the menu button
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def _set_language(self, code: str):
        allowed = {"en", "ro", "ru", "de", "fr", "es"}
        if code not in allowed:
            code = "en"
        self.selected_language = code
        # Update checks if actions exist
        if hasattr(self, "_lang_actions"):
            for c, act in self._lang_actions.items():
                act.setChecked(c == code)

    def toggle_chat_window(self):
        """Open or close the chat window."""
        if self.chat_window is None:
            self.chat_window = ChatWindow(self)
        
        if self.chat_window.isVisible():
            self.chat_window.hide()
        else:
            self.chat_window.show()
            self.chat_window.raise_()
            self.chat_window.activateWindow()
            # Fetch chat history when opening
            self.fetch_and_display_chat_history()
    
    def fetch_and_display_chat_history(self):
        """Fetch chat history from agent service and display it."""
        def _fetch():
            try:
                response = requests.get(f"{self.agent_url}/chat/history", timeout=5)
                if response.status_code == 200:
                    history = response.json().get("history", [])
                    # Emit signal to display on main thread
                    self.history_loaded.emit(history)
            except Exception as e:
                print(f"Failed to fetch chat history: {e}")
        
        threading.Thread(target=_fetch, daemon=True).start()
    
    @pyqtSlot(list)
    def display_chat_history(self, history):
        """Display chat history in the chat window."""
        if not self.chat_window:
            return
        
        self.chat_window.clear_chat()
        
        for entry in history:
            role = entry.get("role", "")
            content = entry.get("content", [])
            
            if role == "user":
                # Display user message
                for item in content:
                    if item.get("type") == "input_text":
                        text = item.get("text", "")
                        # Extract actual user input (remove timestamp prefix if present)
                        if "User's input:" in text:
                            text = text.split("User's input:", 1)[1].strip()
                        self.chat_window.add_user_message(text)
            
            elif role == "assistant":
                # Display assistant response - use the SAME approach as streaming
                for item in content:
                    if item.get("type") == "output_text":
                        text = item.get("text", "")
                        # Create fresh widget for each text block (like streaming does)
                        self.chat_window.start_ai_response()
                        # Append the text exactly as streaming does
                        self.chat_window.append_to_ai_response("Assistant: ", '36')
                        self.chat_window.append_to_ai_response(text)
                        self.chat_window.finish_ai_response()
            
            elif entry.get("type") == "reasoning":
                # Display reasoning only if it has actual content
                summary = entry.get("summary", "")
                if summary:  # Only display if summary exists and is not empty
                    # Handle summary as string or list
                    if isinstance(summary, list):
                        summary_text = " ".join(str(s) for s in summary)
                    else:
                        summary_text = str(summary.get("text", summary))
                    
                    # Only display if there's actual text after conversion
                    if summary_text.strip():
                        # Create widget same as streaming
                        self.chat_window.start_ai_response()
                        self.chat_window.append_to_ai_response("Thinking: ", '33')
                        self.chat_window.append_to_ai_response(summary_text)
                        self.chat_window.finish_ai_response()
            
            elif entry.get("type") == "function_call":
                # Display function call same as streaming
                func_name = entry.get("name", "")
                func_args = entry.get("arguments", "")
                self.chat_window.start_ai_response()
                self.chat_window.append_to_ai_response(
                    f"[Function Call] {func_name}\n",
                    '35'
                )
                if func_args:
                    self.chat_window.append_to_ai_response(f"Arguments: {func_args}\n")
                self.chat_window.finish_ai_response()
        
        # Force layout update after loading all history
        if self.chat_window:
            # Use delay for scrolling to ensure all layouts complete
            QTimer.singleShot(100, self.chat_window.scroll_to_bottom)
    
    def _adjust_all_widget_heights(self):
        """Adjust heights of all AI response widgets in chat."""
        if not self.chat_window:
            return
        
        # Force all QTextEdit widgets to recalculate their heights
        for i in range(self.chat_window.chat_layout.count()):
            widget = self.chat_window.chat_layout.itemAt(i).widget()
            if isinstance(widget, QTextEdit):
                self.chat_window.adjust_widget_height(widget)
        
        # Force container update
        self.chat_window.chat_container.updateGeometry()
        self.chat_window.update()
    
    def send_to_agent(self, text):
        """Send text to the agent service and handle streaming response."""
        if not self.chat_window:
            return
        
        # Add user message to chat
        self.chat_window.add_user_message(text)
        
        # Start AI response
        self.chat_window.start_ai_response()
        
        def _stream():
            try:
                response = requests.post(
                    f"{self.agent_url}/chat/stream",
                    json={"message": text},
                    stream=True,
                    timeout=300
                )
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                event = json.loads(data_str)
                                # Emit signal instead of calling directly
                                self.agent_event_received.emit(event)
                            except json.JSONDecodeError as je:
                                print(f"JSON decode error: {je}")
                            except Exception as ee:
                                print(f"Error processing event: {ee}")
            except Exception as e:
                print(f"Error streaming from agent: {e}")
                # Use signal for error display too
                self.agent_event_received.emit({
                    "type": "error",
                    "message": f"Failed to communicate with agent: {e}"
                })
            finally:
                # Use signal for finish
                self.agent_event_received.emit({"type": "stream.finished"})
        
        threading.Thread(target=_stream, daemon=True).start()
    
    @pyqtSlot(dict)
    def handle_agent_event(self, event):
        """Handle streaming events from the agent (thread-safe via signal)."""
        if not self.chat_window:
            return
        
        try:
            event_type = event.get("type", "")
            
            if event_type == "response.reasoning_summary_part.added":
                self.chat_window.append_to_ai_response("Thinking: ", '33')
            
            elif event_type == "response.reasoning_summary_text.delta":
                delta = event.get("delta", "")
                self.chat_window.append_to_ai_response(delta)
            
            elif event_type == "response.reasoning_summary_text.done":
                self.chat_window.append_to_ai_response("\n")
            
            elif event_type == "response.content_part.added":
                self.chat_window.append_to_ai_response("Assistant: ", '36')
            
            elif event_type == "response.output_text.delta":
                delta = event.get("delta", "")
                self.chat_window.append_to_ai_response(delta)
            
            elif event_type == "response.output_text.done":
                self.chat_window.append_to_ai_response("\n")
            
            elif event_type == "response.output_item.done":
                item = event.get("item", {})
                # Ensure item is a dictionary
                if isinstance(item, dict):
                    item_type = item.get("type", "")
                    if item_type == "function_call":
                        func_name = item.get("name", "")
                        func_args = item.get("arguments", "")
                        # Create a new response widget for function call
                        self.chat_window.finish_ai_response()
                        self.chat_window.start_ai_response()
                        self.chat_window.append_to_ai_response(
                            f"[Function Call] {func_name}\n",
                            '35'
                        )
                        if func_args:
                            self.chat_window.append_to_ai_response(f"Arguments: {func_args}\n")
                        self.chat_window.finish_ai_response()
                        # Start a new widget for the next response
                        self.chat_window.start_ai_response()
            
            elif event_type == "response.image_generation_call.generating":
                self.chat_window.append_to_ai_response("\n[Image Generation]...\n", '34')
            
            elif event_type == "response.image_generation_call.completed":
                self.chat_window.append_to_ai_response("[Image Generation] Completed\n", '34')
            
            elif event_type == "response.completed":
                # Skip displaying usage info - not needed in chat UI
                pass
            
            elif event_type == "response.agent.done":
                # Skip displaying agent done message - not needed in chat UI
                pass
            
            elif event_type == "stream.finished":
                # Custom event to finish AI response
                self.chat_window.finish_ai_response()
            
            elif event_type == "error":
                # Custom error event
                error_msg = event.get("message", "Unknown error")
                self.chat_window.append_to_ai_response(f"\n[Error] {error_msg}\n", '31')
                self.chat_window.finish_ai_response()
        
        except Exception as e:
            print(f"Error in handle_agent_event: {e}")
            import traceback
            traceback.print_exc()

    def quit_app(self):
        # Ensure audio stream stops before quitting
        try:
            if hasattr(self, "stream") and getattr(self, "stream") is not None:
                try:
                    self.stream.stop()
                except Exception:
                    pass
        finally:
            # Close chat window
            if self.chat_window:
                self.chat_window.close()
            app = QApplication.instance()
            if app is not None:
                app.quit()

    def closeEvent(self, event):
        # Cleanup audio stream on window close via window controls
        try:
            if hasattr(self, "stream") and getattr(self, "stream") is not None:
                try:
                    self.stream.stop()
                except Exception:
                    pass
        finally:
            # Close chat window
            if self.chat_window:
                self.chat_window.close()
            event.accept()

    # --- Recording logic ---
    def start_recording(self):
        self.is_recording = True
        self.frames = []  # store raw bytes for exact PCM output

        def callback(indata, frames, time, status):
            if self.is_recording:
                # indata will be int16; store raw bytes
                self.frames.append(indata.copy().tobytes())

        # Ensure any previous stream is stopped/closed
        if hasattr(self, "stream") and getattr(self, "stream") is not None:
            try:
                self.stream.stop()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        # Use 16-bit PCM directly to match WAV settings and avoid conversion artifacts
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="int16",
            blocksize=512,
            latency="low",
            callback=callback,
        )
        self.stream.start()

        self.play_btn.hide()
        self.stop_btn.show()

    def stop_recording(self):
        self.is_recording = False
        t0 = time.perf_counter()
        if hasattr(self, "stream") and getattr(self, "stream") is not None:
            try:
                # Abort immediately to avoid waiting for buffer drain
                self.stream.abort()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        t1 = time.perf_counter()

        # Build WAV in-memory and send to the transcribe microservice in background
        def _send():
            try:
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2)  # 16-bit PCM
                    wf.setframerate(self.samplerate)
                    wf.writeframes(b"".join(self.frames))
                buf.seek(0)
                t2 = time.perf_counter()

                url = os.environ.get("TRANSCRIBE_URL", "http://127.0.0.1:6001/upload")
                files = {"file": (self.filename, buf, "audio/wav")}
                data = {"language": self.selected_language}
                r = requests.post(url, data=data, files=files)
                try:
                    data = r.json()
                except Exception:
                    data = {"raw": r.text}
                t3 = time.perf_counter()
                server_ms = data.get("metrics", {}).get("total_ms") if isinstance(data, dict) else None
                print(
                    "Transcribe response:", data,
                    " timings(s): abort+close=", round(t1 - t0, 3),
                    " build_wav=", round(t2 - t1, 3),
                    " post+resp=", round(t3 - t2, 3),
                    " server_ms=", server_ms,
                )
                
                # If transcription successful and chat window is visible, send to agent
                if isinstance(data, dict) and "text" in data:
                    transcribed_text = data["text"]
                    if transcribed_text and self.chat_window and self.chat_window.isVisible():
                        self.send_to_agent(transcribed_text)
                
            except Exception as e:
                print("Upload failed:", e)

        threading.Thread(target=_send, daemon=True).start()

        self.stop_btn.hide()
        self.play_btn.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gadget = Gadget()
    gadget.show()
    sys.exit(app.exec())
