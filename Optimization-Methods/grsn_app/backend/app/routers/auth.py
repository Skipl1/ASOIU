from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.config import get_settings
from app.db import get_db
from app.deps import client_ip, get_current_user
from app.models import User, as_utc, utcnow
from app.security import create_access_token, hash_password, validate_password_strength, verify_password
from app.services.audit import log_action
from app.services.serializers import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(user: User) -> schemas.AuthResponse:
    token, expires_in = create_access_token(user.user_id, user.role, user.token_version)
    return schemas.AuthResponse(access_token=token, expires_in=expires_in, user=user_out(user))


@router.post("/register", response_model=schemas.AuthResponse, status_code=status.HTTP_201_CREATED,
             summary="Регистрация пользователя",
             responses={409: {"description": "E-mail уже зарегистрирован"}})
def register(body: schemas.RegisterRequest, request: Request, db: Session = Depends(get_db)):
    error = validate_password_strength(body.password)
    if error:
        raise HTTPException(422, detail=error)
    email = body.email.lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Пользователь с таким e-mail уже зарегистрирован")
    user = User(name=body.name, email=email, password_hash=hash_password(body.password), last_login_at=utcnow())
    db.add(user)
    db.flush()
    log_action(db, "register", user.user_id, ip=client_ip(request))
    db.commit()
    return _auth_response(user)


@router.post("/login", response_model=schemas.AuthResponse, summary="Авторизация пользователя",
             responses={401: {"description": "Неверный логин или пароль"}, 423: {"description": "Вход временно заблокирован"}})
def login(body: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    ip = client_ip(request)
    email = body.email.lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    now = utcnow()

    if user is None or user.status == "deleted":
        log_action(db, "login_failed", None, details={"email": email, "reason": "unknown_email"}, ip=ip, commit=True)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Неверный e-mail или пароль")

    locked_until = as_utc(user.locked_until)
    if locked_until and locked_until > now:
        minutes = max(1, int((locked_until - now).total_seconds() // 60) + 1)
        raise HTTPException(
            status.HTTP_423_LOCKED,
            detail=f"Слишком много неудачных попыток входа. Повторите через {minutes} мин. "
                   f"(в {locked_until.astimezone(ZoneInfo(settings.app_timezone)).strftime('%H:%M')})",
        )

    if not verify_password(body.password, user.password_hash):
        user.failed_login_count += 1
        details = {"email": email, "attempt": user.failed_login_count}
        if user.failed_login_count >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_count = 0
            log_action(db, "login_locked", user.user_id, details=details, ip=ip, commit=True)
            raise HTTPException(
                status.HTTP_423_LOCKED,
                detail=f"Превышено число попыток входа ({settings.max_failed_logins}). "
                       f"Вход заблокирован на {settings.lockout_minutes} минут",
            )
        log_action(db, "login_failed", user.user_id, details=details, ip=ip, commit=True)
        left = settings.max_failed_logins - user.failed_login_count
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=f"Неверный e-mail или пароль. Осталось попыток: {left}")

    if user.status == "blocked":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Учётная запись заблокирована администратором")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    log_action(db, "login_success", user.user_id, ip=ip)
    db.commit()
    return _auth_response(user)


@router.post("/refresh", response_model=schemas.AuthResponse, summary="Продление сессии активного пользователя")
def refresh(user: User = Depends(get_current_user)):
    return _auth_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Завершение пользовательской сессии")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1  # все выданные ранее токены становятся недействительными
    log_action(db, "logout", user.user_id, ip=client_ip(request))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=schemas.UserOut, summary="Текущий пользователь")
def me(user: User = Depends(get_current_user)):
    return user_out(user)
