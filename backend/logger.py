"""
logger.py — Central logging for Repochat.

Writes every API call, success, and error to:
  - logs/repochat.log   (rotating, 5 MB per file, 3 backups)
  - stdout              (coloured, for dev convenience)

Usage:
    from logger import log
    log.info("something happened")
    log.error("something broke", exc_info=True)
    log.api_call("GET /index", session_id="abc123")
    log.api_success("GET /index", session_id="abc123", duration_ms=320)
    log.api_error("GET /index", error="repo not found", session_id="abc123")
"""

import logging
import logging.handlers
import os
import time
from functools import wraps
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "repochat.log"

# ── format ─────────────────────────────────────────────────────────────────────
_FILE_FMT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

# ANSI colours for console only
_RESET  = "\033[0m"
_GREY   = "\033[90m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_BOLD   = "\033[1m"

_LEVEL_COLOURS = {
    "DEBUG":    _GREY,
    "INFO":     _GREEN,
    "WARNING":  _YELLOW,
    "ERROR":    _RED,
    "CRITICAL": _BOLD + _RED,
}


class _ColourFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelname, _RESET)
        record.levelname = f"{colour}{record.levelname:<8}{_RESET}"
        record.name      = f"{_CYAN}{record.name:<20}{_RESET}"
        record.asctime   = self.formatTime(record, _DATE_FMT)
        return f"{_GREY}{record.asctime}{_RESET} | {record.levelname} | {record.name} | {record.getMessage()}"


def _build_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:          # avoid duplicate handlers on reload
        return logger
    logger.setLevel(logging.DEBUG)

    # ── rotating file handler (plain text) ─────────────────────────────────
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_FILE_FMT, datefmt=_DATE_FMT))
    logger.addHandler(fh)

    # ── console handler (coloured) ──────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_ColourFormatter())
    logger.addHandler(ch)

    return logger


# ── Extended logger with helper methods ────────────────────────────────────────

class RepochatLogger(logging.Logger):
    """Adds api_call / api_success / api_error convenience methods."""

    def api_call(self, endpoint: str, **ctx):
        """Log the start of an API call."""
        extra = " | ".join(f"{k}={v}" for k, v in ctx.items())
        self.info(f"→ CALL     {endpoint}  {extra}")

    def api_success(self, endpoint: str, duration_ms: float = 0, **ctx):
        """Log a successful API response."""
        extra = " | ".join(f"{k}={v}" for k, v in ctx.items())
        self.info(f"✓ SUCCESS  {endpoint}  {duration_ms:.1f}ms  {extra}")

    def api_error(self, endpoint: str, error: str = "", **ctx):
        """Log a failed API call."""
        extra = " | ".join(f"{k}={v}" for k, v in ctx.items())
        self.error(f"✗ ERROR    {endpoint}  error={error!r}  {extra}")

    def agent(self, agent_name: str, message: str):
        """Log an agent action."""
        self.info(f"[AGENT:{agent_name}] {message}")

    def cache(self, hit: bool, key: str):
        """Log a cache hit or miss."""
        status = "HIT " if hit else "MISS"
        self.debug(f"[CACHE:{status}] {key}")

    def rate_queue(self, message: str):
        """Log rate-queue events (queued, retry, backoff)."""
        self.warning(f"[RATE_QUEUE] {message}")


logging.setLoggerClass(RepochatLogger)


def get_logger(name: str = "repochat") -> RepochatLogger:
    """
    Return a named RepochatLogger.

    Example:
        from logger import get_logger
        log = get_logger(__name__)
    """
    logger = _build_logger(name)
    # Ensure it is cast to our subclass (logging registry may not use it)
    if not isinstance(logger, RepochatLogger):
        logger.__class__ = RepochatLogger
    return logger  # type: ignore[return-value]


# ── Module-level default logger ────────────────────────────────────────────────
log: RepochatLogger = get_logger("repochat")


# ── Decorator ─────────────────────────────────────────────────────────────────

def log_endpoint(endpoint_name: str):
    """
    Decorator for FastAPI route handlers.
    Logs call start, success (with duration), and any exception.

    Usage:
        @app.post("/index")
        @log_endpoint("POST /index")
        async def index_route(body: IndexRequest):
            ...
    """
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            _log = get_logger("repochat.endpoint")
            _log.api_call(endpoint_name)
            t0 = time.perf_counter()
            try:
                result = await fn(*args, **kwargs)
                duration = (time.perf_counter() - t0) * 1000
                _log.api_success(endpoint_name, duration_ms=duration)
                return result
            except Exception as exc:
                duration = (time.perf_counter() - t0) * 1000
                _log.api_error(endpoint_name, error=str(exc))
                _log.exception(f"Unhandled exception in {endpoint_name}")
                raise
        return wrapper
    return decorator
