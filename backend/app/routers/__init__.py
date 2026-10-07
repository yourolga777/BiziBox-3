from .backup import router as backup_router
from .calendar import router as calendar_router
from .channels import router as channels_router
from .contact_folders import router as contact_folders_router
from .contacts import router as contacts_router
from .dashboard import router as dashboard_router
from .export import router as export_router
from .import_router import router as import_router
from .messages import router as messages_router
from .orders import router as orders_router
from .outbox import router as outbox_router
from .products import router as products_router
from .reminders import router as reminders_router
from .settings import router as settings_router
from .startup import router as startup_router
from .suppliers import router as suppliers_router
from .tasks import router as tasks_router
from .vpn_help import router as vpn_help_router

__all__ = [
    "backup_router",
    "calendar_router",
    "contact_folders_router",
    "messages_router",
    "contacts_router",
    "orders_router",
    "outbox_router",
    "products_router",
    "suppliers_router",
    "reminders_router",
    "tasks_router",
    "channels_router",
    "dashboard_router",
    "export_router",
    "import_router",
    "settings_router",
    "startup_router",
    "vpn_help_router",
]
