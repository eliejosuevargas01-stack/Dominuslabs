"""
Documentação do módulo router.py.

O que faz: Implementa a lógica estrutural e funcional para o módulo core/base router.
Impacto na regra de negócio: É responsável por garantir que as operações e validações relacionadas a o módulo core/base router funcionem corretamente e mantenham a integridade dos dados da aplicação.
"""
from fastapi import APIRouter

from app.api.endpoints import projects, uploads, webhooks, auth, crm, users, whatsapp, health, company_setting, product_media, products, orders

api_router = APIRouter()

api_router.include_router(health.router, prefix="/system", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(company_setting.router, prefix="/company-settings", tags=["company-settings"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(product_media.router, prefix="/product-media", tags=["product-media"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(crm.router, prefix="/crm", tags=["crm"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
