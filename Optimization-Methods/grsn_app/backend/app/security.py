"""Хеширование паролей (bcrypt) и JWT-токены (ТЗ 4.3)."""

import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72  # ограничение алгоритма bcrypt


def validate_password_strength(password: str) -> str | None:
    """Возвращает текст ошибки или None, если пароль удовлетворяет требованиям."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Пароль должен содержать не менее {PASSWORD_MIN_LENGTH} символов"
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return "Пароль слишком длинный"
    if not re.search(r"[A-Za-zА-Яа-яЁё]", password) or not re.search(r"\d", password):
        return "Пароль должен содержать буквы и цифры"
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:PASSWORD_MAX_BYTES], password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, role: str, token_version: int) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_in = settings.access_token_minutes * 60
    payload = {
        "sub": str(user_id),
        "role": role,
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], options={"require": ["exp", "sub"]})
