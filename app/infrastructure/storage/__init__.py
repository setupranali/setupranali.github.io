"""
Storage Infrastructure

Database and state storage implementations.
"""

# Backwards compatibility imports
from app.infrastructure.storage.state_storage import (
    StateStorage,
    get_state_storage,
    init_state_storage
)

__all__ = ["StateStorage", "get_state_storage", "init_state_storage"]
