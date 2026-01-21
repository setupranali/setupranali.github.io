"""
Shared Exceptions

Application-wide exception classes.
"""

# Backwards compatibility imports
from app.shared.exceptions.errors import (
    SetuPranaliError,
    ErrorCode,
    install_error_handlers,
    dataset_not_found,
    dimension_not_found,
    metric_not_found,
    query_validation_error,
    internal_error,
    sql_unsafe,
    nlq_provider_missing,
    nlq_translation_failed
)

__all__ = [
    "SetuPranaliError",
    "ErrorCode",
    "install_error_handlers",
    "dataset_not_found",
    "dimension_not_found",
    "metric_not_found",
    "query_validation_error",
    "internal_error",
    "sql_unsafe",
    "nlq_provider_missing",
    "nlq_translation_failed"
]
