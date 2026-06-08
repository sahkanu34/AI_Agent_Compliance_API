"""
app/utils/logger.py
Centralised logging setup using rich for coloured output.
"""
import logging
import sys
from rich.logging import RichHandler
from app.utils.config import get_settings


def get_logger(name: str) -> logging.Logger:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
        force=True,
    )
    return logging.getLogger(name)
