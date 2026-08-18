import asyncio
import logging
import os
import sys
from pathlib import Path

import psutil
from loguru import logger

from core.config import settings

LOG_DIR = Path(settings.LOG_DIR)
SYSTEM_HEALTH_CHANNEL = "system_health"
SYSTEM_HEALTH_WARNING_RAM_PERCENT = 90


def _ram_mb() -> float:
    try:
        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return 0.0


def _sys_health() -> dict:
    try:
        vm = psutil.virtual_memory()
        return {
            "ram_usada_mb": round((vm.total - vm.available) / (1024 * 1024), 2),
            "ram_disponivel_mb": round(vm.available / (1024 * 1024), 2),
            "ram_uso_percent": vm.percent,
        }
    except Exception:
        return {}


class InterceptHandler(logging.Handler):
    """Redireciona o `logging` padrão (uvicorn, rotas da API, libs de terceiros) para o loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        local = f"{record.name}.{record.funcName}" if record.funcName != "<module>" else record.name
        logger.bind(local=local, ram_mb=_ram_mb(), sys_health=_sys_health()).opt(
            depth=depth, exception=record.exc_info
        ).log(level, record.getMessage())


def _console_format(record) -> str:
    # Formatter estático (string) faz o loguru concatenar "\n{exception}" por conta própria,
    # duplicando o traceback (já impresso pelo sink de erro). Como função, esse auto-append não ocorre.
    ram_mb = record["extra"].get("ram_mb", 0.0)
    sys_uso_percent = (record["extra"].get("sys_health") or {}).get("ram_uso_percent")
    sys_part = f"{sys_uso_percent}%" if sys_uso_percent is not None else "--"
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan><bold>{extra[local]}</bold></cyan> - {message} "
        f"(RAM:{ram_mb}MB SYS:{sys_part})\n"
    )


def _error_file_format(record) -> str:
    return (
        "=========== OCORRÊNCIA DE ERRO [{time:YYYY-MM-DD HH:mm:ss.SSS}] ===========\n"
        "NÍVEL: {level} | PID: {process} | LOCAL: {extra[local]} | RAM: {extra[ram_mb]}MB\n"
        "MENSAGEM: {message}\n"
        "SAÚDE DO SISTEMA: {extra[sys_health]}\n"
        "TRACEBACK:\n{exception}\n"
        "--------------------------------------------------------------------------\n"
    )


def _plain_line_format(record) -> str:
    """Uma linha por registro — usado nos arquivos info/ e system/ (bem mais tráfego que errors/)."""
    ram_mb = record["extra"].get("ram_mb", 0.0)
    sys_uso_percent = (record["extra"].get("sys_health") or {}).get("ram_uso_percent")
    sys_part = f"{sys_uso_percent}%" if sys_uso_percent is not None else "--"
    return (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | PID:{process} | "
        "{extra[local]} - {message} "
        f"(RAM:{ram_mb}MB SYS:{sys_part})\n"
    )


def _is_system_health(record) -> bool:
    return record["extra"].get("channel") == SYSTEM_HEALTH_CHANNEL


def setup_logging() -> None:
    """
    Console mostra tudo (INFO+). Disco persiste em 3 trilhas separadas, mesma
    estrutura de pastas (LOG_DIR/<trilha>/<ano>/<mes>/<data>.log):
      - errors/  ERROR/CRITICAL, com traceback completo
      - system/  snapshots periódicos de saúde do sistema (ver start_system_health_monitor)
      - info/    tudo mais em INFO/WARNING (inclui uvicorn.access)
    """
    logger.remove()
    logger.configure(extra={"local": "app", "ram_mb": 0.0, "sys_health": {}})

    logger.add(
        sys.stdout,
        level="INFO",
        format=_console_format,
        filter=lambda record: not _is_system_health(record),
    )

    logger.add(
        LOG_DIR / "errors/{time:YYYY}/{time:MM}/{time:YYYY-MM-DD}.log",
        level="ERROR",
        format=_error_file_format,
        enqueue=False,
        backtrace=True,
        diagnose=True,
        catch=True,
    )

    logger.add(
        LOG_DIR / "system/{time:YYYY}/{time:MM}/{time:YYYY-MM-DD}.log",
        level="INFO",
        filter=_is_system_health,
        format=_plain_line_format,
        enqueue=False,
        catch=True,
    )

    logger.add(
        LOG_DIR / "info/{time:YYYY}/{time:MM}/{time:YYYY-MM-DD}.log",
        level="INFO",
        filter=lambda record: record["level"].name not in ("ERROR", "CRITICAL") and not _is_system_health(record),
        format=_plain_line_format,
        enqueue=False,
        catch=True,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False


async def start_system_health_monitor(interval_seconds: float = 10.0) -> asyncio.Task:
    """
    Loga um snapshot de saúde do sistema a cada `interval_seconds`, persistido
    só em LOG_DIR/system/ (não duplica em info/). Roda como task em background
    durante a vida do processo — ver lifespan em main.py.
    """

    async def _loop() -> None:
        while True:
            health = _sys_health()
            ram_uso_percent = health.get("ram_uso_percent") or 0
            level = "WARNING" if ram_uso_percent >= SYSTEM_HEALTH_WARNING_RAM_PERCENT else "INFO"
            logger.bind(
                channel=SYSTEM_HEALTH_CHANNEL,
                local="system.health_monitor",
                ram_mb=_ram_mb(),
                sys_health=health,
            ).log(
                level,
                f"RAM sistema: {health.get('ram_uso_percent')}% em uso "
                f"({health.get('ram_usada_mb')}MB usados, {health.get('ram_disponivel_mb')}MB livres)",
            )
            await asyncio.sleep(interval_seconds)

    return asyncio.create_task(_loop())
