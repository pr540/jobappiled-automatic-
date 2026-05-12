"""Structured JSON logger used across all modules."""
import logging
import os
from pythonjsonlogger import jsonlogger

os.makedirs("logs", exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(f"logs/{name}.log", encoding="utf-8")
    handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.addHandler(console)
    return logger
