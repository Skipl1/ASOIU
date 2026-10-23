"""recipes.generation_status: значения generated / accepted (рецепт включён в рацион)

Структура таблиц не меняется. До этой версии все рецепты учитывались в отчётах, поэтому
существующие рецепты переводятся в статус accepted, чтобы отчёты и анализ не изменились.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE recipes SET generation_status = 'accepted' WHERE generation_status IN ('generated', 'edited')")


def downgrade() -> None:
    op.execute("UPDATE recipes SET generation_status = 'generated' WHERE generation_status = 'accepted'")
