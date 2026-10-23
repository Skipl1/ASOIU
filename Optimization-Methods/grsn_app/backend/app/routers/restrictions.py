import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, get_current_user
from app.models import Allergen, AvailableIngredient, Ingredient, User, UserRestriction
from app.services.audit import log_action
from app.services.restrictions import (
    check_ingredient,
    effective_allergens,
    find_matches,
    load_forbidden,
    normalize_text,
    resolve_unique,
)
from app.services.serializers import restriction_out

router = APIRouter(prefix="/restrictions", tags=["restrictions"])


def _candidate_out(m) -> schemas.MatchCandidateOut:
    return schemas.MatchCandidateOut(type=m.type, id=m.id, name=m.name, matched_by=m.matched_by, exact=m.score == 3)


@router.get("", response_model=list[schemas.UserRestrictionOut], summary="Запреты текущего пользователя")
def list_restrictions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(UserRestriction).where(UserRestriction.user_id == user.user_id).order_by(UserRestriction.created_at))
    return [restriction_out(r) for r in rows]


@router.get("/match", response_model=schemas.MatchResult, summary="Нормализация ввода и поиск соответствий в справочниках")
def match(q: str = Query(min_length=1, max_length=160), _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    matches = find_matches(db, q)
    unique = resolve_unique(matches)
    return schemas.MatchResult(
        query=q,
        normalized=normalize_text(q),
        unique=_candidate_out(unique) if unique else None,
        candidates=[_candidate_out(m) for m in matches],
    )


@router.post("", response_model=schemas.UserRestrictionOut, status_code=status.HTTP_201_CREATED, summary="Добавить запрет пользователя",
             responses={409: {"description": "Неоднозначное соответствие — требуется выбор из вариантов"}})
def add_restriction(body: schemas.RestrictionCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.ingredient_id and body.allergen_id:
        raise HTTPException(422, detail="Укажите либо ингредиент, либо аллерген")
    normalized = normalize_text(body.source_text)
    if not normalized:
        raise HTTPException(422, detail="Название запрета не может быть пустым")

    ingredient_id, allergen_id, kind = body.ingredient_id, body.allergen_id, None
    if ingredient_id:
        if db.get(Ingredient, ingredient_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ингредиент не найден")
        kind = "ingredient"
    elif allergen_id:
        if db.get(Allergen, allergen_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Аллерген не найден")
        kind = "allergen"
    elif body.as_substance:
        kind = "substance"
    else:
        matches = find_matches(db, body.source_text)
        unique = resolve_unique(matches)
        if unique is None and matches:
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={
                "detail": "Найдено несколько соответствий — выберите вариант",
                "candidates": [_candidate_out(m).model_dump(mode="json", by_alias=True) for m in matches],
            })
        if unique is None:
            kind = "substance"  # нет в справочниках — контроль по названию
        elif unique.type == "ingredient":
            ingredient_id, kind = unique.id, "ingredient"
        else:
            allergen_id, kind = unique.id, "allergen"

    existing = db.scalar(select(UserRestriction).where(
        UserRestriction.user_id == user.user_id,
        UserRestriction.restriction_type == kind,
        UserRestriction.ingredient_id == ingredient_id if ingredient_id else UserRestriction.ingredient_id.is_(None),
        UserRestriction.allergen_id == allergen_id if allergen_id else UserRestriction.allergen_id.is_(None),
        *( [UserRestriction.normalized_name == normalized] if kind == "substance" else [] ),
    ))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Такой запрет уже есть в списке")

    restriction = UserRestriction(
        user_id=user.user_id,
        ingredient_id=ingredient_id,
        allergen_id=allergen_id,
        original_name=body.source_text.strip(),
        normalized_name=normalized,
        restriction_type=kind,
    )
    db.add(restriction)
    log_action(db, "restriction_add", user.user_id, entity="user_restrictions", details={"text": body.source_text, "type": kind}, ip=client_ip(request))
    db.commit()
    db.refresh(restriction)
    return restriction_out(restriction)


@router.delete("/{restriction_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить запрет пользователя")
def delete_restriction(restriction_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    restriction = db.get(UserRestriction, restriction_id)
    if restriction is None or restriction.user_id != user.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Запрет не найден")
    db.delete(restriction)
    log_action(db, "restriction_delete", user.user_id, entity="user_restrictions", entity_id=restriction_id,
               details={"text": restriction.original_name}, ip=client_ip(request))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Очистить список запретов")
def clear_restrictions(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for r in db.scalars(select(UserRestriction).where(UserRestriction.user_id == user.user_id)):
        db.delete(r)
    log_action(db, "restriction_delete", user.user_id, details={"all": True}, ip=client_ip(request))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/check-available", response_model=list[schemas.AvailableCheckItem], summary="Проверка выбранного набора ингредиентов перед генерацией")
def check_available(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    forbidden = load_forbidden(db, user.user_id)
    rows = db.scalars(select(AvailableIngredient).where(AvailableIngredient.user_id == user.user_id))
    result = []
    for a in sorted(rows, key=lambda a: a.ingredient.name):
        reasons = check_ingredient(a.ingredient, forbidden)
        result.append(schemas.AvailableCheckItem(
            ingredient_id=a.ingredient_id,
            name=a.ingredient.name,
            allergens=[x.name for x in effective_allergens(a.ingredient)],
            result="excluded" if reasons else "allowed",
            reasons=reasons,
        ))
    return result
