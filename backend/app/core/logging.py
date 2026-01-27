"""Legacy logging compatibility shim - redirects to structured logging."""

# Re-export from observability.logging for backward compatibility
from app.observability.logging import get_logger, setup_structured_logging as setup_logging

__all__ = ["get_logger", "setup_logging"]
