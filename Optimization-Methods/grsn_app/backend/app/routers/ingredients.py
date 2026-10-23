import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, get_current_user
from app.models import Allergen, AvailableIngredient, Ingredient, IngredientCategory, User, utcnow
from app.services.audit import log_action
from app.services.restrictions import check_ingredients, load_forbidden, normalize_text
from app.services.serializers import ingredient_out

router = APIRouter(tags=["ingredients"])


@router.get("/ingredients", response_model=list[schemas.IngredientOut], summary="Каталог ингредиентов с фильтрацией")
def catalog(
    search: str | None = None,
    category_id: uuid.UUID | None = Query(default=None, alias="categoryId"),
    allowed_only: bool = Query(default=False, alias="allowedOnly"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Ingredient).order_by(Ingredient.name)
    if category_id:
        stmt = stmt.where(Ingredient.category_id == category_id)
    items = list(db.scalars(stmt).unique())
    if search:
        q = normalize_text(search)
        items = [i for i in items if q in normalize_text(i.name) or any(q in normalize_text(s) for s in (i.name_synonyms or []))]
    forbidden = load_forbidden(db, user.user_id)
    result = [ingredient_out(i, forbidden) for i in items]
    if allowed_only:
        result = [i for i in result if i.is_allowed]
    return result


@router.get("/ingredients/{ingredient_id}", response_model=schemas.IngredientOut, summary="Карточка ингредиента")
def ingredient_card(ingredient_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ингредиент не найден")
    return ingredient_out(ingredient, load_forbidden(db, user.user_id))


@router.get("/categories", response_model=list[schemas.CategoryOut], summary="Справочник категорий ингредиентов")
def categories(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Ingredient.category_id, func.count()).group_by(Ingredient.category_id)).all())
    return [
        schemas.CategoryOut(id=c.category_id, code=c.code, name=c.name, description=c.description, ingredients_count=counts.get(c.category_id, 0))
        for c in db.scalars(select(IngredientCategory).order_by(IngredientCategory.name))
    ]


@router.get("/allergens", response_model=list[schemas.AllergenOut], summary="Справочник аллергенов")
def allergens(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [
        schemas.AllergenOut(id=a.allergen_id, code=a.code, name=a.name, description=a.description, synonyms=list(a.synonyms or []))
        for a in db.scalars(select(Allergen).order_by(Allergen.name))
    ]


def _available_out(rows: list[AvailableIngredient], forbidden) -> list[schemas.AvailableIngredientOut]:
    return [
        schemas.AvailableIngredientOut(
            ingredient_id=a.ingredient_id,
            available_qty_g=a.available_amount_g,
            ingredient=ingredient_out(a.ingredient, forbidden),
            updated_at=a.updated_at,
        )
        for a in sorted(rows, key=lambda a: a.ingredient.name)
    ]


@router.get("/available-ingredients", response_model=list[schemas.AvailableIngredientOut], summary="Доступные ингредиенты пользователя")
def get_available(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(AvailableIngredient).where(AvailableIngredient.user_id == user.user_id)))
    return _available_out(rows, load_forbidden(db, user.user_id))


@router.put("/available-ingredients", response_model=list[schemas.AvailableIngredientOut], summary="Обновить набор доступных ингредиентов")
def put_available(body: schemas.AvailableIngredientsUpdate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = [i.ingredient_id for i in body.items]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, detail="Ингредиенты в наборе повторяются")
    found = {i.ingredient_id: i for i in db.scalars(select(Ingredient).where(Ingredient.ingredient_id.in_(ids)))} if ids else {}
    missing = [str(i) for i in ids if i not in found]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Ингредиенты не найдены: {', '.join(missing)}")
    forbidden = load_forbidden(db, user.user_id)
    rejected = [found[i].name for i in ids if not check_ingredients([found[i]], forbidden)[0]]
    if rejected:
        raise HTTPException(422,
                            detail="Запрещённые ингредиенты нельзя добавить в набор: " + ", ".join(rejected))

    db.execute(delete(AvailableIngredient).where(AvailableIngredient.user_id == user.user_id))
    now = utcnow()
    for item in body.items:
        db.add(AvailableIngredient(user_id=user.user_id, ingredient_id=item.ingredient_id,
                                   available_amount_g=item.available_qty_g, updated_at=now))
    log_action(db, "available_update", user.user_id, details={"count": len(ids)}, ip=client_ip(request))
    db.commit()
    rows = list(db.scalars(select(AvailableIngredient).where(AvailableIngredient.user_id == user.user_id)))
    return _available_out(rows, forbidden)
