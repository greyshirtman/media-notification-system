import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def configure_logging(log_level=None, log_file=None):
    """
    Configure application-wide logging
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, logs will only go to stdout
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, (log_level or 'INFO').upper(), None)
    
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, defaulting to INFO")
        numeric_level = logging.INFO
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicate logging
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    verbose_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler if log_file is specified
    if log_file:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # Create rotating file handler (10MB max size, keep 5 backups)
            file_handler = RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5
            )
            file_handler.setFormatter(verbose_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Error setting up file logging: {e}")
    
    # Create module loggers
    loggers = {
        'main': logging.getLogger('main'),
        'notifier': logging.getLogger('notifier')
    }
    
    # Log startup message
    root_logger.info(f"Logging configured with level: {logging.getLevelName(numeric_level)}")
    if log_file:
        root_logger.info(f"Log file: {log_file}")
        
    return loggers
