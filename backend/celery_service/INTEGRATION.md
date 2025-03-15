# Интеграция централизованного Celery с микросервисами

Данный документ описывает шаги, необходимые для интеграции существующих микросервисов с централизованным сервисом Celery.

## Общий принцип

1. Все задачи Celery определяются и выполняются в централизованном сервисе Celery.
2. Микросервисы не импортируют и не выполняют задачи Celery, а только отправляют сообщения в очередь.
3. Сервис Celery выполняет задачи и отправляет запросы обратно к соответствующим микросервисам через HTTP API.

## Шаги интеграции для каждого микросервиса

### 1. Обновление структуры проекта

Для работы с монолитным Celery в микросервисной архитектуре необходимо:

- Добавить задачи для микросервиса в файл `/backend/celery_service/tasks/{service_name}_tasks.py`
- Убедиться, что задачи правильно импортируются в `/backend/celery_service/tasks/__init__.py`
- Добавить периодические задачи в `/backend/celery_service/schedule.py` при необходимости

### 2. Отправка сообщений в очередь Celery из микросервисов

В каждом микросервисе добавьте утилиту для отправки сообщений в Redis:

```python
# utils/celery_utils.py
import json
import os
import redis
import uuid

# Получаем настройки подключения к Redis из переменных окружения или используем значения по умолчанию
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379") 
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Функция для отправки задачи в очередь Celery
def send_celery_task(task_name, args=None, kwargs=None, queue=None):
    """
    Отправка задачи в очередь Celery через Redis.
    
    Args:
        task_name (str): Имя задачи в формате 'service.task_name'
        args (list, optional): Позиционные аргументы задачи
        kwargs (dict, optional): Именованные аргументы задачи
        queue (str, optional): Имя очереди. Если не указано, берется из task_name
        
    Returns:
        str: ID задачи
    """
    args = args or []
    kwargs = kwargs or {}
    
    # Если очередь не указана, берем её из имени задачи (первая часть до точки)
    if queue is None:
        queue = task_name.split('.')[0]
    
    # Создаем соединение с Redis
    r = redis.Redis(
        host=REDIS_HOST,
        port=int(REDIS_PORT),
        db=int(REDIS_DB),
        password=REDIS_PASSWORD or None
    )
    
    # Генерируем уникальный ID задачи
    task_id = str(uuid.uuid4())
    
    # Создаем сообщение задачи в формате Celery
    task_message = {
        "id": task_id,
        "task": task_name,
        "args": args,
        "kwargs": kwargs,
        "retries": 0,
        "eta": None,
        "expires": None,
    }
    
    # Сериализуем сообщение в JSON
    json_message = json.dumps(task_message)
    
    # Публикуем сообщение в очередь Celery
    r.lpush(f'celery:{queue}', json_message)
    
    return task_id
```

### 3. Обновление Docker Compose

В файл `docker-compose.yml` каждого микросервиса добавьте доступ к Redis:

```yaml
services:
  # Существующие сервисы...
  
  your_service:
    # Существующая конфигурация...
    environment:
      # Существующие переменные...
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=0
      - REDIS_PASSWORD=${REDIS_PASSWORD:-}
    networks:
      - app_network
      
networks:
  app_network:
    external: true
```

### 4. Примеры использования в микросервисах

#### Пример для auth_service

```python
# В файле auth_service/app/utils/email.py
from app.utils.celery_utils import send_celery_task

def send_verification_email_to_user(user_id, email, verification_link):
    """Отправляет email для подтверждения регистрации через Celery"""
    send_celery_task(
        'auth.send_verification_email',
        args=[user_id, email, verification_link]
    )

def schedule_token_cleanup():
    """Запускает задачу очистки старых токенов"""
    send_celery_task(
        'auth.cleanup_expired_tokens',
        args=[7]  # Хранить токены 7 дней
    )
```

#### Пример для cart_service

```python
# В файле cart_service/app/services/cart.py
from app.utils.celery_utils import send_celery_task

def merge_user_carts(anonymous_cart_id, user_cart_id):
    """Объединяет анонимную корзину с корзиной пользователя"""
    send_celery_task(
        'cart.merge_carts',
        args=[anonymous_cart_id, user_cart_id]
    )
```

#### Пример для order_service

```python
# В файле order_service/app/services/order.py
from app.utils.celery_utils import send_celery_task

def send_order_confirmation_email(order_id, email):
    """Отправляет подтверждение заказа по email"""
    send_celery_task(
        'order.send_order_confirmation',
        args=[order_id, email]
    )

def update_order_status_async(order_id, new_status):
    """Асинхронно обновляет статус заказа"""
    send_celery_task(
        'order.update_order_status',
        args=[order_id, new_status, True]  # True - отправлять уведомление
    )
```

#### Пример для product_service

```python
# В файле product_service/app/services/product.py
from app.utils.celery_utils import send_celery_task

def process_product_images_async(product_id, image_urls):
    """Обрабатывает изображения продукта асинхронно"""
    send_celery_task(
        'product.process_images',
        args=[product_id, image_urls]
    )

def update_product_stock(product_id, quantity_delta, reason="order"):
    """Обновляет запасы товара"""
    send_celery_task(
        'product.update_stock',
        args=[product_id, quantity_delta, reason]
    )
```

## Обновление и добавление задач Celery

Для добавления новых задач в централизованный сервис Celery:

1. Создайте или обновите файл задач в `/backend/celery_service/tasks/{service_name}_tasks.py`
2. Реализуйте логику задачи с использованием декоратора `@app.task`
3. Убедитесь, что задача зарегистрирована с правильным именем и очередью
4. При необходимости добавьте периодические задачи в `schedule.py`

## Тестирование интеграции

Для проверки правильности интеграции выполните следующие действия:

1. Запустите Redis: `docker run -d --name redis-test -p 6379:6379 redis:7.2-alpine`
2. Запустите воркер Celery: `cd backend/celery_service && ./run_dev.sh worker`
3. В микросервисе отправьте сообщение через `send_celery_task` и проверьте логи воркера

## Мониторинг и отладка

1. Для мониторинга задач используйте Flower: `cd backend/celery_service && ./run_dev.sh flower`
2. Просматривайте очереди Redis: `redis-cli -h localhost -p 6379 LLEN celery:auth`
3. Проверяйте логи воркеров Celery для отладки выполнения задач 