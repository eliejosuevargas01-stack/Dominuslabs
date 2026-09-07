from migrate_db import LEGACY_HEAD, REQUIRED_LEGACY_TABLES


def test_legacy_baseline_matches_last_pre_migration_revision():
    assert LEGACY_HEAD == "2026082902"
    assert {
        "users",
        "whatsapp_accounts",
        "order_manager_orders",
        "order_manager_order_items",
    } == REQUIRED_LEGACY_TABLES


def test_migration_2026090701_whatsapp_account_unique_constraint():
    import importlib.util
    import os

    migration_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "alembic",
        "versions",
        "2026090701_add_whatsapp_account_tenant_session_unique.py"
    )
    assert os.path.exists(migration_path), "Migration file 2026090701 must exist"

    spec = importlib.util.spec_from_file_location("migration_2026090701", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "2026090701"
    assert module.down_revision == "2026090601"
    assert hasattr(module, "upgrade") and callable(module.upgrade)
    assert hasattr(module, "downgrade") and callable(module.downgrade)

