"""Run Alembic safely when adopting migrations on an existing database."""

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import engine

LEGACY_HEAD = "2026082902"
REQUIRED_LEGACY_TABLES = {
    "users",
    "whatsapp_accounts",
    "order_manager_orders",
    "order_manager_order_items",
}


def prepare_existing_database() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    config = Config("alembic.ini")

    if "alembic_version" not in tables:
        missing = REQUIRED_LEGACY_TABLES - tables
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise RuntimeError(
                "Database is neither an initialized legacy database nor an "
                f"Alembic-managed database. Missing baseline tables: {missing_list}"
            )
        command.stamp(config, LEGACY_HEAD)

    command.upgrade(config, "head")


if __name__ == "__main__":
    prepare_existing_database()
