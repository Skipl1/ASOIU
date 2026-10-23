"""Резервное копирование и восстановление PostgreSQL штатными утилитами pg_dump / pg_restore (ТЗ 4.3)."""

import logging
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import SessionLocal, engine
from app.services.audit import log_action

logger = logging.getLogger("grsn.backup")

FILE_RE = re.compile(r"^grsn_[0-9]{8}_[0-9]{6}(_manual|_auto)?\.dump$")


class BackupError(Exception):
    pass


def backup_dir() -> Path:
    path = Path(get_settings().backup_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pg_args() -> tuple[list[str], dict]:
    settings = get_settings()
    url = make_url(settings.owner_database_url or settings.database_url)
    if not url.drivername.startswith("postgresql"):
        raise BackupError("Резервное копирование поддерживается только для PostgreSQL")
    args = ["-h", url.host or "localhost", "-p", str(url.port or 5432), "-U", url.username or "postgres"]
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    return args + ["-d", url.database or "postgres"], env


def _binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise BackupError(f"Утилита {name} не найдена. Установите клиент PostgreSQL или задайте путь в настройках")
    return path


def list_backups() -> list[dict]:
    items = []
    for f in sorted(backup_dir().glob("grsn_*.dump"), reverse=True):
        stat = f.stat()
        items.append({
            "file_name": f.name,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        })
    return items


def cleanup_old() -> int:
    limit = datetime.now(timezone.utc) - timedelta(days=get_settings().backup_retention_days)
    removed = 0
    for item in list_backups():
        if item["created_at"] < limit:
            (backup_dir() / item["file_name"]).unlink(missing_ok=True)
            removed += 1
    return removed


def new_backup_name(kind: str = "manual") -> str:
    return f"grsn_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{kind}.dump"


def create_backup(file_name: str, user_id: uuid.UUID | None = None) -> Path:
    settings = get_settings()
    args, env = _pg_args()
    target = backup_dir() / file_name
    cmd = [_binary(settings.pg_dump_path), *args, "-Fc", "-f", str(target)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
    with SessionLocal() as db:
        if result.returncode != 0:
            target.unlink(missing_ok=True)
            log_action(db, "backup_create", user_id, details={"file": file_name, "status": "error", "error": result.stderr[-500:]}, commit=True)
            raise BackupError(result.stderr.strip() or "pg_dump завершился с ошибкой")
        removed = cleanup_old()
        log_action(db, "backup_create", user_id, details={"file": file_name, "status": "ok",
                                                          "sizeBytes": target.stat().st_size, "removedOld": removed}, commit=True)
    return target


def run_backup_task(file_name: str, user_id: uuid.UUID | None) -> None:
    try:
        create_backup(file_name, user_id)
    except Exception:  # фоновая задача: ошибка уже записана в журнал
        logger.exception("Ошибка резервного копирования")


def restore_backup(file_name: str, user_id: uuid.UUID | None = None) -> None:
    if not FILE_RE.match(file_name):
        raise BackupError("Некорректное имя файла резервной копии")
    source = backup_dir() / file_name
    if not source.exists():
        raise BackupError("Файл резервной копии не найден")
    settings = get_settings()
    args, env = _pg_args()
    engine.dispose()  # закрываем пул соединений приложения перед восстановлением
    cmd = [_binary(settings.pg_restore_path), *args, "--clean", "--if-exists", "--no-owner", "--single-transaction", str(source)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
    with SessionLocal() as db:
        ok = result.returncode == 0
        log_action(db, "backup_restore", user_id, details={"file": file_name, "status": "ok" if ok else "error",
                                                           "error": None if ok else result.stderr[-500:]}, commit=True)
    if result.returncode != 0:
        raise BackupError(result.stderr.strip() or "pg_restore завершился с ошибкой")
