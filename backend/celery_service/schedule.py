from celery.schedules import crontab

# Здесь определяем все периодические задачи для Celery Beat
beat_schedule = {
    # Задачи для cart_service
    'cleanup-anonymous-carts-at-midnight': {
        'task': 'cart.cleanup_old_anonymous_carts',
        'schedule': crontab(hour=0, minute=0),  # Запуск каждый день в полночь
        'args': (1,),  # Аргумент: дни для сохранения корзин
        'options': {'queue': 'cart'},  # Указываем очередь
    },
    
    # Задачи для product_service
    'update-product-search-index': {
        'task': 'product.update_search_index',
        'schedule': crontab(hour='*/2'),  # Каждые 2 часа
        'options': {'queue': 'product'},
    },
    
    # Задачи для order_service
    'process-abandoned-orders': {
        'task': 'order.process_abandoned_orders',
        'schedule': crontab(hour=3, minute=0),  # Каждый день в 3 утра
        'options': {'queue': 'order'},
    },
    
    # Задачи для auth_service
    'cleanup-expired-tokens': {
        'task': 'auth.cleanup_expired_tokens',
        'schedule': crontab(hour='*/3'),  # Каждые 3 часа
        'options': {'queue': 'auth'},
    },
} 