import os
from redis import asyncio as aioredis
import time
import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Настройки защиты от брутфорса
MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "5"))  # Макс. кол-во неудачных попыток
BLOCK_TIME = int(os.getenv("BLOCK_TIME", "300"))  # Время блокировки в секундах (5 минут)
ATTEMPT_TTL = int(os.getenv("ATTEMPT_TTL", "3600"))  # Срок хранения счетчика попыток (1 час)

class BruteforceProtection:
    """Сервис защиты от брутфорса с использованием Redis"""
    
    def __init__(self):
        """Инициализация сервиса защиты от брутфорса"""
        self.redis = None
        logger.info("Инициализация сервиса защиты от брутфорса")
    
    async def initialize(self):
        """Асинхронная инициализация соединения с Redis"""
        try:
            # Создаем строку подключения Redis
            redis_url = f"redis://"
            if REDIS_PASSWORD:
                redis_url += f":{REDIS_PASSWORD}@"
            redis_url += f"{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = await aioredis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=True  # Автоматически декодируем ответы из байтов в строки
            )
            
            logger.info(f"Подключение к Redis успешно: {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {str(e)}")
            self.redis = None
    
    async def check_ip_blocked(self, ip_address: str) -> bool:
        """
        Проверяет, заблокирован ли IP адрес
        
        Args:
            ip_address: IP адрес для проверки
            
        Returns:
            bool: True, если IP заблокирован, иначе False
        """
        if not self.redis:
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
                    logger.warning(f"IP {ip_address} заблокирован на {remaining} секунд")
                    return True
                
                # Если время блокировки истекло, удаляем ключ
                await self.redis.delete(block_key)
                
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке блокировки IP {ip_address}: {str(e)}")
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
        if not self.redis:
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
                except:
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
                
                logger.warning(f"IP {ip_address} заблокирован на {BLOCK_TIME} секунд после {attempts} неудачных попыток")
                
                # Сбрасываем счетчик попыток
                await self.redis.delete(attempt_key)
                
                return {
                    "blocked": True,
                    "attempts": attempts,
                    "remaining_attempts": 0,
                    "blocked_until": block_until,
                    "blocked_for": BLOCK_TIME
                }
            
            logger.info(f"Неудачная попытка входа с IP {ip_address}" + 
                      (f" для пользователя {username}" if username else "") + 
                      f". Попытка {attempts} из {MAX_FAILED_ATTEMPTS}")
            
            return {
                "blocked": False,
                "attempts": attempts,
                "remaining_attempts": MAX_FAILED_ATTEMPTS - attempts
            }
            
        except Exception as e:
            logger.error(f"Ошибка при записи неудачной попытки входа: {str(e)}")
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
        if not self.redis:
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
            
            logger.info(f"Сброшен счетчик неудачных попыток для IP {ip_address}" + 
                      (f" и пользователя {username}" if username else ""))
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при сбросе счетчика попыток: {str(e)}")
            return False

    async def close(self):
        """Закрывает соединение с Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Соединение с Redis для защиты от брутфорса закрыто")

# Глобальный экземпляр для использования в приложении
bruteforce_protection = BruteforceProtection() 