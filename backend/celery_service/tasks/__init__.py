# Импортируем все задачи из модулей для автоматической регистрации в Celery
from .cart_tasks import *  # noqa
from .auth_tasks import *  # noqa
from .order_tasks import *  # noqa
from .product_tasks import *  # noqa 