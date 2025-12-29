"""
SetuPranali SDK Exceptions
"""


class SetuPranaliError(Exception):
    """Base exception for SetuPranali SDK."""
    
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
    
    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class AuthenticationError(SetuPranaliError):
    """Raised when authentication fails (invalid/missing API key)."""
    pass


class DatasetNotFoundError(SetuPranaliError):
    """Raised when the requested dataset doesn't exist."""
    pass


class QueryError(SetuPranaliError):
    """Raised when a query execution fails."""
    pass


class ValidationError(SetuPranaliError):
    """Raised when query parameters are invalid."""
    pass


class RateLimitError(SetuPranaliError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ConnectionError(SetuPranaliError):
    """Raised when connection to the server fails."""
    pass


class TimeoutError(SetuPranaliError):
    """Raised when a request times out."""
    pass

