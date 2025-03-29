from celery.schedules import crontab, timedelta

# Здесь определяем все периодические задачи для Celery Beat
beat_schedule = {    
    # Тестовая задача для удаления корзин, запускается каждую секунду
    #'test-cleanup-anonymous-carts': {
    #    'task': 'cart.cleanup_old_anonymous_carts',
    #    'schedule': timedelta(seconds=1),  # Запуск каждую секунду для тестирования
    #    'args': (1,),  # Аргумент: дни для сохранения корзин
     #   'options': {'queue': 'cart'},  # Указываем очередь
    #},
    
    # Задача для удаления устаревших корзин в полночь по Екатеринбургу (UTC+5)
    # Раскомментировать этот блок и закомментировать/удалить тестовую задачу выше
    # после завершения тестирования
     'cleanup-anonymous-carts-at-ekb-midnight': {
         'task': 'cart.cleanup_old_anonymous_carts',
         'schedule': crontab(hour=19, minute=0),  # 19:00 UTC = 00:00 Екатеринбург (UTC+5)
         'args': (1,),  # Аргумент: дни для сохранения корзин
         'options': {'queue': 'cart'},  # Указываем очередь
     },
} 