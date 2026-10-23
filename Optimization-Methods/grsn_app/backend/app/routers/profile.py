from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, get_current_user
from app.models import FitnessGoal, ParameterHistory, User, UserProfile
from app.services.audit import log_action
from app.services.nutrition import ACTIVITY_LEVELS
from app.services.profile import get_profile, profile_out
from app.services.serializers import goal_out

router = APIRouter(tags=["profile"])


@router.get("/profile", response_model=schemas.ProfileOut, summary="Получить профиль текущего пользователя")
def read_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return profile_out(user.user_id, get_profile(db, user.user_id))


@router.put("/profile", response_model=schemas.ProfileOut, summary="Обновить профиль и текущий фитнес-ориентир")
def update_profile(body: schemas.ProfileUpdate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.get(FitnessGoal, body.goal_id)
    if goal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Фитнес-ориентир не найден")
    profile = get_profile(db, user.user_id)
    params_changed = True
    if profile is None:
        profile = UserProfile(user_id=user.user_id)
        db.add(profile)
    else:
        params_changed = (profile.weight_kg, profile.height_cm, profile.age, profile.activity_level) != (
            body.weight_kg, body.height_cm, body.age, body.activity_level)
    profile.weight_kg = body.weight_kg
    profile.height_cm = body.height_cm
    profile.age = body.age
    profile.sex = body.gender
    profile.activity_level = body.activity_level
    profile.fitness_goal_id = goal.fitness_goal_id
    profile.goal = goal
    if params_changed:  # каждое изменение параметров фиксируется в истории замеров
        db.add(ParameterHistory(user_id=user.user_id, weight_kg=body.weight_kg, height_cm=body.height_cm,
                                age=body.age, activity_level=body.activity_level))
    log_action(db, "profile_update", user.user_id, details={"goal": goal.code, "weightKg": body.weight_kg}, ip=client_ip(request))
    db.commit()
    db.refresh(profile)
    return profile_out(user.user_id, profile)


def _history_item(h: ParameterHistory) -> schemas.ParameterHistoryItem:
    return schemas.ParameterHistoryItem(id=h.record_id, weight_kg=h.weight_kg, height_cm=h.height_cm, age=h.age,
                                        activity_level=h.activity_level, recorded_at=h.recorded_at)


@router.get("/profile/parameter-history", response_model=list[schemas.ParameterHistoryItem], summary="История физических параметров")
def parameter_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(ParameterHistory).where(ParameterHistory.user_id == user.user_id).order_by(ParameterHistory.recorded_at.desc()))
    return [_history_item(h) for h in rows]


@router.post("/profile/parameter-history", response_model=schemas.ParameterHistoryItem, status_code=status.HTTP_201_CREATED,
             summary="Добавить замер физических параметров")
def add_parameter(body: schemas.ParameterHistoryCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = ParameterHistory(user_id=user.user_id, weight_kg=body.weight_kg, height_cm=body.height_cm, age=body.age,
                            activity_level=body.activity_level)
    db.add(item)
    profile = get_profile(db, user.user_id)
    if profile is not None:  # последний замер становится текущим значением профиля
        profile.weight_kg, profile.height_cm, profile.age, profile.activity_level = (
            body.weight_kg, body.height_cm, body.age, body.activity_level)
    log_action(db, "parameter_add", user.user_id, details={"weightKg": body.weight_kg}, ip=client_ip(request))
    db.commit()
    return _history_item(item)


@router.get("/goals", response_model=list[schemas.FitnessGoalOut], summary="Справочник фитнес-ориентиров")
def goals(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [goal_out(g) for g in db.scalars(select(FitnessGoal).order_by(FitnessGoal.sort_order, FitnessGoal.name))]


@router.get("/activity-levels", response_model=list[schemas.ActivityLevelOut], summary="Коэффициенты физической активности")
def activity_levels(_: User = Depends(get_current_user)):
    return [schemas.ActivityLevelOut(value=k, description=v) for k, v in ACTIVITY_LEVELS.items()]
