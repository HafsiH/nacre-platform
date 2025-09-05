"""
Error handling utilities for the NACRE platform.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class NacreError(Exception):
    """Base exception for NACRE platform errors."""
    
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class FileProcessingError(NacreError):
    """Raised when file processing fails."""
    pass


class ClassificationError(NacreError):
    """Raised when classification fails."""
    pass


class ConfigurationError(NacreError):
    """Raised when configuration is invalid."""
    pass


def handle_conversion_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle conversion errors and return structured error information."""
    error_info = {
        "error_type": type(error).__name__,
        "message": str(error),
        "context": context,
        "timestamp": None  # Will be set by caller
    }
    
    if isinstance(error, NacreError):
        error_info["error_code"] = error.error_code
        error_info["details"] = error.details
    else:
        error_info["error_code"] = "UNKNOWN_ERROR"
        error_info["details"] = {}
    
    logger.error(f"Conversion error: {error_info}")
    return error_info


def create_http_error(status_code: int, message: str, error_code: str = None) -> HTTPException:
    """Create a standardized HTTP error response."""
    detail = {
        "message": message,
        "error_code": error_code or f"HTTP_{status_code}"
    }
    return HTTPException(status_code=status_code, detail=detail)


def validate_file_format(filename: str, allowed_extensions: list = None) -> None:
    """Validate file format and raise appropriate error if invalid."""
    if allowed_extensions is None:
        allowed_extensions = ['.csv', '.xlsx']
    
    if not filename:
        raise FileProcessingError("Nom de fichier manquant", "MISSING_FILENAME")
    
    file_ext = filename.lower()
    if not any(file_ext.endswith(ext) for ext in allowed_extensions):
        raise FileProcessingError(
            f"Format de fichier non supporté. Utilisez: {', '.join(allowed_extensions)}",
            "UNSUPPORTED_FILE_FORMAT",
            {"filename": filename, "allowed_extensions": allowed_extensions}
        )


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """Validate that required fields are present in data."""
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        raise ConfigurationError(
            f"Champs requis manquants: {', '.join(missing_fields)}",
            "MISSING_REQUIRED_FIELDS",
            {"missing_fields": missing_fields}
        )
