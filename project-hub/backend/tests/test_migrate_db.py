from migrate_db import LEGACY_HEAD, REQUIRED_LEGACY_TABLES


def test_legacy_baseline_matches_last_pre_migration_revision():
    assert LEGACY_HEAD == "2026082902"
    assert {
        "users",
        "whatsapp_accounts",
        "order_manager_orders",
        "order_manager_order_items",
    } == REQUIRED_LEGACY_TABLES
