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

from core import request_trace
from core.logging_setup import InterceptHandler, setup_logging

setup_logging()

# --- Server params ---
bind = f"0.0.0.0:{os.getenv('PORT', '3000')}"
worker_class = "uvicorn_worker.UvicornWorker"
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
timeout = 300              # 5 min — avoid worker_abort mid heavy raster/zonal processing
# Worker recycling is OFF by default (0): under concurrent traffic each recycle resets the
# connections the dying worker had accepted (measured: ~2.4% failed requests and ~8x lower
# throughput at 100; still 0.27% failures at 1000) and briefly halves capacity while the new
# worker imports. A worker that leaks until the OOM Killer takes it is now logged with the
# requests it was serving (see core/request_trace.py) and respawned by gunicorn. Set
# GUNICORN_MAX_REQUESTS only if you need periodic recycling to shed GDAL/NumPy RAM growth.
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "0"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "10")) if max_requests else 0

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
    worker process is reaped. gunicorn's own arbiter already logs *why*
    (SIGKILL/OOM, signal, exit code) through "gunicorn.error". Here we add what
    the dead worker was serving: if it left a request journal behind (it only
    exists while RAM is above the threshold, and a clean exit removes it), dump
    it into the error log. Runs for every exit, including max_requests
    recycling, so the clean case must stay quiet.
    """
    dumped = request_trace.dump_journal(
        worker.pid,
        f"Worker PID {worker.pid} morreu de forma abrupta com a RAM acima do limiar (provável OOM Killer).",
    )
    if not dumped:
        _hook_logger.info(f"Worker encerrado e reaproveitado pelo gunicorn: PID {worker.pid}")


def worker_int(worker):
    """Called when a worker receives SIGINT/SIGQUIT (e.g. Ctrl+C, graceful shutdown)."""
    _hook_logger.warning(f"Worker recebeu sinal de interrupção: PID {worker.pid}")
