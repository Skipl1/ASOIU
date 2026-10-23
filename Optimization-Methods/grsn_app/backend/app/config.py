"""Настройки приложения. Значения читаются из переменных окружения и файла .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR.parent / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "АС ГРСН"
    app_timezone: str = "Europe/Moscow"
    database_url: str = "postgresql+psycopg://grsn:grsn_dev_pass@localhost:5433/grsn"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Безопасность (ТЗ 4.3)
    jwt_secret: str = "dev-secret-change-me-please-32-bytes-min"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # Генерация рецептов
    llm_provider: str = "gigachat"  # gigachat | mock
    llm_fallback_to_mock: bool = True
    llm_timeout_seconds: float = 25.0
    llm_max_concurrency: int = 1  # Freemium GigaChat: один поток
    llm_queue_wait_seconds: float = 30.0
    llm_temperature: float = 0.4

    gigachat_credentials: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-2"
    gigachat_ca_bundle_file: str | None = str(BASE_DIR / "certs" / "russian_trusted_root_ca.crt")
    gigachat_verify_ssl_certs: bool = True
    gigachat_use_json_schema: bool = True
    gigachat_keepalive_seconds: int = 30  # 0 — без фонового прогрева соединения

    # Хранилища
    storage_dir: str = str(BASE_DIR / "storage")
    backup_dir: str = str(BASE_DIR / "storage" / "backups")
    backup_retention_days: int = 30
    pg_dump_path: str = "pg_dump"
    pg_restore_path: str = "pg_restore"
    pdf_font_path: str | None = None

    # Начальное наполнение
    admin_email: str = "admin@grsn.local"
    admin_password: str = "Admin12345"
    admin_name: str = "Администратор"
    seed_demo: bool = True

    @property
    def reports_dir(self) -> Path:
        return Path(self.storage_dir) / "reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
