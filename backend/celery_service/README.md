# Централизованный Celery-сервис для периодических задач

Этот сервис используется только для запуска периодических задач (beat) в рамках микросервисной архитектуры.

## Особенности

- Единый сервис Celery для периодических задач
- Поддержка расписания через Celery Beat
- Общая инфраструктура (Redis) для брокера сообщений и хранения результатов

## Структура

```
celery_service/
├── tasks/
│   ├── __init__.py
│   └── ... (файлы с задачами для beat)
├── celery_app.py          # Настройка Celery и beat
├── schedule.py            # Настройка периодических задач (celerybeat)
├── requirements.txt       # Зависимости
├── Dockerfile             # Для создания Docker-образа
├── .env.example           # Пример переменных окружения 
└── README.md              # Документация
```

## Запуск

### В режиме разработки:

```bash
./run_dev.sh worker  # Запуск worker (для beat)
./run_dev.sh beat    # Запуск beat для периодических задач
./run_dev.sh flower  # Запуск Flower для мониторинга
```

### С Docker Compose:

```bash
docker-compose up -d
```

## Добавление новых периодических задач

1. Создайте/обновите файл в директории `tasks/` для соответствующего микросервиса
2. Зарегистрируйте задачу с помощью декоратора `@app.task`
3. Добавьте задачу в расписание в `schedule.py`

Пример:

```python
# В файле tasks/order_tasks.py
from celery_app import app

@app.task(name='order.process_abandoned_orders', queue='order')
def process_abandoned_orders():
    # Логика обработки
    pass
```

В `schedule.py`:

```python
beat_schedule = {
    'process-abandoned-orders-every-hour': {
        'task': 'order.process_abandoned_orders',
        'schedule': 3600,  # каждый час
    },
}
```

## Мониторинг

Для мониторинга задач используйте Flower:
- В режиме разработки: `./run_dev.sh flower`
- В Docker Compose: доступен по адресу `http://localhost:5555` 