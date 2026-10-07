import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from ..paths import get_data_dir
from .log_scrubber import SensitiveFilter


def setup_logging() -> None:
    logger = logging.getLogger()
    if logger.handlers:
        return

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_dir = get_data_dir() / "logs"
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_dir / "bizibox.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    scrubber = SensitiveFilter()
    logger.addFilter(scrubber)

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").addFilter(scrubber)
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
