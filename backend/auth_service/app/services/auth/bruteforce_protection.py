"""Модуль для защиты от брутфорс-атак с использованием Redis для хранения состояния попыток входа."""

import json
import logging
import time
from typing import Dict, Any

import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)

# Настройки Redis из конфигурации
REDIS_HOST = settings.REDIS_HOST
REDIS_PORT = settings.REDIS_PORT
REDIS_DB = 0  # Auth service использует DB 0
REDIS_PASSWORD = settings.REDIS_PASSWORD

# Настройки защиты от брутфорса из конфигурации
MAX_FAILED_ATTEMPTS = settings.MAX_FAILED_ATTEMPTS  # Макс. кол-во неудачных попыток
BLOCK_TIME = settings.BLOCK_TIME  # Время блокировки в секундах (5 минут)
ATTEMPT_TTL = settings.ATTEMPT_TTL  # Срок хранения счетчика попыток (1 час)

class BruteforceProtection:
    """Сервис защиты от брутфорса с использованием Redis"""
    
    def __init__(self):
        """Инициализация сервиса защиты от брутфорса"""
        self.redis = None
        self.enabled = True
        logger.info("Инициализация сервиса защиты от брутфорса")
    
    async def initialize(self):
        """Асинхронная инициализация соединения с Redis"""
        try:
            # Создаем строку подключения Redis
            redis_url = "redis://"
            if REDIS_PASSWORD:
                redis_url += f":{REDIS_PASSWORD}@"
            redis_url += f"{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = await redis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=True  # Автоматически декодируем ответы из байтов в строки
            )
            
            logger.info("Подключение к Redis успешно: %s:%s/%s", REDIS_HOST, REDIS_PORT, REDIS_DB)
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка подключения к Redis: %s", str(e))
            self.redis = None
            self.enabled = False
    
    async def check_ip_blocked(self, ip_address: str) -> bool:
        """
        Проверяет, заблокирован ли IP адрес
        
        Args:
            ip_address: IP адрес для проверки
            
        Returns:
            bool: True, если IP заблокирован, иначе False
        """
        if not self.redis or not self.enabled:
            logger.warning("Redis недоступен, проверка блокировки IP пропущена")
            return False
            
        try:
            block_key = f"ip_block:{ip_address}"
            blocked_until = await self.redis.get(block_key)
            
            if blocked_until:
                # Если время блокировки еще не истекло
                blocked_until_int = int(blocked_until)
                if blocked_until_int > int(time.time()):
                    remaining = blocked_until_int - int(time.time())
                    logger.warning("IP %s заблокирован на %s секунд", ip_address, remaining)
                    return True
                
                # Если время блокировки истекло, удаляем ключ
                await self.redis.delete(block_key)
                
            return False
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, ValueError) as e:
            logger.error("Ошибка при проверке блокировки IP %s: %s", ip_address, str(e))
            return False
    
    async def record_failed_attempt(self, ip_address: str, username: str = None) -> Dict[str, Any]:
        """
        Регистрирует неудачную попытку входа
        
        Args:
            ip_address: IP адрес
            username: Имя пользователя (опционально)
            
        Returns:
            Dict[str, Any]: Информация о блокировке
        """
        if not self.redis or not self.enabled:
            logger.warning("Redis недоступен, запись неудачной попытки входа пропущена")
            return {"blocked": False, "attempts": 0, "remaining_attempts": MAX_FAILED_ATTEMPTS}
            
        try:
            current_time = int(time.time())
            
            # Для более точной защиты используем комбинацию IP и имени пользователя (если указано)
            if username:
                attempt_key = f"login_attempts:{ip_address}:{username}"
            else:
                attempt_key = f"login_attempts:{ip_address}"
                
            # Получаем текущее количество попыток
            attempts_data = await self.redis.get(attempt_key)
            attempts = 1
            
            if attempts_data:
                try:
                    data = json.loads(attempts_data)
                    attempts = data.get("count", 0) + 1
                except (json.JSONDecodeError, AttributeError, TypeError):
                    attempts = 1
            
            # Обновляем данные о попытках
            await self.redis.setex(
                attempt_key,
                ATTEMPT_TTL,  # TTL ключа
                json.dumps({"count": attempts, "last_attempt": current_time})
            )
            
            # Проверяем, не превышено ли максимальное количество попыток
            if attempts >= MAX_FAILED_ATTEMPTS:
                # Блокируем IP
                block_key = f"ip_block:{ip_address}"
                block_until = current_time + BLOCK_TIME
                await self.redis.setex(block_key, BLOCK_TIME, str(block_until))
                
                logger.warning("IP %s заблокирован на %s секунд после %s неудачных попыток", ip_address, BLOCK_TIME, attempts)
                
                # Сбрасываем счетчик попыток
                await self.redis.delete(attempt_key)
                
                return {
                    "blocked": True,
                    "attempts": attempts,
                    "remaining_attempts": 0,
                    "blocked_until": block_until,
                    "blocked_for": BLOCK_TIME
                }
            
            logger.info("Неудачная попытка входа с IP %s%s. Попытка %s из %s", ip_address, f' для пользователя {username}' if username else '', attempts, MAX_FAILED_ATTEMPTS)
            
            return {
                "blocked": False,
                "attempts": attempts,
                "remaining_attempts": MAX_FAILED_ATTEMPTS - attempts
            }
            
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError, ValueError, json.JSONDecodeError) as e:
            logger.error("Ошибка при записи неудачной попытки входа: %s", str(e))
            return {"blocked": False, "attempts": 0, "remaining_attempts": MAX_FAILED_ATTEMPTS}
    
    async def reset_attempts(self, ip_address: str, username: str = None) -> bool:
        """
        Сбрасывает счетчик неудачных попыток входа (после успешного входа)
        
        Args:
            ip_address: IP адрес
            username: Имя пользователя (опционально)
            
        Returns:
            bool: True при успешном сбросе, иначе False
        """
        if not self.redis or not self.enabled:
            logger.warning("Redis недоступен, сброс счетчика попыток пропущен")
            return False
            
        try:
            # Удаляем ключи попыток для данного IP (и пользователя, если указан)
            if username:
                attempt_key = f"login_attempts:{ip_address}:{username}"
                await self.redis.delete(attempt_key)
                
            # Также сбрасываем счетчик для IP без привязки к пользователю
            ip_attempt_key = f"login_attempts:{ip_address}"
            await self.redis.delete(ip_attempt_key)
            
            logger.info("Сброшен счетчик неудачных попыток для IP %s%s", ip_address, f' и пользователя {username}' if username else '')
            
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка при сбросе счетчика попыток: %s", str(e))
            return False

    async def close(self):
        """Закрывает соединение с Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Соединение с Redis для защиты от брутфорса закрыто")

# Глобальный экземпляр для использования в приложении
bruteforce_protection = BruteforceProtection()
