#!/bin/bash

# Запуск Celery worker
echo "Запуск Celery worker для обработки задач..."
celery -A tasks worker --loglevel=info --without-mingle --without-gossip --without-heartbeat &

# Запуск Celery beat для планирования задач по расписанию
echo "Запуск Celery beat для планирования задач..."
celery -A tasks beat --loglevel=info

# Ожидание завершения всех процессов
wait 