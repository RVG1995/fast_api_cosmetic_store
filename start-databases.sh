#!/bin/bash

# Запуск всех баз данных для проекта
echo "Запуск баз данных для всех сервисов..."

# Запуск контейнеров
docker-compose -f docker-compose.db.yml up -d

echo "Проверка статуса контейнеров..."
docker ps

echo "Базы данных запущены!"
echo "- auth-db: postgres://postgres:postgres@localhost:5433/auth_db"
echo "- product-db: postgres://postgres:postgres@localhost:5432/product_db"
echo "- cart-db: postgres://postgres:postgres@localhost:5434/cart_db"
echo "- redis: redis://localhost:6379/0" 