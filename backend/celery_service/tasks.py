from celery_config import app

@app.task(name='order.update_boxberry_statuses', queue='order')
def update_boxberry_statuses():
    # Импортируем здесь, чтобы избежать циклических импортов
    from cron_tasks.update_delivery_statuses import cron_update_boxberry_statuses
    import asyncio
    asyncio.run(cron_update_boxberry_statuses())