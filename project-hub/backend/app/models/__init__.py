"""Central registry for SQLAlchemy models used by Alembic and tests."""

from app.models.asset import ProjectAsset
from app.models.company_setting import CompanySetting
from app.models.feedback import Feedback
from app.models.logs import CommitLog, DeployLog
from app.models.order_manager import OrderManagerOrder, OrderManagerOrderItem
from app.models.product import Product
from app.models.product_media import ProductMedia
from app.models.project import Project
from app.models.task import ProjectTask
from app.models.user import User
from app.models.whatsapp_account import WhatsappAccount

__all__ = [
    "CommitLog",
    "CompanySetting",
    "DeployLog",
    "Feedback",
    "OrderManagerOrder",
    "OrderManagerOrderItem",
    "Product",
    "ProductMedia",
    "Project",
    "ProjectAsset",
    "ProjectTask",
    "User",
    "WhatsappAccount",
]
