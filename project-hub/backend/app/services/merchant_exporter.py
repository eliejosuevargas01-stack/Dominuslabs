"""Export a tenant's merchant data in the Open Delivery v1.7.x merchant schema.

The schema returned by :func:`export_merchant` follows the ``merchant`` object
expected by Open Delivery platforms (e.g. iFood / Pedidos10) - see the
Open Delivery Merchant API documentation for the canonical reference.
"""

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_setting import CompanySetting
from app.models.product import Product
from app.models.tenant_platform_integration import TenantPlatformIntegration


def _build_address(company: CompanySetting) -> Dict[str, Any]:
    """Return an Open Delivery ``address`` dict from a CompanySetting."""
    return {
        "streetName": company.address,
        "streetNumber": company.address_number,
        "neighborhood": company.address_neighborhood,
        "city": company.address_city,
        "state": company.address_state,
        "postalCode": company.address_zip,
    }


def export_merchant(tenant_id: str, db: Session) -> Dict[str, Any]:
    """Export the Open Delivery merchant schema for ``tenant_id``.

    The returned dictionary is a ``merchant`` object as defined by the Open
    Delivery specification (v1.7.x).  Tenant isolation is enforced - only the
    products, company settings and platform integrations belonging to
    ``tenant_id`` are ever queried.

    Args:
        tenant_id: The tenant whose merchant data should be exported.
        db: An active SQLAlchemy :class:`~sqlalchemy.orm.Session`.

    Returns:
        A dictionary with the keys ``id``, ``name``, ``document``,
        ``address``, ``categories`` and ``items``.
    """
    # ------------------------------------------------------------------ #
    # Company setting (merchant identity, document and address).         #
    # ------------------------------------------------------------------ #
    company = db.execute(
        select(CompanySetting).where(CompanySetting.tenant_id == tenant_id)
    ).scalar_one_or_none()

    # Resolve the merchant id: prefer the platform integration's merchant_id,
    # falling back to the tenant_id when no integration exists.
    integration = db.execute(
        select(TenantPlatformIntegration).where(
            TenantPlatformIntegration.tenant_id == tenant_id
        )
    ).scalar_one_or_none()

    merchant_id = (integration.merchant_id if integration else None) or tenant_id

    if company is None:
        # No company setting at all -> minimum schema, no items.
        return {
            "id": merchant_id,
            "name": tenant_id,
            "document": {"number": None, "type": "CNPJ"},
            "address": {
                "streetName": None,
                "streetNumber": None,
                "neighborhood": None,
                "city": None,
                "state": None,
                "postalCode": None,
            },
            "categories": [],
            "items": [],
        }

    merchant: Dict[str, Any] = {
        "id": merchant_id,
        "name": company.company_name or tenant_id,
        "document": {
            "number": company.cnpj_cpf,
            "type": "CNPJ",
        },
        "address": _build_address(company),
    }

    # ------------------------------------------------------------------ #
    # Products (categories + items).                                     #
    # ------------------------------------------------------------------ #
    products = db.execute(
        select(Product).where(Product.tenant_id == tenant_id)
    ).scalars().all()

    # Build the category list from the *unique* categories of the tenant's
    # products.  Products whose ``categoria`` is None or empty string are
    # grouped under the ``Outros`` category.
    categories: List[Dict[str, Any]] = []
    category_index: Dict[str, int] = {}

    for product in products:
        category_name = product.categoria if product.categoria else "Outros"
        if category_name not in category_index:
            idx = len(category_index)
            category_index[category_name] = idx
            categories.append(
                {"id": f"cat-{idx}", "name": category_name, "sequence": idx}
            )

    # Build the items list, mapping each product to its category id.
    items: List[Dict[str, Any]] = []
    for product in products:
        category_name = product.categoria if product.categoria else "Outros"
        category_id = f"cat-{category_index[category_name]}"

        items.append(
            {
                "id": product.codigo_slug,
                "name": product.nome,
                "description": product.descricao,
                "externalCode": product.codigo_slug,
                "price": {
                    "value": product.preco,
                    "currency": "BRL",
                },
                "status": "AVAILABLE" if product.disponivel else "UNAVAILABLE",
                "categoryId": category_id,
                "imagePath": product.imagem_url,
            }
        )

    merchant["categories"] = categories
    merchant["items"] = items

    return merchant
