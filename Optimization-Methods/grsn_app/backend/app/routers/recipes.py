import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, get_current_user
from app.models import RECIPE_ACCEPTED, RECIPE_GENERATED, Ingredient, Recipe, RecipeIngredient, RecipeRating, User, utcnow
from app.services import nutrition
from app.services.audit import log_action
from app.services.generation import generate_recipes
from app.services.reports import recipes_in_period
from app.services.restrictions import check_ingredients, load_forbidden, normalize_text
from app.services.serializers import recipe_out, recipe_summary

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _own_recipe(db: Session, recipe_id: uuid.UUID, user: User) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or recipe.user_id != user.user_id:  # доступ только к собственной истории
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Рецепт не найден")
    return recipe


@router.post("/generate", response_model=schemas.GenerateRecipeResponse, status_code=status.HTTP_201_CREATED,
             summary="Сгенерировать персонализированный рецепт")
def generate(body: schemas.GenerateRecipeRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    outcome = generate_recipes(db, user, body.goal_id, body.variants_count, body.meal_share, body.difficulty, body.comment,
                               meal_type=body.meal_type)
    req = outcome.request
    forbidden = load_forbidden(db, user.user_id)
    log_action(db, "recipe_generate", user.user_id, entity="generation_requests", entity_id=req.generation_request_id,
               details={"status": req.status, "provider": req.provider, "durationMs": req.duration_ms,
                        "recipes": len(outcome.recipes)}, ip=client_ip(request), commit=True)
    return schemas.GenerateRecipeResponse(
        request_id=req.generation_request_id,
        status="generated" if req.status == "completed" else "failed",
        provider=req.provider,
        duration_ms=req.duration_ms,
        recipes=[recipe_out(r, user.user_id, forbidden) for r in outcome.recipes],
        failure_reason=req.rejection_reason,
        conflicts=list(dict.fromkeys(req.conflicts or [])),
        recommended_ingredients=req.recommended_ingredients or [],
        suggestions=outcome.suggestions,
        warnings=outcome.warnings,
    )


@router.get("", response_model=list[schemas.RecipeSummary], summary="История рецептов пользователя")
def history(
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    goal_id: uuid.UUID | None = Query(default=None, alias="goalId"),
    in_diet: bool | None = Query(default=None, alias="inDiet"),
    search: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if date_from or date_to:
        recipes = recipes_in_period(db, user.user_id, date_from or date(2000, 1, 1), date_to or date(2100, 1, 1), goal_id, only_diet=False)
        recipes.reverse()
    else:
        stmt = select(Recipe).where(Recipe.user_id == user.user_id)
        if goal_id:
            stmt = stmt.where(Recipe.fitness_goal_id == goal_id)
        recipes = list(db.scalars(stmt.order_by(Recipe.created_at.desc())))
    if in_diet is not None:
        recipes = [r for r in recipes if (r.generation_status == RECIPE_ACCEPTED) == in_diet]
    if search:
        q = normalize_text(search)
        recipes = [r for r in recipes if q in normalize_text(r.name)]
    forbidden = load_forbidden(db, user.user_id)
    return [recipe_summary(r, user.user_id, forbidden) for r in recipes]


@router.get("/{recipe_id}", response_model=schemas.RecipeOut, summary="Подробная карточка рецепта")
def card(recipe_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return recipe_out(_own_recipe(db, recipe_id, user), user.user_id, load_forbidden(db, user.user_id))


@router.patch("/{recipe_id}", response_model=schemas.RecipeOut, summary="Редактировать сохранённый рецепт")
def edit(recipe_id: uuid.UUID, body: schemas.RecipeUpdate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = _own_recipe(db, recipe_id, user)
    if body.name is not None:
        recipe.name = body.name.strip()
    if body.servings is not None:
        recipe.servings = body.servings
    if body.instructions is not None:
        steps = [s.strip() for s in body.instructions if s.strip()]
        if len(steps) < 3:
            raise HTTPException(422, detail="Инструкция должна содержать не менее трёх шагов")
        recipe.cooking_instruction = steps
    forbidden = load_forbidden(db, user.user_id)
    if body.ingredients is not None:
        ids = [i.ingredient_id for i in body.ingredients]
        if len(ids) != len(set(ids)):
            raise HTTPException(422, detail="Ингредиенты в рецепте повторяются")
        found = {i.ingredient_id: i for i in db.scalars(select(Ingredient).where(Ingredient.ingredient_id.in_(ids)))}
        if len(found) != len(ids):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Некоторые ингредиенты не найдены в каталоге")
        ok, reasons = check_ingredients(list(found.values()), forbidden)
        if not ok:
            raise HTTPException(422, detail="Рецепт нарушает запреты: " + "; ".join(reasons))
        recipe.items.clear()
        db.flush()
        recipe.items = [
            RecipeIngredient(ingredient_id=i.ingredient_id, ingredient=found[i.ingredient_id], mass_g=i.mass_g, list_order=n)
            for n, i in enumerate(body.ingredients, start=1)
        ]
        totals = nutrition.recipe_totals([
            nutrition.NutrientRow(i.mass_g, found[i.ingredient_id].protein_per_100g, found[i.ingredient_id].fat_per_100g,
                                  found[i.ingredient_id].carb_per_100g, found[i.ingredient_id].calories_per_100g)
            for i in body.ingredients
        ])
        recipe.protein_total_g = round(totals.protein, 1)
        recipe.fat_total_g = round(totals.fat, 1)
        recipe.carb_total_g = round(totals.carbs, 1)
        recipe.calories_kcal = round(totals.calories, 1)
        recipe.matches_restrictions, recipe.mismatch_reasons = True, []
    recipe.updated_at = utcnow()
    log_action(db, "recipe_update", user.user_id, entity="recipes", entity_id=recipe_id, ip=client_ip(request))
    db.commit()
    db.refresh(recipe)
    return recipe_out(recipe, user.user_id, forbidden)


def _set_diet(db: Session, recipe_id: uuid.UUID, user: User, request: Request, accepted: bool) -> schemas.RecipeOut:
    recipe = _own_recipe(db, recipe_id, user)
    recipe.generation_status = RECIPE_ACCEPTED if accepted else RECIPE_GENERATED
    log_action(db, "recipe_diet_add" if accepted else "recipe_diet_remove", user.user_id, entity="recipes",
               entity_id=recipe_id, details={"name": recipe.name}, ip=client_ip(request))
    db.commit()
    return recipe_out(recipe, user.user_id, load_forbidden(db, user.user_id))


@router.post("/{recipe_id}/diet", response_model=schemas.RecipeOut, summary="Добавить рецепт в рацион (учитывается в отчётах и анализе)")
def add_to_diet(recipe_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = _own_recipe(db, recipe_id, user)
    forbidden = load_forbidden(db, user.user_id)
    ok, reasons = check_ingredients([i.ingredient for i in recipe.items], forbidden)
    if not ok:  # рецепт мог стать недопустимым после добавления новых запретов
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Рецепт нарушает текущие запреты: " + "; ".join(reasons))
    return _set_diet(db, recipe_id, user, request, accepted=True)


@router.delete("/{recipe_id}/diet", response_model=schemas.RecipeOut, summary="Убрать рецепт из рациона (останется в истории)")
def remove_from_diet(recipe_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _set_diet(db, recipe_id, user, request, accepted=False)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить рецепт из истории")
def remove(recipe_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own_recipe(db, recipe_id, user))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{recipe_id}/rating", response_model=schemas.RatingOut, status_code=status.HTTP_201_CREATED, summary="Сохранить оценку рецепта")
def rate(recipe_id: uuid.UUID, body: schemas.RatingCreate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipe = _own_recipe(db, recipe_id, user)
    rating = db.scalar(select(RecipeRating).where(RecipeRating.recipe_id == recipe.recipe_id, RecipeRating.user_id == user.user_id))
    if rating is None:
        rating = RecipeRating(recipe_id=recipe.recipe_id, user_id=user.user_id, score=body.score)
        db.add(rating)
    rating.score = body.score
    rating.comment = (body.comment or "").strip() or None
    rating.rated_at = utcnow()
    log_action(db, "recipe_rate", user.user_id, entity="recipes", entity_id=recipe_id, details={"score": body.score}, ip=client_ip(request))
    db.commit()
    return schemas.RatingOut(id=rating.rating_id, recipe_id=recipe.recipe_id, score=rating.score, comment=rating.comment, created_at=rating.rated_at)
