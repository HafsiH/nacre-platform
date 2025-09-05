"""
Utility modules for the NACRE platform.
"""

from .error_handler import (
    NacreError,
    FileProcessingError,
    ClassificationError,
    ConfigurationError,
    handle_conversion_error,
    create_http_error,
    validate_file_format,
    validate_required_fields
)

__all__ = [
    "NacreError",
    "FileProcessingError", 
    "ClassificationError",
    "ConfigurationError",
    "handle_conversion_error",
    "create_http_error",
    "validate_file_format",
    "validate_required_fields"
]
