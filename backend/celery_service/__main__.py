#!/usr/bin/env python3
import os
import sys
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('celery_service_main')

# Добавляем текущую директорию в sys.path, если её ещё нет
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
    logger.info(f"Добавлено в sys.path: {current_dir}")

# Выполнение главной функции
if __name__ == "__main__":
    from celery_app import app
    logger.info("Celery приложение импортировано")
    
    # Отображение информации
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")
    logger.info(f"sys.path: {sys.path}")
    
    # Запуск Celery app
    app.start() 