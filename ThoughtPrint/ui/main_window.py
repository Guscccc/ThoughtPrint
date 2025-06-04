import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QMessageBox, QSizePolicy, QLabel, QStyleOption, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QSize
from PyQt6.QtGui import QIcon, QPainter

# Assuming settings_dialog and other modules are in expected locations
try:
    from .settings_dialog import SettingsDialog
    from ..core import config_manager
    from ..core import ai_handler
    from ..core import pdf_generator
    from ..core.ai_handler import AICommunicationError # Specific exception
    from ..core.pdf_generator import PDFGenerationError # Specific exception
    from ..core.logger import log_info, log_warning, log_error
except ImportError:
    # Fallback for direct execution or different project structure
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from ui.settings_dialog import SettingsDialog
    from core import config_manager
    from core import ai_handler
    from core import pdf_generator
    from core.ai_handler import AICommunicationError # Specific exception
    from core.pdf_generator import PDFGenerationError # Specific exception
    from core.logger import log_info, log_warning, log_error


class Worker(QObject):
    """
    Worker thread for handling AI requests and PDF generation.
    """
    finished = pyqtSignal() # Emitted when work is done
    error = pyqtSignal(str, str) # Emitted on error (title, message)
    success = pyqtSignal(str) # Emitted on success (e.g., PDF path)

    def __init__(self, prompt_text, provider_config, system_prompt_text):
        super().__init__()
        self.prompt_text = prompt_text
        self.provider_config = provider_config
        self.system_prompt_text = system_prompt_text

    def run(self):
        try:
            log_info(f"Worker: Sending to AI provider: {self.provider_config.get('name')}")
            ai_response_markdown = ai_handler.get_ai_response(
                self.prompt_text, self.provider_config, self.system_prompt_text
            )
            log_info("Worker: AI response received.")
        except AICommunicationError as e:
            log_error(f"Worker: AI Communication Error: {e}")
            self.error.emit("AI Error", f"Error communicating with AI provider: {e}")
            self.finished.emit()
            return
        except ValueError as e: # From invalid AI config
            log_error(f"Worker: AI Configuration Value Error: {e}")
            self.error.emit("AI Configuration Error", f"AI configuration error: {e}")
            self.finished.emit()
            return
        except Exception as e: # Catch-all for unexpected AI handler errors
            log_error(f"Worker: Unexpected AI Error: {e}")
            self.error.emit("Unexpected AI Error", f"An unexpected error occurred with the AI handler: {e}")
            self.finished.emit()
            return

        try:
            log_info("Worker: Generating PDF...")
            pdf_path = pdf_generator.create_pdf(self.prompt_text, ai_response_markdown)
            log_info(f"Worker: PDF generated successfully: {pdf_path}")
            self.success.emit(pdf_path)
        except PDFGenerationError as e:
            log_error(f"Worker: PDF Generation Error: {e}")
            self.error.emit("PDF Generation Error", f"Error generating PDF: {e}")
        except Exception as e: # Catch-all for unexpected PDF generator errors
            log_error(f"Worker: Unexpected PDF Error: {e}")
            self.error.emit("Unexpected PDF Error", f"An unexpected error occurred during PDF generation: {e}")
        finally:
            self.finished.emit()


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = None # To hold the QThread
        self.worker = None # To hold the Worker object
        self.last_input_text = "" # To store input text during processing
        self.setWindowTitle("Input") # Title for this widget if shown standalone
        
        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5) # Small margins
        main_layout.setSpacing(5)

        # Horizontal layout for the custom title bar
        title_bar_layout = QHBoxLayout()
        title_bar_layout.setContentsMargins(0, 0, 0, 0) # No margins for the title bar itself
        title_bar_layout.setSpacing(5)

        self.title_label = QLabel(" ") # Window Title
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # Allow clicks to pass through to parent for dragging
        title_bar_layout.addWidget(self.title_label)

        title_bar_layout.addStretch(1) # Pushes buttons to the right

        self.pin_button = QPushButton("") # No text
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(True)
        self.pin_button.setToolTip("Toggle Always on Top")
        self.pin_button.setFixedSize(QSize(28, 22)) # Adjust size for icon
        self.pin_button.setIconSize(QSize(16,16)) # Adjust icon size
        self.update_pin_button_appearance(True) # Set initial icon
        self.pin_button.clicked.connect(self.toggle_pin)
        title_bar_layout.addWidget(self.pin_button)

        self.close_button = QPushButton() # No text, will use icon
        self.close_button.setToolTip("Close Application")
        close_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)
        self.close_button.setIcon(close_icon)
        self.close_button.setFixedSize(QSize(28, 22)) # Adjust size for icon
        self.close_button.setIconSize(QSize(16,16)) # Adjust icon size
        self.close_button.clicked.connect(self.close_app)
        # Remove custom stylesheet for normal color
        self.close_button.setStyleSheet("QPushButton { border: none; background: transparent; }") # Make it flat
        title_bar_layout.addWidget(self.close_button)
        
        main_layout.addLayout(title_bar_layout)

        self.input_line_edit = QLineEdit()
        self.input_line_edit.setPlaceholderText("Enter")
        self.input_line_edit.returnPressed.connect(self.handle_input)
        main_layout.addWidget(self.input_line_edit)
        
        self.setLayout(main_layout)
        
        # Initial button appearance based on parent's state (if parent exists and has the state)
        if self.parent() and hasattr(self.parent(), 'is_always_on_top'):
            self.update_pin_button_appearance(self.parent().is_always_on_top)
        # As per requirements, the window is "mini"
        # The main_app will set the overall window geometry.
        # This widget itself doesn't need to define a fixed size here.

    def handle_input(self):
        user_text = self.input_line_edit.text().strip()

        if not user_text: # Ignore empty input
            return

        if user_text.lower() == "/config":
            self.open_settings_dialog()
            # Input box is NOT cleared as per requirements
        else:
            self.process_ai_request(user_text)
            # Input box is NOT cleared

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec()
        # After dialog closes, settings might have changed.
        # No immediate action needed here as settings are loaded on demand by handlers.

    def process_ai_request(self, prompt_text):
        log_info(f"Main Thread: Queuing AI request for: {prompt_text}")

        # Disable input while processing to prevent multiple submissions
        self.last_input_text = self.input_line_edit.text() # Store current text
        self.input_line_edit.setEnabled(False)
        self.input_line_edit.clear() # Make input box blank when inactive

        provider_config = config_manager.get_selected_provider()
        system_prompt_text = config_manager.get_system_prompt()

        if not provider_config:
            QMessageBox.warning(self, "Configuration Error",
                                "No AI provider is configured or selected. Please check settings using '/config'.")
            self.input_line_edit.setEnabled(True) # Re-enable input
            self.input_line_edit.setText(self.last_input_text) # Restore text
            return

        # Setup and start the thread
        self.thread = QThread()
        self.worker = Worker(prompt_text, provider_config, system_prompt_text)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.success.connect(self.on_processing_success)
        self.worker.error.connect(self.on_processing_error)
        self.worker.finished.connect(self.on_processing_finished)
        
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def on_processing_success(self, pdf_path):
        log_info(f"Main Thread: Success! PDF generated at {pdf_path}")
        # No QMessageBox for success to adhere to "does nothing apparently"
        # For dev: QMessageBox.information(self, "Success", f"PDF generated: {pdf_path}")

    def on_processing_error(self, title, message):
        log_error(f"Main Thread: Error - {title}: {message}")
        # Adhering to "does nothing apparently" for errors too.
        # Original behavior showed QMessageBox. For now, only logging.
        # QMessageBox.critical(self, title, message)

    def on_processing_finished(self):
        log_info("Main Thread: Background processing finished.")
        self.input_line_edit.setEnabled(True) # Re-enable input
        self.input_line_edit.setText(self.last_input_text) # Restore text
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()
        self.thread = None
        self.worker = None

    def toggle_pin(self):
        if self.parent() and hasattr(self.parent(), 'toggle_always_on_top'):
            self.parent().toggle_always_on_top()
            # The parent will call update_pin_button_appearance

    def update_pin_button_appearance(self, is_on_top):
        self.pin_button.setChecked(is_on_top)
        if is_on_top:
            self.pin_button.setText("📌") # Unicode pin character
            # self.pin_button.setIcon(QIcon("path/to/pin_icon.png")) # Example for custom icon
        else:
            self.pin_button.setText("⚪") # Unicode circle character (placeholder for unpinned)
            # self.pin_button.setIcon(QIcon("path/to/unpin_icon.png")) # Example for custom icon

    def close_app(self):
        if self.parent():
            self.parent().close() # Call close on the QMainWindow
        
if __name__ == '__main__':
    # Initialize logging for standalone testing
    try:
        from ..core.logger import init_logging
        init_logging()
    except ImportError:
        from core.logger import init_logging
        init_logging()
    
    app = QApplication(sys.argv)
    # For testing, ensure a settings file can be accessed or created by SettingsDialog
    if not config_manager.SETTINGS_FILE_PATH.exists():
        config_manager.save_settings(config_manager.DEFAULT_SETTINGS)

    main_win = QWidget() # Create a dummy parent window
    main_win.setWindowTitle("Main App Test Window")
    main_win_layout = QVBoxLayout(main_win)
    
    ai_input_widget = MainWindow()
    main_win_layout.addWidget(ai_input_widget)
    
    main_win.setGeometry(300, 300, 500, 60) # Adjusted height for input box
    main_win.show()
    
    sys.exit(app.exec())