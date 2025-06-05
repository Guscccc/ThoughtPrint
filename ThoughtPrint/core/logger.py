import logging
import sys
from pathlib import Path
from datetime import datetime
import os

class AppendOnFileHandler(logging.Handler):
    """
    A logging handler that opens the log file for each message
    and closes it immediately after writing.
    """
    def __init__(self, filename, encoding=None, delay=False):
        super().__init__()
        self.baseFilename = filename
        self.encoding = encoding
        # delay is not used by this handler as file is opened/closed per emit

    def emit(self, record):
        try:
            msg = self.format(record)
            # Ensure the log directory exists (it should be created by FileLogger's __init__)
            # but this is a good safeguard if the handler is used independently.
            log_dir = Path(self.baseFilename).parent
            log_dir.mkdir(parents=True, exist_ok=True)

            with open(self.baseFilename, 'a', encoding=self.encoding) as f:
                f.write(msg + self.terminator) # self.terminator is usually '\n'
            self.flush() # In this case, flush doesn't do much as file is closed.
        except Exception:
            self.handleError(record)

    # Add terminator attribute if not present in older Python logging.Handler
    # For Python 3.2+, logging.StreamHandler defines self.terminator = '\n'
    # We'll ensure it exists for robustness.
    terminator = '\n'
class FileLogger:
    """
    Centralized logging system that outputs to files and optionally to console.
    """
    
    def __init__(self, log_dir=None, enable_console=None):
        if log_dir is None:
            # Use the "logs" subdirectory in the current working directory for logs
            log_dir = Path.cwd() / "logs"
        else:
            log_dir = Path(log_dir)
        
        # Create logs directory if it doesn't exist
        log_dir.mkdir(exist_ok=True)
        
        # Set up log file paths
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.app_log_file = log_dir / f"ThoughtPrint_app_{timestamp}.txt"
        self.error_log_file = log_dir / f"ThoughtPrint_error_{timestamp}.txt"
        
        # Determine if console logging should be enabled
        if enable_console is None:
            self.enable_console = self._has_console()
        else:
            self.enable_console = enable_console
        
        # Store original stdout/stderr before any redirection
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Set up loggers
        self._setup_loggers()
        
        # Redirect stdout and stderr
        self._redirect_streams()
    
    def _has_console(self):
        """
        Check if a console is available for output.
        Returns False if running from .pyw file or in a GUI-only environment.
        """
        try:
            # Check if we're running from a .pyw file (no console)
            if sys.argv[0].endswith('.pyw'):
                return False
            
            # Check if stdout is connected to a terminal/console
            if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
                return True
            
            # On Windows, check if we have a console window
            if os.name == 'nt':
                try:
                    import ctypes
                    # GetConsoleWindow returns 0 if no console is attached
                    return ctypes.windll.kernel32.GetConsoleWindow() != 0
                except:
                    pass
            
            # Default to True if we can't determine (better to have console output than not)
            return True
        except:
            return False
    
    def _setup_loggers(self):
        """Set up the logging configuration."""
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console formatter (simpler, no timestamp for cleaner console output)
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(name)s: %(message)s'
        )

        # App logger (INFO and above)
        self.app_logger = logging.getLogger('ThoughtPrint.App')
        self.app_logger.setLevel(logging.INFO)
        
        # File handler for app logger
        app_handler = AppendOnFileHandler(self.app_log_file, encoding='utf-8')
        app_handler.setFormatter(file_formatter)
        self.app_logger.addHandler(app_handler)
        
        # Console handler for app logger (if console is available)
        if self.enable_console:
            console_handler = logging.StreamHandler(self.original_stdout)
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)
            self.app_logger.addHandler(console_handler)
        
        # Error logger (WARNING and above)
        self.error_logger = logging.getLogger('ThoughtPrint.Error')
        self.error_logger.setLevel(logging.WARNING)
        
        # File handler for error logger
        error_handler = AppendOnFileHandler(self.error_log_file, encoding='utf-8')
        error_handler.setFormatter(file_formatter)
        self.error_logger.addHandler(error_handler)
        
        # Console handler for error logger (if console is available)
        if self.enable_console:
            error_console_handler = logging.StreamHandler(self.original_stderr)
            error_console_handler.setFormatter(console_formatter)
            error_console_handler.setLevel(logging.WARNING)
            self.error_logger.addHandler(error_console_handler)
        
        # Prevent propagation to root logger
        self.app_logger.propagate = False
        self.error_logger.propagate = False
    
    def _redirect_streams(self):
        """Redirect stdout and stderr to log files, but preserve console output if available."""
        # Create custom stream classes
        class LogStream:
            def __init__(self, logger, level, original_stream=None, enable_console=False):
                self.logger = logger
                self.level = level
                self.original_stream = original_stream
                self.enable_console = enable_console
                self.buffer = ""
            
            def write(self, message):
                if message and message.strip():
                    # Remove trailing newlines for cleaner logging
                    clean_message = message.rstrip('\n\r')
                    if clean_message:
                        # Only log to file handlers, not console handlers
                        # (console handlers are added separately in _setup_loggers)
                        for handler in self.logger.handlers:
                            if isinstance(handler, AppendOnFileHandler):
                                handler.emit(self.logger.makeRecord(
                                    self.logger.name, self.level, "", 0, clean_message, (), None
                                ))
                        
                        # Also write to original stream if console is enabled
                        if self.enable_console and self.original_stream:
                            try:
                                self.original_stream.write(message)
                                self.original_stream.flush()
                            except:
                                pass  # Ignore errors writing to console
            
            def flush(self):
                if self.enable_console and self.original_stream:
                    try:
                        self.original_stream.flush()
                    except:
                        pass
        
        # Only redirect streams if console is not available
        # If console is available, we want to preserve normal stdout/stderr behavior
        # while still logging to files
        if not self.enable_console:
            # Redirect stdout to app logger (file only)
            sys.stdout = LogStream(self.app_logger, logging.INFO)
            
            # Redirect stderr to error logger (file only)
            sys.stderr = LogStream(self.error_logger, logging.ERROR)
        else:
            # Keep original streams but create hybrid streams that log to files AND output to console
            sys.stdout = LogStream(self.app_logger, logging.INFO, self.original_stdout, True)
            sys.stderr = LogStream(self.error_logger, logging.ERROR, self.original_stderr, True)
    
    def info(self, message):
        """Log an info message."""
        self.app_logger.info(message)
    
    def warning(self, message):
        """Log a warning message."""
        self.error_logger.warning(message)
    
    def error(self, message):
        """Log an error message."""
        self.error_logger.error(message)
    
    def debug(self, message):
        """Log a debug message."""
        self.app_logger.debug(message)

# Global logger instance
_logger_instance = None

def get_logger():
    """Get the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = FileLogger()
    return _logger_instance

def init_logging(log_dir=None, enable_console=None):
    """Initialize the logging system."""
    global _logger_instance
    _logger_instance = FileLogger(log_dir, enable_console)
    return _logger_instance

# Convenience functions for easy use throughout the app
def log_info(message):
    """Log an info message."""
    get_logger().info(message)

def log_warning(message):
    """Log a warning message."""
    get_logger().warning(message)

def log_error(message):
    """Log an error message."""
    get_logger().error(message)

def log_debug(message):
    """Log a debug message."""
    get_logger().debug(message)