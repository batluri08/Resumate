"""
Logging configuration for RestlessResume
"""

import logging
import logging.handlers
import os
from datetime import datetime

# Create logs directory if it doesn't exist
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Create logger
logger = logging.getLogger("restlessresume")
logger.setLevel(logging.DEBUG)

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

simple_formatter = logging.Formatter(
    '%(levelname)s: %(message)s'
)

# File handler - logs all messages to a rotating file
log_file = os.path.join(LOGS_DIR, "app.log")
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)
logger.addHandler(file_handler)

# Error file handler - logs only errors and above
error_log_file = os.path.join(LOGS_DIR, "errors.log")
error_handler = logging.handlers.RotatingFileHandler(
    error_log_file,
    maxBytes=10 * 1024 * 1024,
    backupCount=5
)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(detailed_formatter)
logger.addHandler(error_handler)

# Console handler - logs info and above to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(simple_formatter)
logger.addHandler(console_handler)


def get_logger(name: str = None):
    """Get a logger instance"""
    if name:
        return logging.getLogger(f"restlessresume.{name}")
    return logger
