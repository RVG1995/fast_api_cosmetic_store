# Сервис заказов (Order Service)

Микросервис для управления заказами в интернет-магазине косметики.

## Функциональность

- Создание заказов
- Управление статусами заказов
- Отслеживание истории изменений статусов
- Управление адресами доставки и выставления счетов
- Отмена заказов
- Статистика по заказам

## Технологии

- FastAPI
- SQLAlchemy (асинхронный режим)
- Alembic для миграций
- PostgreSQL
- JWT для аутентификации
- Pydantic для валидации данных

## Установка и запуск

### Предварительные требования

- Python 3.10+
- PostgreSQL
- Redis (опционально, для кеширования)

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Настройка окружения

Создайте файл `.env` в корневой директории проекта и заполните его следующими переменными:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost/orders_db
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_SECONDS=3600
PRODUCT_SERVICE_URL=http://localhost:8001
CART_SERVICE_URL=http://localhost:8002
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_FROM=your-email@example.com
MAIL_FROM_NAME=Your Name
UPLOAD_DIR=static/uploads
LOG_LEVEL=INFO
```

### Миграции базы данных

Инициализация миграций:

```bash
alembic init alembic
```

Создание миграции:

```bash
alembic revision --autogenerate -m "Initial migration"
```

Применение миграций:

```bash
alembic upgrade head
```

### Запуск сервера

```bash
uvicorn main:app --reload
```

Сервер будет доступен по адресу: http://localhost:8000

## API Endpoints

### Заказы

- `GET /api/orders` - Получение списка заказов
- `GET /api/orders/{order_id}` - Получение информации о заказе
- `POST /api/orders` - Создание нового заказа
- `PUT /api/orders/{order_id}` - Обновление информации о заказе
- `POST /api/orders/{order_id}/status` - Изменение статуса заказа
- `POST /api/orders/{order_id}/cancel` - Отмена заказа
- `GET /api/orders/stats/summary` - Получение статистики по заказам

### Статусы заказов

- `GET /api/order-statuses` - Получение списка статусов заказов
- `GET /api/order-statuses/{status_id}` - Получение информации о статусе
- `POST /api/order-statuses` - Создание нового статуса
- `PUT /api/order-statuses/{status_id}` - Обновление информации о статусе
- `DELETE /api/order-statuses/{status_id}` - Удаление статуса

### Адреса доставки

- `GET /api/shipping-addresses` - Получение списка адресов доставки
- `GET /api/shipping-addresses/{address_id}` - Получение информации об адресе
- `POST /api/shipping-addresses` - Создание нового адреса
- `PUT /api/shipping-addresses/{address_id}` - Обновление информации об адресе
- `DELETE /api/shipping-addresses/{address_id}` - Удаление адреса

### Адреса для выставления счетов

- `GET /api/billing-addresses` - Получение списка адресов для выставления счетов
- `GET /api/billing-addresses/{address_id}` - Получение информации об адресе
- `POST /api/billing-addresses` - Создание нового адреса
- `PUT /api/billing-addresses/{address_id}` - Обновление информации об адресе
- `DELETE /api/billing-addresses/{address_id}` - Удаление адреса

## Документация API

После запуска сервера документация API доступна по адресам:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc 