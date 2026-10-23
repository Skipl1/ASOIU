import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthorized("Требуется авторизация")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Сессия истекла, войдите снова")
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauthorized("Недействительный токен")

    user = db.get(User, user_id)
    if user is None or user.status == "deleted":
        raise _unauthorized("Учётная запись не найдена")
    if user.status == "blocked":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Учётная запись заблокирована администратором")
    if payload.get("ver") != user.token_version:
        raise _unauthorized("Сессия завершена, войдите снова")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Операция доступна только администратору")
    return user


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
