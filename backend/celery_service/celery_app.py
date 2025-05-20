from celery_config import app
import tasks  # Импортируем задачи

if __name__ == '__main__':
    app.start()