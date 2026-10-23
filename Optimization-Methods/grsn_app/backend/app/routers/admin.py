import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.deps import client_ip, require_admin
from app.models import (
    Allergen,
    AuditLog,
    Ingredient,
    IngredientCategory,
    Recipe,
    RecipeIngredient,
    User,
    UserRestriction,
    utcnow,
)
from app.services import backup as backup_service
from app.services.audit import ACTION_TITLES, log_action
from app.services.integrity import check_integrity
from app.services.serializers import ingredient_out

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------- пользователи ----------------

def _admin_user(u: User, recipes_count: int) -> schemas.AdminUserOut:
    return schemas.AdminUserOut(
        id=u.user_id, name=u.name, email=u.email, role=u.role, status=u.status, created_at=u.registered_at,
        last_login_at=u.last_login_at, recipes_count=recipes_count, failed_login_count=u.failed_login_count,
        locked_until=u.locked_until,
    )


def _recipe_counts(db: Session) -> dict:
    return dict(db.execute(select(Recipe.user_id, func.count()).group_by(Recipe.user_id)).all())


@router.get("/stats", response_model=schemas.AdminStats, summary="Сводные показатели системы")
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    issues = check_integrity(db)
    week_ago = utcnow() - timedelta(days=7)
    backups = backup_service.list_backups()
    return schemas.AdminStats(
        users=db.scalar(select(func.count()).select_from(User).where(User.status != "deleted")),
        active_users=db.scalar(select(func.count()).select_from(User).where(User.status == "active")),
        blocked_users=db.scalar(select(func.count()).select_from(User).where(User.status == "blocked")),
        ingredients=db.scalar(select(func.count()).select_from(Ingredient)),
        allergens=db.scalar(select(func.count()).select_from(Allergen)),
        categories=db.scalar(select(func.count()).select_from(IngredientCategory)),
        recipes=db.scalar(select(func.count()).select_from(Recipe)),
        data_errors=sum(1 for i in issues if i.severity == "error"),
        data_warnings=sum(1 for i in issues if i.severity == "warning"),
        failed_logins_7d=db.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.action.in_(["login_failed", "login_locked"]), AuditLog.created_at >= week_ago)),
        last_backup=backups[0]["created_at"] if backups else None,
    )


@router.get("/users", response_model=list[schemas.AdminUserOut], summary="Список пользователей")
def users(search: str | None = None, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(User).where(User.status != "deleted").order_by(User.registered_at)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.email).like(like), func.lower(User.name).like(like)))
    counts = _recipe_counts(db)
    return [_admin_user(u, counts.get(u.user_id, 0)) for u in db.scalars(stmt)]


@router.patch("/users/{user_id}", response_model=schemas.AdminUserOut, summary="Изменить роль или статус пользователя")
def update_user(user_id: uuid.UUID, body: schemas.AdminUserUpdate, request: Request,
                admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None or user.status == "deleted":
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if user.user_id == admin.user_id and ((body.status and body.status != "active") or body.role == "user"):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Нельзя заблокировать или лишить прав собственную учётную запись")
    changes = {}
    if body.role and body.role != user.role:
        changes["role"] = [user.role, body.role]
        user.role = body.role
    if body.status and body.status != user.status:
        changes["status"] = [user.status, body.status]
        user.status = body.status
        if body.status == "active":
            user.locked_until, user.failed_login_count = None, 0
    if changes:
        user.token_version += 1  # принудительное завершение сессий пользователя
    log_action(db, "admin_user_update", admin.user_id, entity="users", entity_id=user_id,
               details={"email": user.email, **changes}, ip=client_ip(request))
    db.commit()
    return _admin_user(user, _recipe_counts(db).get(user.user_id, 0))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить учётную запись пользователя")
def delete_user(user_id: uuid.UUID, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if user.user_id == admin.user_id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Нельзя удалить собственную учётную запись")
    email = user.email
    db.delete(user)
    log_action(db, "admin_user_delete", admin.user_id, entity="users", entity_id=user_id, details={"email": email}, ip=client_ip(request))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _log_out(entry: AuditLog, emails: dict) -> schemas.AuditLogOut:
    return schemas.AuditLogOut(
        id=entry.log_id, user_id=entry.user_id, user_email=emails.get(entry.user_id), action=entry.action,
        action_title=ACTION_TITLES.get(entry.action, entry.action), entity=entry.entity, entity_id=entry.entity_id,
        details=entry.details or {}, ip=entry.ip, created_at=entry.created_at,
    )


@router.get("/logs", response_model=list[schemas.AuditLogOut], summary="Журнал событий системы")
def logs(
    action: str | None = None,
    user_id: uuid.UUID | None = Query(default=None, alias="userId"),
    limit: int = Query(default=200, ge=1, le=1000),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditLog.action.in_(action.split(",")))
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    entries = list(db.scalars(stmt))
    emails = dict(db.execute(select(User.user_id, User.email)).all())
    return [_log_out(e, emails) for e in entries]


@router.get("/users/{user_id}/activity", response_model=list[schemas.AuditLogOut], summary="Активность пользователя")
def user_activity(user_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return logs(action=None, user_id=user_id, limit=100, _=admin, db=db)


# ---------------- справочники ----------------

def _unique_violation(db: Session, what: str):
    db.rollback()
    raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{what} с таким названием или кодом уже существует")


def _apply_ingredient(db: Session, ingredient: Ingredient, body: schemas.IngredientInput) -> None:
    if body.category_id and db.get(IngredientCategory, body.category_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    if body.protein100g + body.fat100g + body.carbs100g > 100:
        raise HTTPException(422, detail="Сумма белков, жиров и углеводов не может превышать 100 г")
    allergens = list(db.scalars(select(Allergen).where(Allergen.allergen_id.in_(body.allergen_ids)))) if body.allergen_ids else []
    if len(allergens) != len(set(body.allergen_ids)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Некоторые аллергены не найдены")
    components: list[Ingredient] = []
    if body.component_ids:
        if ingredient.ingredient_id in body.component_ids:
            raise HTTPException(422, detail="Ингредиент не может входить в собственный состав")
        components = list(db.scalars(select(Ingredient).where(Ingredient.ingredient_id.in_(body.component_ids))))
        if len(components) != len(set(body.component_ids)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Некоторые компоненты не найдены")

        def contains(node: Ingredient, target: uuid.UUID, depth: int = 0) -> bool:
            return depth < 6 and any(c.ingredient_id == target or contains(c, target, depth + 1) for c in node.components)

        if ingredient.ingredient_id and any(contains(c, ingredient.ingredient_id) for c in components):
            raise HTTPException(422, detail="Циклическая ссылка в составе ингредиента")

    ingredient.code = body.code or None
    ingredient.name = body.name.strip()
    ingredient.category_id = body.category_id
    ingredient.protein_per_100g = body.protein100g
    ingredient.fat_per_100g = body.fat100g
    ingredient.carb_per_100g = body.carbs100g
    ingredient.calories_per_100g = body.calories100g
    ingredient.is_composite = body.is_composite or bool(components)
    ingredient.name_synonyms = [s.strip() for s in body.synonyms if s.strip()]
    ingredient.composition_description = body.composition_description
    ingredient.allergens = allergens
    ingredient.components = components


@router.post("/ingredients", response_model=schemas.IngredientOut, status_code=status.HTTP_201_CREATED, summary="Добавить ингредиент в каталог")
def create_ingredient(body: schemas.IngredientInput, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    ingredient = Ingredient(ingredient_id=uuid.uuid4())
    _apply_ingredient(db, ingredient, body)
    db.add(ingredient)
    try:
        db.flush()
    except IntegrityError:
        _unique_violation(db, "Ингредиент")
    log_action(db, "admin_ingredient_create", admin.user_id, entity="ingredients", entity_id=ingredient.ingredient_id,
               details={"name": ingredient.name}, ip=client_ip(request))
    db.commit()
    db.refresh(ingredient)
    return ingredient_out(ingredient)


@router.put("/ingredients/{ingredient_id}", response_model=schemas.IngredientOut, summary="Изменить ингредиент")
def update_ingredient(ingredient_id: uuid.UUID, body: schemas.IngredientInput, request: Request,
                      admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ингредиент не найден")
    _apply_ingredient(db, ingredient, body)
    try:
        db.flush()
    except IntegrityError:
        _unique_violation(db, "Ингредиент")
    log_action(db, "admin_ingredient_update", admin.user_id, entity="ingredients", entity_id=ingredient_id,
               details={"name": ingredient.name}, ip=client_ip(request))
    db.commit()
    db.refresh(ingredient)
    return ingredient_out(ingredient)


@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить ингредиент")
def delete_ingredient(ingredient_id: uuid.UUID, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ингредиент не найден")
    used = db.scalar(select(func.count()).select_from(RecipeIngredient).where(RecipeIngredient.ingredient_id == ingredient_id))
    if used:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Ингредиент используется в сохранённых рецептах ({used}) — удаление невозможно")
    name = ingredient.name
    db.delete(ingredient)
    log_action(db, "admin_ingredient_delete", admin.user_id, entity="ingredients", entity_id=ingredient_id, details={"name": name}, ip=client_ip(request))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _allergen_out(a: Allergen) -> schemas.AllergenOut:
    return schemas.AllergenOut(id=a.allergen_id, code=a.code, name=a.name, description=a.description, synonyms=list(a.synonyms or []))


@router.post("/allergens", response_model=schemas.AllergenOut, status_code=status.HTTP_201_CREATED, summary="Добавить аллерген")
def create_allergen(body: schemas.AllergenInput, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    allergen = Allergen(code=body.code or None, name=body.name.strip(), description=body.description,
                        synonyms=[s.strip() for s in body.synonyms if s.strip()])
    db.add(allergen)
    try:
        db.flush()
    except IntegrityError:
        _unique_violation(db, "Аллерген")
    log_action(db, "admin_allergen_create", admin.user_id, entity="allergens", entity_id=allergen.allergen_id,
               details={"name": allergen.name}, ip=client_ip(request))
    db.commit()
    return _allergen_out(allergen)


@router.put("/allergens/{allergen_id}", response_model=schemas.AllergenOut, summary="Изменить аллерген")
def update_allergen(allergen_id: uuid.UUID, body: schemas.AllergenInput, request: Request,
                    admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    allergen = db.get(Allergen, allergen_id)
    if allergen is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Аллерген не найден")
    allergen.code, allergen.name, allergen.description = body.code or None, body.name.strip(), body.description
    allergen.synonyms = [s.strip() for s in body.synonyms if s.strip()]
    try:
        db.flush()
    except IntegrityError:
        _unique_violation(db, "Аллерген")
    log_action(db, "admin_allergen_update", admin.user_id, entity="allergens", entity_id=allergen_id, details={"name": allergen.name}, ip=client_ip(request))
    db.commit()
    return _allergen_out(allergen)


@router.delete("/allergens/{allergen_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить аллерген")
def delete_allergen(allergen_id: uuid.UUID, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    allergen = db.get(Allergen, allergen_id)
    if allergen is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Аллерген не найден")
    # Удаление снимет запрет у пользователей и «разрешит» продукты с этим аллергеном — не допускаем
    users_count = db.scalar(select(func.count(func.distinct(UserRestriction.user_id))).where(UserRestriction.allergen_id == allergen_id))
    if users_count:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail=f"Аллерген указан в запретах пользователей ({users_count}) — удаление невозможно, используйте редактирование")
    name = allergen.name
    db.delete(allergen)
    log_action(db, "admin_allergen_delete", admin.user_id, entity="allergens", entity_id=allergen_id, details={"name": name}, ip=client_ip(request))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _category_out(db: Session, c: IngredientCategory) -> schemas.CategoryOut:
    count = db.scalar(select(func.count()).select_from(Ingredient).where(Ingredient.category_id == c.category_id))
    return schemas.CategoryOut(id=c.category_id, code=c.code, name=c.name, description=c.description, ingredients_count=count)


@router.post("/categories", response_model=schemas.CategoryOut, status_code=status.HTTP_201_CREATED, summary="Добавить категорию ингредиентов")
def create_category(body: schemas.CategoryInput, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    category = IngredientCategory(code=body.code or None, name=body.name.strip(), description=body.description)
    db.add(category)
    try:
        db.flush()
    except IntegrityError:
        _unique_violation(db, "Категория")
    log_action(db, "admin_category_create", admin.user_id, entity="ingredient_categories", entity_id=category.category_id,
               details={"name": category.name}, ip=client_ip(request))
    db.commit()
    return _category_out(db, category)


@router.put("/categories/{category_id}", response_model=schemas.CategoryOut, summary="Изменить категорию")
def update_category(category_id: uuid.UUID, body: schemas.CategoryInput, request: Request,
                    admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    category = db.get(IngredientCategory, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    category.code, category.name, category.description = body.code or None, body.name.strip(), body.description
    try:
        db.flush()
    except IntegrityError:
        _unique_violation(db, "Категория")
    log_action(db, "admin_category_update", admin.user_id, entity="ingredient_categories", entity_id=category_id,
               details={"name": category.name}, ip=client_ip(request))
    db.commit()
    return _category_out(db, category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить категорию")
def delete_category(category_id: uuid.UUID, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    category = db.get(IngredientCategory, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    name = category.name
    db.delete(category)  # ингредиенты категории остаются без категории (ON DELETE SET NULL)
    log_action(db, "admin_category_delete", admin.user_id, entity="ingredient_categories", entity_id=category_id,
               details={"name": name}, ip=client_ip(request))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/integrity", response_model=list[schemas.IntegrityIssue], summary="Проверка корректности и целостности справочников")
def integrity(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return check_integrity(db)


# ---------------- резервное копирование ----------------

@router.get("/backups", response_model=list[schemas.BackupInfo], summary="Список резервных копий")
def backups(_: User = Depends(require_admin)):
    return [schemas.BackupInfo(**b) for b in backup_service.list_backups()]


@router.post("/backups", response_model=schemas.TaskAccepted, status_code=status.HTTP_202_ACCEPTED, summary="Запустить резервное копирование БД")
def create_backup(background: BackgroundTasks, admin: User = Depends(require_admin)):
    try:
        backup_service._pg_args()
        backup_service._binary(backup_service.get_settings().pg_dump_path)
    except backup_service.BackupError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    file_name = backup_service.new_backup_name("manual")
    background.add_task(backup_service.run_backup_task, file_name, admin.user_id)
    return schemas.TaskAccepted(status="started", message="Резервное копирование запущено", file_name=file_name)


@router.post("/backups/restore", response_model=schemas.TaskAccepted, summary="Восстановить БД из резервной копии")
def restore_backup(body: schemas.BackupRestoreRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    db.close()
    try:
        backup_service.restore_backup(body.file_name, admin.user_id)
    except backup_service.BackupError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    return schemas.TaskAccepted(status="completed", message="База данных восстановлена из резервной копии", file_name=body.file_name)
