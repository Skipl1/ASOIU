"""Ограниченная учётная запись приложения в PostgreSQL (ТЗ 4.3: «минимально необходимые права»).

Запускается при старте backend под владельцем БД, после миграций. Идемпотентно:

  * роль приложения (имя и пароль берутся из DATABASE_URL) создаётся или обновляется;
  * права только на чтение и запись данных (SELECT/INSERT/UPDATE/DELETE) в схеме public;
  * нельзя создавать, изменять и удалять таблицы, управлять ролями и базой (не суперпользователь);
  * таблица alembic_version приложению недоступна;
  * права на таблицы, которые будут созданы позже (миграции, pg_restore), выдаются автоматически.

Миграции, наполнение справочников, резервное копирование и восстановление выполняются под владельцем
(переменная OWNER_DATABASE_URL), а все запросы пользователей — под ограниченной ролью.
"""

import logging
import os
import sys

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

logger = logging.getLogger("grsn.db_roles")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    owner_raw = os.environ.get("OWNER_DATABASE_URL")
    app_raw = os.environ.get("DATABASE_URL")
    if not owner_raw or not app_raw:
        logger.info("OWNER_DATABASE_URL не задан — ограниченная роль не создаётся")
        return 0

    owner, app = make_url(owner_raw), make_url(app_raw)
    if owner.username == app.username:
        logger.info("Приложение и владелец используют одну учётную запись — роль не создаётся")
        return 0
    role, password, database = app.username, app.password, app.database
    owner_name = owner.username

    with psycopg.connect(host=owner.host, port=owner.port or 5432, user=owner_name, password=owner.password,
                         dbname=database, autocommit=True) as conn:
        ident = sql.Identifier
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        verb = "ALTER" if exists else "CREATE"
        conn.execute(sql.SQL(verb + " ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION")
                     .format(ident(role), sql.Literal(password)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(ident(database), ident(role)))
        conn.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(ident(role)))
        conn.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(ident(role)))
        conn.execute(sql.SQL("REVOKE ALL ON TABLE alembic_version FROM {}").format(ident(role)))
        conn.execute(sql.SQL("ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}")
                     .format(ident(owner_name), ident(role)))
    logger.info("Роль приложения %s %s: только SELECT/INSERT/UPDATE/DELETE в схеме public", role, "обновлена" if exists else "создана")
    return 0


if __name__ == "__main__":
    sys.exit(main())
