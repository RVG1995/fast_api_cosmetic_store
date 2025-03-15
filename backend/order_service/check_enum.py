import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

from database import DATABASE_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("check_enum")

# Загрузка переменных окружения
load_dotenv()

# Создание подключения к базе данных
engine = create_async_engine(DATABASE_URL)

async def check_payment_method_enum():
    """
    Проверка значений типа перечисления для методов оплаты в PostgreSQL
    """
    async with engine.begin() as conn:
        # Запрос значений перечисления
        enum_values_query = text("""
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'paymentmethodenum'
            ORDER BY e.enumsortorder
        """)
        result = await conn.execute(enum_values_query)
        values = result.fetchall()
        
        logger.info("Значения перечисления paymentmethodenum:")
        for value in values:
            logger.info(f"- {value[0]}")
        
        return values

async def main():
    try:
        await check_payment_method_enum()
    except Exception as e:
        logger.error(f"Ошибка при проверке типа перечисления: {str(e)}")
    
    # Закрываем соединение с базой данных
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main()) 