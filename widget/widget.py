
# Put all three controls in the same row
import sys
import os
import sounddevice as sd
import wave
import requests
import io
import time
import threading
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QPoint, QEvent


class Gadget(QWidget):
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
        self.menu_btn.setStyleSheet(small_button_style)

        # Row contents
        row.addWidget(self.play_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.menu_btn)
        layout.addLayout(row)

        # Initially only Play visible
        self.stop_btn.hide()

        # Button actions
        self.play_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        self.menu_btn.clicked.connect(self.show_menu)

        # Dragging state
        self.drag_position = None  # used by top-level mouse* overrides
        self._drag_offset = None  # used by eventFilter for child widgets
        self._dragging = False
        self._press_global_pos = None

        # Allow dragging when starting on buttons too
        self.play_btn.installEventFilter(self)
        self.stop_btn.installEventFilter(self)
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
        if obj in (self.menu_btn, self.play_btn, self.stop_btn):
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

    def quit_app(self):
        # Ensure audio stream stops before quitting
        try:
            if hasattr(self, "stream") and getattr(self, "stream") is not None:
                try:
                    self.stream.stop()
                except Exception:
                    pass
        finally:
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
