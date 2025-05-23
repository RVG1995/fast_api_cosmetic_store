from celery.schedules import crontab

# Здесь определяем все периодические задачи для Celery Beat
beat_schedule = {   
    # Задача для удаления устаревших корзин в полночь по Екатеринбургу (UTC+5)
    # Раскомментировать этот блок и закомментировать/удалить тестовую задачу выше
    # после завершения тестирования
     'update-delivery-statuses': {
         'task': 'order.update_boxberry_statuses',
         #'schedule': crontab(hour=19, minute=0),  # 19:00 UTC = 00:00 Екатеринбург (UTC+5)
         #'schedule': crontab(minute='*'), 
         'schedule': crontab(minute=0, hour='*/2'),
         #'args': (1,),  # Аргумент: дни для сохранения корзин
         #'options': {'queue': 'cart'},  # Указываем очередь
     },
} 