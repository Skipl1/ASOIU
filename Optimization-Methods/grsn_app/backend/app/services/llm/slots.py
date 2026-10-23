"""Ограничение числа одновременных обращений к модели генерации.

Freemium-тариф GigaChat допускает один поток. Backend запускается в нескольких процессах
(uvicorn --workers), поэтому лимит обеспечивается рекомендательной блокировкой PostgreSQL
(pg_try_advisory_lock), общей для всех процессов и контейнеров. Для SQLite (автотесты)
используется обычный семафор процесса.
"""

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text

from app.db import engine
from app.services.llm.base import LLMBusyError

LOCK_BASE_KEY = 742_001  # произвольный ключ приложения для advisory lock
_local_semaphores: dict[int, threading.BoundedSemaphore] = {}
_local_guard = threading.Lock()


@contextmanager
def llm_slot(max_concurrency: int, wait_seconds: float) -> Iterator[None]:
    slots = max(1, max_concurrency)
    if engine.dialect.name != "postgresql":
        with _local_guard:
            semaphore = _local_semaphores.setdefault(slots, threading.BoundedSemaphore(slots))
        if not semaphore.acquire(timeout=wait_seconds):
            raise LLMBusyError("Модель генерации занята, повторите запрос позже")
        try:
            yield
        finally:
            semaphore.release()
        return

    conn = engine.connect()
    key = None
    try:
        deadline = time.monotonic() + wait_seconds
        while key is None:
            for candidate in range(LOCK_BASE_KEY, LOCK_BASE_KEY + slots):
                if conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": candidate}).scalar():
                    key = candidate
                    break
            if key is None:
                if time.monotonic() > deadline:
                    raise LLMBusyError("Модель генерации занята другими запросами, повторите позже")
                time.sleep(0.25)
        conn.commit()
        yield
    finally:
        if key is not None:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            conn.commit()
        conn.close()
