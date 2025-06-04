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
    Centralized logging system that outputs to files instead of stdout/stderr.
    """
    
    def __init__(self, log_dir=None):
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
        
        # Set up loggers
        self._setup_loggers()
        
        # Redirect stdout and stderr
        self._redirect_streams()
    
    def _setup_loggers(self):
        """Set up the logging configuration."""
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # App logger (INFO and above)
        self.app_logger = logging.getLogger('ThoughtPrint.App')
        self.app_logger.setLevel(logging.INFO)
        
        app_handler = AppendOnFileHandler(self.app_log_file, encoding='utf-8')
        app_handler.setFormatter(formatter)
        self.app_logger.addHandler(app_handler)
        
        # Error logger (WARNING and above)
        self.error_logger = logging.getLogger('ThoughtPrint.Error')
        self.error_logger.setLevel(logging.WARNING)
        
        error_handler = AppendOnFileHandler(self.error_log_file, encoding='utf-8')
        error_handler.setFormatter(formatter)
        self.error_logger.addHandler(error_handler)
        
        # Prevent propagation to root logger
        self.app_logger.propagate = False
        self.error_logger.propagate = False
    
    def _redirect_streams(self):
        """Redirect stdout and stderr to log files."""
        # Create custom stream classes
        class LogStream:
            def __init__(self, logger, level):
                self.logger = logger
                self.level = level
                self.buffer = ""
            
            def write(self, message):
                if message and message.strip():
                    # Remove trailing newlines for cleaner logging
                    clean_message = message.rstrip('\n\r')
                    if clean_message:
                        self.logger.log(self.level, clean_message)
            
            def flush(self):
                pass
        
        # Redirect stdout to app logger
        sys.stdout = LogStream(self.app_logger, logging.INFO)
        
        # Redirect stderr to error logger
        sys.stderr = LogStream(self.error_logger, logging.ERROR)
    
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

def init_logging(log_dir=None):
    """Initialize the logging system."""
    global _logger_instance
    _logger_instance = FileLogger(log_dir)
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