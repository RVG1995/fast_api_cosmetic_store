import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List
from models import OrderModel, OrderItemModel
from schema import OrderSchema
import jinja2
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("order_email_service")

# Настройки SMTP
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@cosmetic-store.com")
EMAIL_ADMIN = os.getenv("EMAIL_ADMIN", "admin@cosmetic-store.com")

# Настройка Jinja2 для шаблонов писем
template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(os.path.dirname(__file__), "templates"))
template_env = jinja2.Environment(loader=template_loader)

class EmailService:
    """Сервис для отправки электронных писем"""
    
    @staticmethod
    def _render_template(template_name: str, context: Dict[str, Any]) -> str:
        """
        Рендеринг шаблона письма
        
        Args:
            template_name: Имя шаблона
            context: Контекст для рендеринга
            
        Returns:
            str: Отрендеренный HTML-код письма
        """
        try:
            template = template_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Ошибка при рендеринге шаблона {template_name}: {str(e)}")
            # Возвращаем простой текст в случае ошибки
            return f"Заказ №{context.get('order_number', 'N/A')} был создан."
    
    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Отправка электронного письма
        
        Args:
            to_email: Email получателя
            subject: Тема письма
            html_content: HTML-содержимое письма
            cc: Копия (Carbon Copy)
            bcc: Скрытая копия (Blind Carbon Copy)
            
        Returns:
            bool: Успешность отправки
        """
        # Проверка наличия настроек SMTP
        if not all([SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD]):
            logger.warning("Настройки SMTP не полностью указаны, отправка почты не выполнена")
            return False
        
        try:
            # Создаем письмо
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = EMAIL_FROM
            message["To"] = to_email
            
            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)
            
            # Добавляем HTML-версию
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Список всех получателей
            all_recipients = [to_email]
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # Отправляем письмо
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, all_recipients, message.as_string())
            
            logger.info(f"Письмо успешно отправлено на {to_email}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке письма на {to_email}: {str(e)}")
            return False
    
    @classmethod
    async def send_order_confirmation(cls, order: OrderSchema) -> bool:
        """
        Отправка письма с подтверждением заказа
        
        Args:
            order: Данные заказа
            
        Returns:
            bool: Успешность отправки
        """
        if not order.contact_email:
            logger.warning(f"Не указан email для заказа {order.id}, письмо не отправлено")
            return False
        
        try:
            # Подготавливаем контекст для шаблона
            context = {
                "order": order,
                "order_number": order.order_number,
                "order_date": order.created_at.strftime("%d.%m.%Y %H:%M"),
                "total_price": order.total_price,
                "shipping_address": order.shipping_address or "Не указан",
                "contact_phone": order.contact_phone or "Не указан",
                "contact_email": order.contact_email,
                "items": order.items,
                "status": order.status.name if order.status else "Новый",
                "current_year": datetime.now().year
            }
            
            # Рендерим шаблон
            html_content = cls._render_template("order_confirmation.html", context)
            
            # Отправляем письмо
            subject = f"Заказ №{order.order_number} в магазине косметики"
            bcc = [EMAIL_ADMIN]  # Отправляем копию администратору
            
            return await cls.send_email(order.contact_email, subject, html_content, bcc=bcc)
        except Exception as e:
            logger.error(f"Ошибка при отправке письма с подтверждением заказа {order.id}: {str(e)}")
            return False
    
    @classmethod
    async def send_order_status_update(cls, order: OrderSchema, old_status_name: str) -> bool:
        """
        Отправка письма об изменении статуса заказа
        
        Args:
            order: Данные заказа
            old_status_name: Название предыдущего статуса
            
        Returns:
            bool: Успешность отправки
        """
        if not order.contact_email:
            logger.warning(f"Не указан email для заказа {order.id}, письмо об изменении статуса не отправлено")
            return False
        
        try:
            # Подготавливаем контекст для шаблона
            context = {
                "order": order,
                "order_number": order.order_number,
                "old_status": old_status_name,
                "new_status": order.status.name if order.status else "Неизвестный",
                "order_date": order.created_at.strftime("%d.%m.%Y %H:%M"),
                "status_updated_at": order.updated_at.strftime("%d.%m.%Y %H:%M"),
                "total_price": order.total_price,
                "shipping_address": order.shipping_address or "Не указан",
                "contact_phone": order.contact_phone or "Не указан",
                "contact_email": order.contact_email,
                "current_year": datetime.now().year
            }
            
            # Рендерим шаблон
            html_content = cls._render_template("order_status_update.html", context)
            
            # Отправляем письмо
            subject = f"Изменение статуса заказа №{order.order_number} в магазине косметики"
            
            return await cls.send_email(order.contact_email, subject, html_content)
        except Exception as e:
            logger.error(f"Ошибка при отправке письма об изменении статуса заказа {order.id}: {str(e)}")
            return False 