import sys
from loguru import logger
from app.core.config import settings


def setup_logging() -> None:
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.debug else "INFO",
        colorize=True,
    )

    # File handler for errors
    logger.add(
        "logs/error.log",
        format=log_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

    # File handler for all logs
    logger.add(
        "logs/app.log",
        format=log_format,
        level="INFO",
        rotation="50 MB",
        retention="14 days",
        compression="zip",
    )

    logger.info(f"Logging initialized | Environment: {settings.environment}")
