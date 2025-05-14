# Импорт роутеров для удобного доступа
from .orders import router as orders_router
from .admin_router import router as admin_orders_router
from .service_router import router as service_orders_router
from .order_statuses import router as order_statuses_router
from .addresses import shipping_router, billing_router 