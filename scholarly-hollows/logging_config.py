"""
Scholarly Hollows Logging Configuration

Provides a simple logging setup for the plugin.
Compatible with Veritas Core's app.logging_config interface.
"""
import logging

# Configure root logger for the module
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Compatible with Veritas Core's get_logger function.
    """
    return logging.getLogger(name)
