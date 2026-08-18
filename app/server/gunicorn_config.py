"""
Production process manager config (gunicorn + uvicorn workers).

Local dev keeps using `uv run python main.py` (uvicorn --reload). This file
exists because reload-mode uvicorn has no supervisor watching worker health —
if a worker gets OOM-killed (SIGKILL) or segfaults, nothing can log it from
inside that worker (SIGKILL can't be caught), and uvicorn's own reload
supervisor only reacts to file changes, not worker death. Gunicorn's arbiter
process survives the worker's death and can log it from the outside.

Run with: uv run gunicorn -c gunicorn_config.py main:app
"""
import logging
import os

from gunicorn.glogging import Logger as GunicornLogger

from core.logging_setup import InterceptHandler, setup_logging

setup_logging()

# --- Server params ---
bind = f"0.0.0.0:{os.getenv('PORT', '3000')}"
worker_class = "uvicorn_worker.UvicornWorker"
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
timeout = 300              # 5 min — avoid worker_abort mid heavy raster/zonal processing
max_requests = 100         # recycle workers periodically to shed GDAL/NumPy RAM growth
max_requests_jitter = 10   # stagger recycling so workers don't all restart at once

# --- Gunicorn's own access/error logging ---
loglevel = "info"
accesslog = "-"
errorlog = "-"


class GunicornLoguruLogger(GunicornLogger):
    """Redirects gunicorn's own access/error logging into our loguru setup."""

    def __init__(self, cfg):
        super().__init__(cfg)
        logging.getLogger("gunicorn.error").handlers = [InterceptHandler()]
        logging.getLogger("gunicorn.access").handlers = [InterceptHandler()]


logger_class = GunicornLoguruLogger

_hook_logger = logging.getLogger("gunicorn.hooks")


def worker_abort(worker):
    """Called (in the worker itself) when gunicorn SIGABRTs a hung/timed-out worker."""
    _hook_logger.error(f"Worker abortado pelo gunicorn (timeout ou travamento): PID {worker.pid}")


def child_exit(server, worker):
    """
    Called in the arbiter — which survives the worker's death — right after a
    worker process is reaped. gunicorn's own arbiter already classifies *why*
    (SIGKILL/OOM, signal, exit code) and logs it through "gunicorn.error"
    right before calling this hook, which we already capture via
    GunicornLoguruLogger. This just marks that the dead worker was reaped, so
    it's easy to see in the log that gunicorn recovered from it on its own.
    """
    _hook_logger.error(f"Worker morto e reaproveitado pelo gunicorn: PID {worker.pid}")


def worker_int(worker):
    """Called when a worker receives SIGINT/SIGQUIT (e.g. Ctrl+C, graceful shutdown)."""
    _hook_logger.warning(f"Worker recebeu sinal de interrupção: PID {worker.pid}")
