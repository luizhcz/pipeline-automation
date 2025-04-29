import logging
import os
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Final, Optional

# helper
def _int_env(var: str, default: int) -> int:
    raw = os.getenv(var)
    if not raw:
        return default
    raw = raw.split("#", 1)[0].strip()      # remove comentário inline
    try:
        return int(raw)
    except ValueError:
        return default

LOG_LEVEL_ENV: Final = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: Final[Optional[str]] = os.getenv("LOG_FILE")
LOG_MAX_BYTES: Final[int] = _int_env("LOG_MAX_BYTES", 10_485_760)
LOG_BACKUP_COUNT: Final[int] = _int_env("LOG_BACKUP_COUNT", 3)

_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s – %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

def _configure_root() -> None:
    level = getattr(logging, LOG_LEVEL_ENV, logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        return

    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
    root.addHandler(stream)

    if LOG_FILE:
        path = Path(LOG_FILE).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        file_h = RotatingFileHandler(
            path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        file_h.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
        root.addHandler(file_h)

    root.setLevel(level)

_configure_root()

@lru_cache(None)
def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name)