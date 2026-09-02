"""create company settings, products, and product media tables

Revision ID: 2026083001
Revises: 2026082902
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "2026083001"
down_revision = "2026082902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("company_name", sa.String(), nullable=True),
        sa.Column("niche", sa.String(), nullable=True),
        sa.Column("cnpj_cpf", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("address_number", sa.String(), nullable=True),
        sa.Column("address_neighborhood", sa.String(), nullable=True),
        sa.Column("address_city", sa.String(), nullable=True),
        sa.Column("address_state", sa.String(), nullable=True),
        sa.Column("address_zip", sa.String(), nullable=True),
        sa.Column("business_hours", sa.Text(), nullable=True),
        sa.Column("tone_of_voice", sa.String(), nullable=True),
        sa.Column("custom_instructions", sa.Text(), nullable=True),
        sa.Column("exchange_policy", sa.Text(), nullable=True),
        sa.Column("delivery_policy", sa.Text(), nullable=True),
        sa.Column("terms_of_service", sa.Text(), nullable=True),
        sa.Column("menu_catalog", sa.JSON(), nullable=True),
        sa.Column("accepted_payment_types", sa.JSON(), nullable=True),
        sa.Column("payment_notes", sa.Text(), nullable=True),
        sa.Column("values_mission", sa.Text(), nullable=True),
        sa.Column("additional_notes", sa.Text(), nullable=True),
        sa.Column("delivery_fee_type", sa.String(), nullable=True),
        sa.Column("delivery_fee_value", sa.Float(), nullable=True),
        sa.Column("delivery_radius_km", sa.Float(), nullable=True),
        sa.Column("delivery_max_coverage_km", sa.Float(), nullable=True),
        sa.Column("delivery_tiers", sa.JSON(), nullable=True),
        sa.Column("minimum_order_value", sa.Float(), nullable=True),
        sa.Column("preparation_time_minutes", sa.Integer(), nullable=True),
        sa.Column("promotions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_company_settings_tenant_id"),
    )
    op.create_index("ix_company_settings_id", "company_settings", ["id"])
    op.create_index("ix_company_settings_tenant_id", "company_settings", ["tenant_id"])

    op.create_table(
        "produtos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("codigo_slug", sa.String(), nullable=False),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("descricao", sa.String(), nullable=True),
        sa.Column("categoria", sa.String(), nullable=True),
        sa.Column("preco", sa.Float(), nullable=False),
        sa.Column("disponivel", sa.Boolean(), nullable=False),
        sa.Column("estoque", sa.Integer(), nullable=False),
        sa.Column("imagem_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_produtos_id", "produtos", ["id"])
    op.create_index("ix_produtos_tenant_id", "produtos", ["tenant_id"])

    op.create_table(
        "product_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("media_url", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["produtos.id"],
            name="fk_product_media_product_id_produtos",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_product_media_id", "product_media", ["id"])
    op.create_index("ix_product_media_tenant_id", "product_media", ["tenant_id"])
    op.create_index("ix_product_media_product_id", "product_media", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_product_media_product_id", table_name="product_media")
    op.drop_index("ix_product_media_tenant_id", table_name="product_media")
    op.drop_index("ix_product_media_id", table_name="product_media")
    op.drop_table("product_media")
    op.drop_index("ix_produtos_tenant_id", table_name="produtos")
    op.drop_index("ix_produtos_id", table_name="produtos")
    op.drop_table("produtos")
    op.drop_index("ix_company_settings_tenant_id", table_name="company_settings")
    op.drop_index("ix_company_settings_id", table_name="company_settings")
    op.drop_table("company_settings")
