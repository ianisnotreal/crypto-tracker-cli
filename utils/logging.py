import logging
import os
from logging.handlers import RotatingFileHandler


def get_logger(name="crypto"):
    os.makedirs(os.path.expanduser("~/.crypto_tracker"), exist_ok=True)
    log_path = os.path.expanduser("~/.crypto_tracker/crypto.log")

    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler.setFormatter(fmt)

    if not logger.handlers:
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler())

    return logger
