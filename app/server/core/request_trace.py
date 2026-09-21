"""
Rastreio das últimas N requisições (método, caminho, corpo) para investigar OOM.

Um SIGKILL do OOM Killer não pode ser interceptado, então o processo morto não
consegue gravar nada na hora. Por isso cada worker mantém um buffer em memória
das últimas requisições e, quando a RAM passa do limiar, passa a espelhá-lo num
journal em LOG_DIR/requests/<pid>.jsonl (atualizado a cada requisição). Um
encerramento normal apaga o journal; se ele sobrar, o processo morreu de forma
abrupta e o journal é despejado no log de erros — pelo gunicorn (child_exit)
ou, se o pai também morreu, pelo próximo startup (recover_orphans).
"""
import asyncio
import contextlib
import itertools
import json
import logging
import os
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import psutil

from core.config import settings
from core.logging_setup import LOG_DIR, _ram_mb, _sys_health

log = logging.getLogger("request_trace")

JOURNAL_DIR = LOG_DIR / "requests"
_BODYLESS_METHODS = ("GET", "HEAD", "OPTIONS")
_HYSTERESIS = 0.9
_COMPACT_AFTER_RINGS = 10
_RETRY_AFTER_SECONDS = 60
_MIN_CHECK_INTERVAL = 0.1
_MAX_INFLIGHT = 50


def journal_path(pid: int) -> Path:
    return JOURNAL_DIR / f"{pid}.jsonl"


def _public(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if not k.startswith("_")}


class _Tracer:
    def __init__(self) -> None:
        self.ring: deque = deque(maxlen=max(1, settings.REQUEST_TRACE_SIZE))  # últimas concluídas
        self.inflight: dict[int, dict] = {}  # em andamento: nunca despejadas pelo tráfego novo
        self.active = False
        self._fh = None
        self._events = 0
        self._retry_at = 0.0
        self._last_check = 0.0
        self._ids = itertools.count(1)

    def _guard(self, fn, *args) -> None:
        """Falha de I/O do rastreio (disco cheio, permissão...) nunca pode derrubar a requisição."""
        if time.monotonic() < self._retry_at:
            return
        try:
            fn(*args)
        except Exception as exc:
            self._retry_at = time.monotonic() + _RETRY_AFTER_SECONDS
            self.active = False
            if self._fh:
                with contextlib.suppress(Exception):
                    self._fh.close()
                self._fh = None
            log.error(
                f"Falha ao gravar o journal de requisições ({exc!r}); rastreio em disco pausado por "
                f"{_RETRY_AFTER_SECONDS}s. As requisições não foram afetadas."
            )

    def _over_threshold(self, factor: float = 1.0) -> bool:
        process_mb, system_pct = settings.REQUEST_TRACE_PROCESS_MB, settings.REQUEST_TRACE_RAM_PERCENT
        if process_mb and _ram_mb() >= process_mb * factor:
            return True
        return bool(system_pct and (_sys_health().get("ram_uso_percent") or 0) >= system_pct * factor)

    def check_ram(self) -> None:
        self._guard(self._check_ram)

    def _check_ram(self) -> None:
        now = time.monotonic()
        if now - self._last_check < _MIN_CHECK_INTERVAL:
            return
        self._last_check = now
        if not self.active and self._over_threshold():
            self._activate()
        elif self.active and not self._over_threshold(_HYSTERESIS):
            self._deactivate()

    def _activate(self) -> None:
        self.active = True
        self._rewrite()
        log.warning(
            f"RAM acima do limiar (processo>={settings.REQUEST_TRACE_PROCESS_MB}MB ou "
            f"sistema>={settings.REQUEST_TRACE_RAM_PERCENT}%): gravando as últimas "
            f"{self.ring.maxlen} requisições em {journal_path(os.getpid())}"
        )

    def _deactivate(self) -> None:
        self.active = False
        self._close_and_remove()
        log.info("RAM voltou ao normal: rastreio de requisições em disco desativado")

    def _close_and_remove(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None
        journal_path(os.getpid()).unlink(missing_ok=True)

    def _rewrite(self) -> None:
        JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        path = journal_path(os.getpid())
        tmp = path.with_suffix(".tmp")
        header = {"ev": "hdr", "pid": os.getpid(), "create_time": psutil.Process().create_time()}
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(header) + "\n")
            oldest_inflight = sorted(self.inflight.values(), key=lambda e: e["id"])[:_MAX_INFLIGHT]
            for entry in (*self.ring, *oldest_inflight):
                f.write(json.dumps({"ev": "start", **_public(entry)}, ensure_ascii=False) + "\n")
        if self._fh:
            self._fh.close()
        os.replace(tmp, path)
        self._fh = open(path, "a", encoding="utf-8")
        self._events = 0

    def _append(self, event: dict) -> None:
        if self._events >= self.ring.maxlen * _COMPACT_AFTER_RINGS:
            self._rewrite()
            return
        self._fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._fh.flush()
        self._events += 1

    def begin(self, method: str, path: str, query: str, body: bytes, body_size: int) -> dict:
        entry = {
            "id": next(self._ids),
            "at": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "method": method,
            "path": path,
            "query": query,
            "body": body.decode("utf-8", errors="replace") if body else "",
            "body_size": body_size,
            "status": None,
            "ms": None,
            "_t0": time.monotonic(),
        }
        self.inflight[entry["id"]] = entry
        self._guard(self._begin_io, entry)
        return entry

    def _begin_io(self, entry: dict) -> None:
        self._check_ram()
        if self.active:
            self._append({"ev": "start", **_public(entry)})

    def finish(self, entry: dict, status) -> None:
        entry["status"] = status
        entry["ms"] = round((time.monotonic() - entry["_t0"]) * 1000)
        self.inflight.pop(entry["id"], None)
        self.ring.append(entry)
        self._guard(self._finish_io, entry)

    def _finish_io(self, entry: dict) -> None:
        self._check_ram()
        if self.active:
            self._append({"ev": "end", "id": entry["id"], "status": entry["status"], "ms": entry["ms"]})

    def shutdown(self) -> None:
        with contextlib.suppress(OSError):
            self._close_and_remove()


tracer = _Tracer()


def shutdown() -> None:
    tracer.shutdown()


class RequestTraceMiddleware:
    """ASGI puro: o corpo é lido antes de chamar o app e reenviado intacto."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        max_body = settings.REQUEST_TRACE_MAX_BODY_KB * 1024
        buffered, kept, body_size = [], bytearray(), 0
        if method not in _BODYLESS_METHODS:
            while True:
                message = await receive()
                buffered.append(message)
                if message["type"] != "http.request":
                    break
                chunk = message.get("body", b"")
                body_size += len(chunk)
                if len(kept) < max_body:
                    kept += chunk[: max_body - len(kept)]
                if not message.get("more_body"):
                    break

        async def replay_receive():
            return buffered.pop(0) if buffered else await receive()

        entry = tracer.begin(
            method, scope["path"], scope.get("query_string", b"").decode("latin-1"), bytes(kept), body_size
        )
        status = None

        async def capture_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, replay_receive, capture_send)
        except BaseException:
            status = status or "exceção"
            raise
        finally:
            tracer.finish(entry, status if status is not None else "sem resposta")


def start_watchdog(interval_seconds: float | None = None) -> asyncio.Task:
    """Reavalia a RAM mesmo sem tráfego, para pegar crescimento no meio de uma requisição longa."""
    interval = interval_seconds or settings.REQUEST_TRACE_WATCHDOG_SECONDS

    async def _loop() -> None:
        while True:
            tracer.check_ram()
            await asyncio.sleep(interval)

    return asyncio.create_task(_loop())


def _read_journal(path: Path) -> list[dict]:
    entries = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue  # linha cortada pelo SIGKILL no meio da escrita
            if not isinstance(ev, dict):
                continue
            kind, entry_id = ev.pop("ev", None), ev.get("id")
            if kind == "start" and entry_id is not None:
                entries[entry_id] = ev
            elif kind == "end" and entry_id in entries:
                entries[entry_id].update(status=ev.get("status"), ms=ev.get("ms"))
    in_flight = [e for e in entries.values() if e.get("status") is None][:_MAX_INFLIGHT]
    completed = [e for e in entries.values() if e.get("status") is not None]
    return in_flight + completed[-max(1, settings.REQUEST_TRACE_SIZE):]


def _format_report(entries: list[dict]) -> str:
    in_flight = sum(1 for e in entries if e.get("status") is None)
    lines = [f"{len(entries)} requisições registradas ({in_flight} ainda em andamento quando o processo morreu, listadas primeiro):"]
    for e in entries:
        outcome = "EM ANDAMENTO" if e.get("status") is None else f"{e['status']} | {e['ms']}ms"
        target = e["path"] + (f"?{e['query']}" if e.get("query") else "")
        lines.append(f"[{outcome}] {e['at']} {e['method']} {target}")
        if e.get("body_size"):
            shown = len(e["body"].encode("utf-8"))
            truncated = f" (truncado: exibindo {shown} de {e['body_size']} bytes)" if shown < e["body_size"] else ""
            lines.append(f"  corpo ({e['body_size']} bytes){truncated}: {e['body']}")
    return "\n".join(lines)


def dump_journal(pid: int, reason: str) -> bool:
    """
    Despeja o journal de `pid` no log de erros. Retorna False se não havia journal.
    Nunca levanta exceção: roda no arbiter do gunicorn (sem proteção contra erro em hook)
    e no startup, onde uma falha derrubaria o serviço inteiro por causa de um arquivo de diagnóstico.
    """
    path = journal_path(pid)
    claimed = path.with_suffix(f".claimed-{os.getpid()}")
    try:
        os.rename(path, claimed)  # atômico: se dois processos tentarem, só um leva
    except FileNotFoundError:
        return False
    except OSError as exc:
        log.error(f"{reason}\nNão foi possível ler o journal de requisições: {exc!r}")
        return True
    try:
        report = _format_report(_read_journal(claimed))
    except Exception as exc:
        report = f"Journal de requisições ilegível ({exc!r}); descartado."
    finally:
        with contextlib.suppress(OSError):
            claimed.unlink(missing_ok=True)
    log.error(f"{reason}\n{report}")
    return True


def _is_alive(pid: int, create_time: float | None) -> bool:
    try:
        return create_time is not None and abs(psutil.Process(pid).create_time() - create_time) < 1
    except psutil.Error:
        return False


def _recover_one(path: Path) -> None:
    if not path.stem.isdigit():
        return
    try:
        with open(path, encoding="utf-8") as f:
            header = json.loads(f.readline())
        create_time = header.get("create_time") if isinstance(header, dict) else None
    except (ValueError, OSError):
        create_time = None
    if _is_alive(int(path.stem), create_time):
        return
    dump_journal(
        int(path.stem),
        f"Processo PID {path.stem} terminou sem encerrar normalmente com a RAM acima do limiar "
        "(provável OOM Killer/SIGKILL).",
    )


def recover_orphans() -> None:
    """Despeja journals de processos que morreram sem que o gunicorn (ou ninguém) os tenha lido."""
    try:
        paths = list(JOURNAL_DIR.glob("*.jsonl"))
    except OSError:
        return
    for path in paths:
        try:
            _recover_one(path)
        except Exception as exc:
            log.warning(f"Journal órfão {path.name} ignorado: {exc!r}")
