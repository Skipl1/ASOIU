"""Журнал аудита: события входа, изменения профиля, генерации и действия администратора."""

import uuid

from sqlalchemy.orm import Session

from app.models import AuditLog

ACTION_TITLES = {
    "register": "Регистрация",
    "login_success": "Успешный вход",
    "login_failed": "Неудачный вход",
    "login_locked": "Вход заблокирован (превышен лимит попыток)",
    "logout": "Выход",
    "profile_update": "Изменение профиля",
    "parameter_add": "Новый замер параметров",
    "restriction_add": "Добавлен запрет",
    "restriction_delete": "Удалён запрет",
    "available_update": "Изменён набор доступных ингредиентов",
    "recipe_generate": "Генерация рецепта",
    "recipe_update": "Редактирование рецепта",
    "recipe_rate": "Оценка рецепта",
    "recipe_diet_add": "Рецепт добавлен в рацион",
    "recipe_diet_remove": "Рецепт убран из рациона",
    "report_export": "Экспорт отчёта",
    "admin_user_update": "Админ: изменение пользователя",
    "admin_user_delete": "Админ: удаление пользователя",
    "admin_ingredient_create": "Админ: добавлен ингредиент",
    "admin_ingredient_update": "Админ: изменён ингредиент",
    "admin_ingredient_delete": "Админ: удалён ингредиент",
    "admin_allergen_create": "Админ: добавлен аллерген",
    "admin_allergen_update": "Админ: изменён аллерген",
    "admin_allergen_delete": "Админ: удалён аллерген",
    "admin_category_create": "Админ: добавлена категория",
    "admin_category_update": "Админ: изменена категория",
    "admin_category_delete": "Админ: удалена категория",
    "backup_create": "Резервное копирование",
    "backup_restore": "Восстановление из резервной копии",
}


def log_action(
    db: Session,
    action: str,
    user_id: uuid.UUID | None = None,
    *,
    entity: str | None = None,
    entity_id: object | None = None,
    details: dict | None = None,
    ip: str | None = None,
    commit: bool = False,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
            ip=ip,
        )
    )
    if commit:
        db.commit()
