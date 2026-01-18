import logging
from typing import Optional


DEFAULT_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def configure_logging(level: int = logging.INFO, fmt: str = DEFAULT_LOG_FORMAT) -> None:
    """Configure application logging."""
    logging.basicConfig(level=level, format=fmt)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger by name."""
    return logging.getLogger(name or __name__)
