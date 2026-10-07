import logging
import sys

from app.core.config import get_settings


def setup_logging() -> logging.Logger:
    """
    Configures and returns the application root logger.
    Provides structured, clean format for both local development and containerized production.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    log_format = (
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s"
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )

    logger = logging.getLogger("geospatial_api")
    logger.setLevel(log_level)
    return logger

logger = setup_logging()
