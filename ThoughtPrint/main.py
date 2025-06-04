import sys
import logging
import atexit
from PyQt6.QtWidgets import QApplication, QMainWindow # Using PyQt6 as planned
from PyQt6.QtCore import Qt # Import Qt
from PyQt6.QtGui import QCloseEvent # Import QCloseEvent for proper type hinting

# Placeholder for future imports
from .ui.main_window import MainWindow # Explicit relative import
from .core.logger import init_logging, log_info, log_warning, log_error

class AiToPdfApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle(" ")
        self.main_widget = MainWindow(self) # Pass self as parent
        self.setCentralWidget(self.main_widget)
        # Set initial size for the main application window
        # The "mini window" requirement refers to the simplicity of the input area,
        # not necessarily an extremely tiny overall application window.
        self.setGeometry(300, 300, 300, 60) # x, y, width, height (Adjusted for minimal height)
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event to ensure application terminates properly."""
        log_info("Application window closing - terminating application")
        
        # Clean up any running threads in the main widget
        if hasattr(self.main_widget, 'thread') and self.main_widget.thread is not None:
            log_info("Cleaning up background thread before exit")
            self.main_widget.thread.quit()
            self.main_widget.thread.wait()
        
        # Accept the close event and quit the application
        event.accept()
        QApplication.quit()

def main():
    # Initialize logging system first
    init_logging() # from .core.logger
    atexit.register(logging.shutdown) # Ensure loggers are closed on exit
    
    # Ensure core.config_manager can create its settings file if it doesn't exist
    # This is important if the app is run for the first time.
    # A more robust solution might involve an explicit app initialization step.
    try:
        from .core import config_manager # Explicit relative import
        if not config_manager.SETTINGS_FILE_PATH.exists():
            log_info(f"Initializing default settings at {config_manager.SETTINGS_FILE_PATH}...")
            config_manager.save_settings(config_manager.DEFAULT_SETTINGS)
    except ImportError:
        log_warning("Could not import core.config_manager for pre-flight checks.")
    except Exception as e:
        log_error(f"Error during pre-flight settings check: {e}")

    app = QApplication(sys.argv)
    main_app = AiToPdfApp()
    main_app.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()