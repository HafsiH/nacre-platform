"""
Logging configuration for the NACRE platform.
"""
import logging
import logging.handlers
import os
from pathlib import Path
from ..config import settings


def setup_logging():
    """Setup logging configuration for the application."""
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.storage_dir) / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file_path = log_dir / settings.log_file
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, settings.log_level.upper()))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
