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
        self.is_always_on_top = True  # Default state, app starts on top
        self.old_pos = None # For dragging frameless window

        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool # Add Tool hint
        if self.is_always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        # Note: Qt.WindowType.Tool is re-added to attempt to hide from taskbar.
        # If specific 'Tool' window behaviors (like not appearing in taskbar prominently) are desired
        # and Frameless isn't working with it, this might need further platform-specific investigation.
        self.setWindowFlags(flags)
        # setWindowTitle is less relevant for frameless, but good practice
        self.setWindowTitle(" ")
        # Apply a simple border style
        self.setStyleSheet("QMainWindow { border: 1px solid #aaa; }") # Light gray border
        
        self.main_widget = MainWindow(self) # Pass self as parent
        self.setCentralWidget(self.main_widget)
        # Set initial size for the main application window
        # The "mini window" requirement refers to the simplicity of the input area,
        # not necessarily an extremely tiny overall application window.
        self.setGeometry(300, 300, 300, 60) # x, y, width, height (Adjusted for minimal height)
    
    def toggle_always_on_top(self):
        self.is_always_on_top = not self.is_always_on_top
        
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool # Add Tool hint
        if self.is_always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        # If not is_always_on_top, WindowStaysOnTopHint is simply not added
        
        self.hide() # Hide before changing flags
        self.setWindowFlags(flags)
        self.show() # Re-show to apply flag changes

        # Update button appearance in the child widget (MainWindow)
        if hasattr(self.main_widget, 'update_pin_button_appearance'):
            self.main_widget.update_pin_button_appearance(self.is_always_on_top)

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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the press is within the custom title bar area
            # For now, assume any press on MainWindow (which will contain the title bar) can drag
            # A more precise check would involve getting the geometry of the custom title bar
            # within the main_widget.
            if self.main_widget.geometry().contains(event.pos()):
                 # Check if the press is on the input_line_edit of main_widget
                if hasattr(self.main_widget, 'input_line_edit') and \
                   self.main_widget.input_line_edit.geometry().contains(
                       self.main_widget.mapFromGlobal(event.globalPosition().toPoint()) # map to main_widget coords
                   ):
                    self.old_pos = None # Don't drag if clicking on input field
                else:
                    self.old_pos = event.globalPosition().toPoint()


    def mouseMoveEvent(self, event):
        if self.old_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None

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