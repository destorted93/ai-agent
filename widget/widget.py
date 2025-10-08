
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
import asyncio
import websockets
import traceback
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                              QHBoxLayout, QMenu, QTextEdit, QLineEdit, QScrollArea,
                              QLabel, QFrame, QSizePolicy, QLayout)
from PyQt6.QtGui import QAction, QTextCursor, QFont, QTextOption, QKeyEvent, QPainter, QColor, QPen, QPixmap
from PyQt6.QtCore import Qt, QPoint, QEvent, pyqtSignal, QObject, QThread, pyqtSlot, QTimer, QRect, QSize


class ScreenshotSelector(QWidget):
    """Overlay widget for selecting a screen area."""
    screenshot_selected = pyqtSignal(QPixmap)
    screenshot_cancelled = pyqtSignal()
    
    def __init__(self, screenshot):
        super().__init__()
        self.screenshot = screenshot
        self.start_pos = None
        self.end_pos = None
        self.selecting = False
        
        # Set up fullscreen transparent overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
    def paintEvent(self, event):
        """Draw the screenshot with selection overlay."""
        painter = QPainter(self)
        
        # Draw the screenshot
        painter.drawPixmap(0, 0, self.screenshot)
        
        # Draw semi-transparent overlay
        overlay_color = QColor(0, 0, 0, 100)
        painter.fillRect(self.rect(), overlay_color)
        
        # If selecting, draw the selection rectangle
        if self.start_pos and self.end_pos:
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # Clear the selection area (show original screenshot)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection_rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.drawPixmap(selection_rect, self.screenshot, selection_rect)
            
            # Draw selection border
            pen = QPen(QColor(0, 150, 255), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(selection_rect)
            
            # Draw dimensions text
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                selection_rect.x(),
                selection_rect.y() - 5,
                f"{selection_rect.width()}x{selection_rect.height()}"
            )
    
    def mousePressEvent(self, event):
        """Start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.selecting = True
            self.update()
    
    def mouseMoveEvent(self, event):
        """Update selection."""
        if self.selecting:
            self.end_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Finish selection."""
        if event.button() == Qt.MouseButton.LeftButton and self.selecting:
            self.selecting = False
            self.end_pos = event.pos()
            
            # Get the selected area
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # Must have some minimum size
            if selection_rect.width() > 10 and selection_rect.height() > 10:
                selected_pixmap = self.screenshot.copy(selection_rect)
                self.screenshot_selected.emit(selected_pixmap)
                self.close()
            else:
                # Too small, cancel
                self.screenshot_cancelled.emit()
                self.close()
    
    def keyPressEvent(self, event):
        """Cancel selection on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.screenshot_cancelled.emit()
            self.close()


class MultilineInput(QTextEdit):
    """Custom QTextEdit that sends message on Enter and adds newline on Shift+Enter."""
    send_message = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        self.setPlaceholderText("Type your message or drag & drop files...")
        
        # Enable word wrap
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Set fixed comfortable height matching original QLineEdit (with padding from stylesheet)
        self.base_height = 40  # Standard single-line input height
        self.max_lines = 10
        
        font_metrics = self.fontMetrics()
        self.line_height = font_metrics.lineSpacing()
        self.max_height = self.base_height + (self.line_height * (self.max_lines - 1))
        
        self.setFixedHeight(self.base_height)
        
        # Connect to textChanged to adjust height dynamically
        self.textChanged.connect(self.adjust_height)
        
    def adjust_height(self):
        """Adjust height based on content, up to max_lines."""
        # Get document height and calculate needed height
        doc_height = int(self.document().size().height())
        
        # Add padding (16px total - 8px top + 8px bottom from stylesheet)
        new_height = doc_height + 16
        
        # Constrain between base and max height
        new_height = max(self.base_height, min(new_height, self.max_height))
        
        if new_height != self.height():
            self.setFixedHeight(new_height)
        
    def keyPressEvent(self, event: QKeyEvent):
        """Handle Enter and Shift+Enter differently."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter: insert newline
                super().keyPressEvent(event)
            else:
                # Plain Enter: send message
                self.send_message.emit()
                event.accept()
        else:
            super().keyPressEvent(event)
    
    def clear_text(self):
        """Clear the text content."""
        self.clear()
        # Reset to base height
        self.setFixedHeight(self.base_height)


class FlowLayout(QLayout):
    """Custom layout that wraps items to multiple lines like a flow layout."""
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.item_list.append(item)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins()
        size += QSize(margin.left() + margin.right(), margin.top() + margin.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self.item_list:
            widget = item.widget()
            space_x = spacing
            space_y = spacing
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class ChatWindow(QWidget):
    """Separate chat window that maintains its state."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("AI Chat")
        self.resize(600, 700)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        self.dropped_files = []
        
        # Screenshot state - now supports multiple screenshots (max 5)
        self.screenshots = []  # List of {"data": base64, "pixmap": QPixmap}
        self.max_screenshots = 5
        
        # Sending state tracking
        self.is_sending = False
        self.send_animation_timer = QTimer()
        self.send_animation_timer.timeout.connect(self.animate_sending)
        self.send_animation_step = 0
        
        # Chat display area
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top toolbar with clear button
        toolbar = QWidget()
        toolbar.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3d3d3d;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.addStretch()
        
        self.screenshot_button = QPushButton("📸")
        self.screenshot_button.setToolTip("Capture Screenshot")
        self.screenshot_button.setFixedSize(32, 32)
        self.screenshot_button.clicked.connect(self.capture_screenshot)
        self.screenshot_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888 !important;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #4da6ff !important;
            }
        """)
        
        toolbar_layout.addWidget(self.screenshot_button)
        
        self.clear_button = QPushButton("🗑️")
        self.clear_button.setToolTip("Clear Chat History")
        self.clear_button.setFixedSize(32, 32)
        self.clear_button.clicked.connect(self.request_clear_chat)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888 !important;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                color: #ff6b6b !important;
            }
        """)
        
        toolbar_layout.addWidget(self.clear_button)
        layout.addWidget(toolbar)
        
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
        
        # Attached files area (hidden by default)
        self.attached_files_widget = QWidget()
        self.attached_files_widget.hide()
        attached_files_main_layout = QHBoxLayout(self.attached_files_widget)
        attached_files_main_layout.setContentsMargins(5, 5, 5, 5)
        attached_files_main_layout.setSpacing(5)
        
        # Container for file chips - uses flow layout
        self.files_container = QWidget()
        self.files_container.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        # Use FlowLayout for wrapping
        self.files_layout = FlowLayout(self.files_container, margin=5, spacing=5)
        
        attached_files_main_layout.addWidget(self.files_container, 1)
        
        # Clear all button
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.setFixedHeight(24)
        self.clear_all_btn.setToolTip("Clear all attached files")
        self.clear_all_btn.clicked.connect(self.clear_attached_files)
        self.clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ff6b6b !important;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
                color: white !important;
            }
        """)
        
        attached_files_main_layout.addWidget(self.clear_all_btn)
        layout.addWidget(self.attached_files_widget)
        
        # Screenshots preview area (hidden by default)
        self.screenshots_widget = QWidget()
        self.screenshots_widget.hide()
        screenshots_main_layout = QHBoxLayout(self.screenshots_widget)
        screenshots_main_layout.setContentsMargins(5, 5, 5, 5)
        screenshots_main_layout.setSpacing(5)
        
        # Container for screenshot thumbnails - uses flow layout
        self.screenshots_container = QWidget()
        self.screenshots_container.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        # Use FlowLayout for wrapping
        self.screenshots_layout = FlowLayout(self.screenshots_container, margin=5, spacing=5)
        
        screenshots_main_layout.addWidget(self.screenshots_container, 1)
        
        # Clear all screenshots button
        self.clear_screenshots_btn = QPushButton("Clear All")
        self.clear_screenshots_btn.setFixedHeight(24)
        self.clear_screenshots_btn.setToolTip("Clear all screenshots")
        self.clear_screenshots_btn.clicked.connect(self.clear_all_screenshots)
        self.clear_screenshots_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: #ff6b6b !important;
                border: none;
                border-radius: 3px;
                font-size: 10px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
                color: white !important;
            }
        """)
        
        screenshots_main_layout.addWidget(self.clear_screenshots_btn)
        layout.addWidget(self.screenshots_widget)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_field = MultilineInput()
        self.input_field.send_message.connect(self.send_message)
        
        self.send_button = QPushButton("➤")
        self.send_button.setFixedSize(40, 40)
        self.send_button.clicked.connect(self.handle_send_button_click)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:disabled {
                background-color: #444444;
                color: #888888;
            }
        """)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignBottom)
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
            QTextEdit {
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
    
    def handle_send_button_click(self):
        """Handle send button click - either send message or stop inference."""
        if self.is_sending:
            self.stop_inference()
        else:
            self.send_message()
    
    def send_message(self):
        """Send message from input field."""
        text = self.input_field.toPlainText().strip()
        
        # Build message with file context if files are attached
        if self.dropped_files:
            file_context = "\n\n**Attached files/folders:**\n"
            for path in self.dropped_files:
                file_context += f"- `{path}`\n"
            text = text + file_context if text else file_context.strip()
        
        # Require either text or screenshots
        if (text or self.screenshots) and self.parent_widget:
            self.input_field.clear_text()
            self.clear_attached_files()
            self.start_sending_state()
            # Pass text and list of screenshot data
            screenshot_data_list = [s["data"] for s in self.screenshots]
            self.parent_widget.send_to_agent(text, screenshot_data_list)
            # Clear screenshots after sending
            self.clear_all_screenshots()
            # Scroll with longer delay to ensure user message is fully rendered
            QTimer.singleShot(100, self._do_scroll)
    
    def start_sending_state(self):
        """Start the sending animation state."""
        self.is_sending = True
        self.send_animation_step = 0
        self.send_button.setText("⠋")  # Clean spinner
        self.send_animation_timer.start(100)  # Update every 100ms (same as recording)
        self.input_field.setEnabled(False)
    
    def stop_sending_state(self):
        """Stop the sending animation and return to normal state."""
        self.is_sending = False
        self.send_animation_timer.stop()
        self.send_button.setText("➤")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:disabled {
                background-color: #444444;
                color: #888888;
            }
        """)
        self.input_field.setEnabled(True)
    
    def animate_sending(self):
        """Clean rotating spinner animation - same as recording."""
        self.send_animation_step = (self.send_animation_step + 1) % 8
        
        # Standard Unicode spinner
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]
        
        self.send_button.setText(spinner_chars[self.send_animation_step])
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #c83232;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #d84444;
            }
        """)
    
    def stop_inference(self):
        """Stop the AI inference (placeholder for future implementation)."""
        # TODO: Implement actual inference cancellation
        # This should send a cancellation request to the agent service
        print("Stop inference requested - not yet implemented")
        self.stop_sending_state()
    
    def request_clear_chat(self):
        """Request parent to clear chat (both locally and on server) with confirmation."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            'Clear Chat History',
            'Are you sure you want to clear all chat history?\n\nThis action cannot be undone.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes and self.parent_widget:
            self.parent_widget.clear_chat_all()
    
    def clear_chat(self):
        """Clear all chat messages from UI."""
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.current_ai_widget = None
        self.chat_history = []
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """Handle drop event - extract file/folder paths."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path not in self.dropped_files:
                        self.dropped_files.append(path)
            
            self.update_attached_files_display()
            event.acceptProposedAction()
    
    def update_attached_files_display(self):
        """Update the display of attached files with individual remove buttons."""
        # Clear existing file widgets
        while self.files_layout.count():
            item = self.files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self.dropped_files:
            # Create a tag for each file
            for path in self.dropped_files:
                file_widget = QWidget()
                file_layout = QHBoxLayout(file_widget)
                file_layout.setContentsMargins(8, 2, 4, 2)
                file_layout.setSpacing(4)
                
                # Icon and filename
                if os.path.isdir(path):
                    icon_text = "📁"
                    name = os.path.basename(path) + "/"
                else:
                    icon_text = "�"
                    name = os.path.basename(path)
                
                file_label = QLabel(f"{icon_text} {name}")
                file_label.setStyleSheet("""
                    QLabel {
                        color: #d4d4d4;
                        font-size: 11px;
                        background-color: transparent;
                    }
                """)
                file_label.setToolTip(path)
                
                # Remove button for this specific file - small and close
                remove_btn = QPushButton("✖")
                remove_btn.setFixedSize(14, 14)
                remove_btn.setToolTip(f"Remove {name}")
                remove_btn.clicked.connect(lambda checked, p=path: self.remove_file(p))
                remove_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #888888 !important;
                        border: none;
                        font-size: 9px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        color: #ff6b6b !important;
                    }
                """)
                
                file_layout.addWidget(file_label)
                file_layout.addWidget(remove_btn)
                
                # Set fixed size policy to prevent stretching
                file_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                file_widget.adjustSize()
                
                # Style the file widget as a compact chip
                file_widget.setStyleSheet("""
                    QWidget {
                        background-color: #3d3d3d;
                        border-radius: 10px;
                    }
                    QWidget:hover {
                        background-color: #4d4d4d;
                    }
                """)
                
                # Add to flow layout
                self.files_layout.addWidget(file_widget)
            
            self.attached_files_widget.show()
        else:
            self.attached_files_widget.hide()
    
    def remove_file(self, file_path):
        """Remove a specific file from attached files."""
        if file_path in self.dropped_files:
            self.dropped_files.remove(file_path)
            self.update_attached_files_display()
    
    def clear_attached_files(self):
        """Clear all attached files."""
        self.dropped_files.clear()
        self.update_attached_files_display()
    
    def capture_screenshot(self):
        """Capture a screenshot of the entire screen - user can crop later."""
        # Check if max screenshots reached
        if len(self.screenshots) >= self.max_screenshots:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Maximum Screenshots",
                f"You can attach a maximum of {self.max_screenshots} screenshots per message."
            )
            return
        
        try:
            import base64
            from io import BytesIO
            
            # Hide the chat window temporarily
            self.hide()
            QTimer.singleShot(300, self._perform_screenshot)
            
        except Exception as e:
            print(f"Screenshot error: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Screenshot Error",
                f"Failed to capture screenshot: {str(e)}"
            )
    
    def _perform_screenshot(self):
        """Actually perform the screenshot after window is hidden."""
        try:
            # Capture the entire screen using Qt
            screen = QApplication.primaryScreen()
            full_screenshot = screen.grabWindow(0)
            
            # Show selection overlay
            from PyQt6.QtCore import QRect
            self.selection_overlay = ScreenshotSelector(full_screenshot)
            self.selection_overlay.screenshot_selected.connect(self._handle_screenshot_selection)
            self.selection_overlay.screenshot_cancelled.connect(self._handle_screenshot_cancelled)
            self.selection_overlay.showFullScreen()
                
        except Exception as e:
            self.show()
            print(f"Screenshot error: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Screenshot Error",
                f"Failed to capture screenshot: {str(e)}"
            )
    
    def _handle_screenshot_selection(self, selected_pixmap):
        """Handle the selected screenshot area."""
        try:
            import base64
            from PyQt6.QtCore import QBuffer, QIODevice
            
            # Show window again
            self.show()
            self.raise_()
            self.activateWindow()
            
            if selected_pixmap:
                # Convert QPixmap to base64 using QBuffer
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                selected_pixmap.save(buffer, "PNG")
                buffer.close()
                
                screenshot_data = base64.b64encode(buffer.data()).decode('utf-8')
                
                # Add to screenshots list
                self.screenshots.append({
                    "data": screenshot_data,
                    "pixmap": selected_pixmap
                })
                
                # Update display
                self.update_screenshots_display()
                
        except Exception as e:
            print(f"Screenshot processing error: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_screenshot_cancelled(self):
        """Handle screenshot cancellation."""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def update_screenshots_display(self):
        """Update the display of screenshot thumbnails."""
        # Clear existing thumbnails
        while self.screenshots_layout.count():
            item = self.screenshots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self.screenshots:
            # Create thumbnail for each screenshot
            for idx, screenshot in enumerate(self.screenshots):
                thumb_widget = QWidget()
                thumb_layout = QVBoxLayout(thumb_widget)
                thumb_layout.setContentsMargins(2, 2, 2, 2)
                thumb_layout.setSpacing(2)
                
                # Thumbnail image (clickable)
                thumb_label = QLabel()
                thumb_pixmap = screenshot["pixmap"].scaled(
                    80, 60,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                thumb_label.setPixmap(thumb_pixmap)
                thumb_label.setStyleSheet("""
                    QLabel {
                        background-color: #2d2d2d;
                        border: 2px solid #4da6ff;
                        border-radius: 3px;
                        padding: 2px;
                    }
                    QLabel:hover {
                        border: 2px solid #66b3ff;
                    }
                """)
                thumb_label.setCursor(Qt.CursorShape.PointingHandCursor)
                thumb_label.mousePressEvent = lambda event, p=screenshot["pixmap"]: self.show_screenshot_fullsize(p)
                
                # Remove button
                remove_btn = QPushButton("✖")
                remove_btn.setFixedSize(16, 16)
                remove_btn.setToolTip(f"Remove screenshot {idx + 1}")
                remove_btn.clicked.connect(lambda checked, i=idx: self.remove_screenshot(i))
                remove_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff6b6b;
                        color: white !important;
                        border: none;
                        border-radius: 8px;
                        font-size: 10px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #ff5555;
                    }
                """)
                
                thumb_layout.addWidget(thumb_label, alignment=Qt.AlignmentFlag.AlignCenter)
                thumb_layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignCenter)
                
                thumb_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                thumb_widget.adjustSize()
                
                self.screenshots_layout.addWidget(thumb_widget)
            
            self.screenshots_widget.show()
        else:
            self.screenshots_widget.hide()
    
    def show_screenshot_fullsize(self, pixmap):
        """Show screenshot in a separate window at full size."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QScrollArea
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Screenshot Preview")
        dialog.setModal(False)
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        label = QLabel()
        label.setPixmap(pixmap)
        label.setScaledContents(False)
        
        scroll.setWidget(label)
        layout.addWidget(scroll)
        
        dialog.show()
    
    def remove_screenshot(self, index):
        """Remove a specific screenshot."""
        if 0 <= index < len(self.screenshots):
            self.screenshots.pop(index)
            self.update_screenshots_display()
    
    def clear_all_screenshots(self):
        """Clear all screenshots."""
        self.screenshots.clear()
        self.update_screenshots_display()
    
    def closeEvent(self, event):
        """Override close to just hide the window."""
        self.hide()
        event.ignore()


class Gadget(QWidget):
    # Signals for thread-safe UI updates
    history_loaded = pyqtSignal(list)
    agent_event_received = pyqtSignal(dict)
    transcription_received = pyqtSignal(str)
    
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
        
        # Long press state
        self.press_start_time = None
        self.long_press_threshold = 1000  # 1 second in milliseconds
        self.long_press_timer = QTimer()
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.timeout.connect(self.on_long_press)
        self.ready_to_record = False  # Indicates button held long enough, waiting for release
        
        # Animation state
        self.recording_animation_timer = QTimer()
        self.recording_animation_timer.timeout.connect(self.animate_recording)
        self.animation_step = 0
        
        # Chat window
        self.chat_window = None
        self.agent_url = os.environ.get("AGENT_URL", "http://127.0.0.1:6002")
        
        # Connect signals to slots for thread-safe UI updates
        self.history_loaded.connect(self.display_chat_history)
        self.agent_event_received.connect(self.handle_agent_event)
        self.transcription_received.connect(self.send_to_agent)

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

        # Single unified button
        self.main_btn = QPushButton("🤖")
        self.main_btn.setFixedSize(56, 56)
        
        button_style = """
            QPushButton {
                background-color: rgba(50, 50, 50, 200);
                color: white;
                border-radius: 28px;
                font-size: 28px;
                border: 2px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background-color: rgba(70, 70, 70, 220);
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
        """
        self.main_btn.setStyleSheet(button_style)
        
        # Install event filter for custom mouse handling
        self.main_btn.installEventFilter(self)
        
        layout.addWidget(self.main_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Dragging state
        self.drag_position = None
        self._drag_offset = None
        self._dragging = False
        self._press_global_pos = None

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

    def eventFilter(self, obj, event):
        # Handle main button events
        if obj == self.main_btn:
            # Left button press - start timer for long press
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._press_global_pos = event.globalPosition().toPoint()
                self._drag_offset = self._press_global_pos - self.frameGeometry().topLeft()
                self._dragging = False
                self.press_start_time = time.time()
                
                # Start long press timer only if not recording
                if not self.is_recording:
                    self.long_press_timer.start(self.long_press_threshold)
                
                return False
            
            # Right button press - show menu
            elif event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.RightButton:
                self.show_menu()
                return True
            
            # Mouse move - handle dragging
            elif event.type() == QEvent.Type.MouseMove and (event.buttons() & Qt.MouseButton.LeftButton):
                if self._press_global_pos is not None:
                    current = event.globalPosition().toPoint()
                    if not self._dragging:
                        if (current - self._press_global_pos).manhattanLength() >= QApplication.startDragDistance():
                            self._dragging = True
                            # Cancel long press if we start dragging
                            self.long_press_timer.stop()
                            # Reset ready to record state
                            if self.ready_to_record:
                                self.ready_to_record = False
                                self.main_btn.setText("🤖")
                    
                    if self._dragging and self._drag_offset is not None:
                        self.move(current - self._drag_offset)
                        return True
                return False
            
            # Left button release - handle click, start recording, or stop recording
            elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self.long_press_timer.stop()
                was_dragging = self._dragging
                self._press_global_pos = None
                self._drag_offset = None
                self._dragging = False
                
                if not was_dragging:
                    if self.is_recording:
                        # Stop recording
                        self.stop_recording()
                    elif self.ready_to_record:
                        # User held long enough and now released - start recording
                        self.ready_to_record = False
                        self.start_recording()
                    else:
                        # Short click - toggle chat if it wasn't held long enough
                        if self.press_start_time and (time.time() - self.press_start_time) < (self.long_press_threshold / 1000.0):
                            self.toggle_chat_window()
                
                self.press_start_time = None
                return True if was_dragging else False

        return super().eventFilter(obj, event)

    def on_long_press(self):
        """Called when button is held for long press threshold - show ready to record indicator."""
        if not self.is_recording and not self._dragging:
            self.ready_to_record = True
            # Change icon to indicate ready to record (but don't start yet)
            self.main_btn.setText("🎙️")
    
    def animate_recording(self):
        """Clean rotating spinner animation."""
        self.animation_step = (self.animation_step + 1) % 8
        
        # Standard Unicode spinner
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]
        
        self.main_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(80, 80, 80, 200);
                color: #ff4444;
                border-radius: 28px;
                font-size: 28px;
                border: 2px solid rgba(255, 80, 80, 0.6);
            }
        """)
        self.main_btn.setText(spinner_chars[self.animation_step])
    
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
        clear_chat_action = QAction("Clear Chat History", self)
        clear_chat_action.triggered.connect(self.clear_chat_all)
        menu.addAction(clear_chat_action)
        
        menu.addSeparator()
        close_action = QAction("Close", self)
        close_action.triggered.connect(self.quit_app)
        menu.addAction(close_action)

        # Show menu below the main button
        menu.exec(self.main_btn.mapToGlobal(self.main_btn.rect().bottomLeft()))

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
            # Position chat window above the widget
            self.position_chat_window()
            self.chat_window.show()
            self.chat_window.raise_()
            self.chat_window.activateWindow()
            # Fetch chat history when opening
            self.fetch_and_display_chat_history()
    
    def position_chat_window(self):
        """Position chat window centered above the widget."""
        if not self.chat_window:
            return
        
        # Get widget geometry
        widget_rect = self.frameGeometry()
        widget_x = widget_rect.x()
        widget_y = widget_rect.y()
        widget_width = widget_rect.width()
        
        # Get chat window size
        chat_width = self.chat_window.width()
        chat_height = self.chat_window.height()
        
        # Get screen geometry
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Calculate position: centered horizontally with widget, above it
        chat_x = widget_x + (widget_width - chat_width) // 2
        chat_y = widget_y - chat_height - 10  # 10px gap above widget
        
        # Ensure chat window stays within screen bounds
        if chat_x < screen.x():
            chat_x = screen.x() + 10
        elif chat_x + chat_width > screen.x() + screen.width():
            chat_x = screen.x() + screen.width() - chat_width - 10
        
        if chat_y < screen.y():
            chat_y = screen.y() + 10
        
        self.chat_window.move(chat_x, chat_y)
    
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
    
    def clear_chat_all(self):
        """Clear chat history both locally and on the server."""
        # Clear local UI
        if self.chat_window:
            self.chat_window.clear_chat()
        
        # Send request to server to clear history
        def _clear_on_server():
            try:
                response = requests.delete(f"{self.agent_url}/chat/history", timeout=5)
                if response.status_code == 200:
                    print("Chat history cleared on server")
                else:
                    print(f"Failed to clear chat history on server: {response.status_code}")
            except Exception as e:
                print(f"Failed to clear chat history on server: {e}")
        
        threading.Thread(target=_clear_on_server, daemon=True).start()
    
    def send_to_agent(self, text, screenshots_data=None):
        """Send text and optional screenshots to the agent service and handle streaming response via WebSocket."""
        if not self.chat_window:
            return
        
        # Build message with file context if files are attached (same as manual send)
        if self.chat_window.dropped_files:
            file_context = "\n\n**Attached files/folders:**\n"
            for path in self.chat_window.dropped_files:
                file_context += f"- `{path}`\n"
            text = text + file_context if text else file_context.strip()
            # Clear attached files after including them
            self.chat_window.clear_attached_files()
        
        # Add user message to chat (with file context if any)
        display_text = text if text else f"[{len(screenshots_data) if screenshots_data else 0} Screenshot(s)]"
        self.chat_window.add_user_message(display_text)
        
        # Start AI response
        self.chat_window.start_ai_response()
        
        def _stream():
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self._websocket_stream(text, screenshots_data))
            except Exception as e:
                print(f"Error in websocket stream: {e}")
                traceback.print_exc()
                self.agent_event_received.emit({
                    "type": "error",
                    "message": f"Failed to communicate with agent: {e}"
                })
                self.agent_event_received.emit({"type": "stream.finished"})
            finally:
                loop.close()
        
        threading.Thread(target=_stream, daemon=True).start()
    
    async def _websocket_stream(self, text, screenshots_data=None):
        """Handle WebSocket streaming communication with chunked screenshot sending."""
        # Convert http:// to ws://
        ws_url = self.agent_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/chat/ws"
        
        try:
            # Increase timeouts and max message size for screenshots
            async with websockets.connect(
                ws_url, 
                ping_interval=None,  # Disable automatic ping/pong
                close_timeout=10,
                max_size=10 * 1024 * 1024  # 10MB max message size
            ) as websocket:
                # Send initial message WITHOUT screenshots
                payload = {
                    "type": "message",
                    "message": text,
                    "has_screenshots": bool(screenshots_data),
                    "screenshot_count": len(screenshots_data) if screenshots_data else 0
                }
                await websocket.send(json.dumps(payload))
                
                # Send each screenshot as a separate message to avoid size limits
                if screenshots_data:
                    for idx, screenshot_b64 in enumerate(screenshots_data):
                        screenshot_payload = {
                            "type": "screenshot",
                            "index": idx,
                            "data": screenshot_b64
                        }
                        await websocket.send(json.dumps(screenshot_payload))
                        # Small delay to ensure order
                        await asyncio.sleep(0.01)
                    
                    # Signal all screenshots sent
                    await websocket.send(json.dumps({"type": "screenshots_complete"}))
                
                # Receive streaming events
                async for message in websocket:
                    try:
                        event = json.loads(message)
                        
                        # Check for completion
                        if event.get("type") == "stream.finished":
                            self.agent_event_received.emit(event)
                            break
                        
                        # Emit event to UI thread
                        self.agent_event_received.emit(event)
                        
                    except json.JSONDecodeError as je:
                        print(f"JSON decode error: {je}")
                    except Exception as ee:
                        print(f"Error processing event: {ee}")
                        traceback.print_exc()
                        
        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket error: {e}")
            raise
        except Exception as e:
            print(f"Error in websocket stream: {e}")
            traceback.print_exc()
            raise
    
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
                # Stop sending animation
                self.chat_window.stop_sending_state()
            
            elif event_type == "error":
                # Custom error event
                error_msg = event.get("message", "Unknown error")
                self.chat_window.append_to_ai_response(f"\n[Error] {error_msg}\n", '31')
                self.chat_window.finish_ai_response()
                # Stop sending animation on error
                self.chat_window.stop_sending_state()
        
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

        # Start recording animation - clean spinner
        self.animation_step = 0
        self.main_btn.setText("⠋")
        self.recording_animation_timer.start(100)  # 100ms for smooth rotation

    def stop_recording(self):
        self.is_recording = False
        
        # Stop animation and restore icon with original style
        self.recording_animation_timer.stop()
        self.main_btn.setText("🤖")
        self.main_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(50, 50, 50, 200);
                color: white;
                border-radius: 28px;
                font-size: 28px;
                border: 2px solid rgba(255, 255, 255, 0.1);
            }
            QPushButton:hover {
                background-color: rgba(70, 70, 70, 220);
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
        """)
        
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
                
                # If transcription successful, open chat if not visible and send to agent
                if isinstance(data, dict) and "text" in data:
                    transcribed_text = data["text"]
                    if transcribed_text:
                        # Open chat window if not visible
                        if not self.chat_window or not self.chat_window.isVisible():
                            self.toggle_chat_window()
                        # Use signal to call send_to_agent on main thread
                        self.transcription_received.emit(transcribed_text)
                
            except Exception as e:
                print("Upload failed:", e)

        threading.Thread(target=_send, daemon=True).start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gadget = Gadget()
    gadget.show()
    sys.exit(app.exec())
