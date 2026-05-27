from dome_core.logging import configure_logging, get_logger

from app.core.config import settings


def setup_logging() -> None:
    configure_logging(environment=settings.environment)


__all__ = ["setup_logging", "get_logger"]
