"""
Утилиты для работы с email и шаблонами.
"""
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib

from config import settings, TEMPLATES_DIR, logger

async def send_email(recipient: str, subject: str, html_content: str) -> None:
    """
    Отправляет email с помощью aiosmtplib
    
    Args:
        recipient: Email получателя
        subject: Тема письма
        html_content: HTML-содержимое письма
    """
    # Создаем сообщение
    message = MIMEMultipart()
    message["From"] = settings.SMTP_FROM
    message["To"] = recipient
    message["Subject"] = subject
    
    # Добавляем HTML-содержимое
    message.attach(MIMEText(html_content, "html"))
    
    try:
        # Отправляем письмо
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=True
        )
        logger.info("Письмо успешно отправлено на %s", recipient)
    except Exception as e:
        error_msg = f"Ошибка при отправке письма: {e}"
        logger.error(error_msg)
        raise


def load_template(template_name: str) -> str:
    """
    Загружает HTML шаблон из файла
    
    Args:
        template_name: Имя файла шаблона (без пути)
    
    Returns:
        str: Содержимое шаблона
    """
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError as e:
        logger.error("Файл не найден: %s", e)
        raise
    except OSError as e:
        logger.error("Непредвиденная ошибка: %s", e)
        raise 