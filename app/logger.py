import logging
import sys
from functools import lru_cache


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """
    Returns a module-level logger.  Calling with the same name always returns
    the same instance (lru_cache), so handlers are only attached once.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger
