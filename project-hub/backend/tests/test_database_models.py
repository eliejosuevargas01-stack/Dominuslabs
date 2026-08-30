from sqlalchemy import ForeignKeyConstraint

from app.core.database import Base
import app.models  # noqa: F401


def test_required_tables_are_registered():
    assert {"company_settings", "produtos", "product_media"} <= set(Base.metadata.tables)


def test_product_media_uses_uuid_foreign_key():
    media_table = Base.metadata.tables["product_media"]
    product_table = Base.metadata.tables["produtos"]

    assert media_table.c.product_id.type.python_type is product_table.c.id.type.python_type

    foreign_keys = [
        constraint
        for constraint in media_table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert any(
        element.target_fullname == "produtos.id"
        for constraint in foreign_keys
        for element in constraint.elements
    )
