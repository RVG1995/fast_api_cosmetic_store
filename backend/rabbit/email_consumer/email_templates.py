"""
Функции для создания HTML-содержимого email-сообщений.
"""
import logging
from datetime import datetime

from config import logger, settings

def create_order_email_content(order_data):
    """
    Создает HTML-содержимое для письма с подтверждением заказа
    
    Args:
        order_data (dict): Данные о заказе
        
    Returns:
        str: HTML-содержимое письма
    """
    items_html = ""
    total = 0
    
    for item in order_data.get('items', []):
        price = item.get('product_price', 0)
        quantity = item.get('quantity', 1)
        item_total = price * quantity
        total += item_total
        
        items_html += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.get('product_name', 'Товар')}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">{quantity}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{price:.2f} ₽</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{item_total:.2f} ₽</td>
        </tr>
        """
    
    # Получаем статус - может быть как строкой, так и словарем
    status = order_data.get('status', 'Новый')
    if isinstance(status, dict):
        status = status.get('name', 'Новый')
    
    # Форматируем дату из ISO формата в читаемый вид
    formatted_date = "Н/Д"
    created_at = order_data.get('created_at', '')
    
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))           
            formatted_date = f"{dt.day}-{dt.month}-{dt.year}"
        except ValueError as e:
            logger.warning("Ошибка при форматировании даты: %s", e)
            formatted_date = created_at.split('T')[0] if 'T' in created_at else created_at
    
    # Информация о промокоде и скидке
    discount_info = ""
    # Берем promo_code из promo_code или promo_code_dict
    promo_code = order_data.get('promo_code') or order_data.get('promo_code_dict')
    discount_amount = order_data.get('discount_amount', 0)
    
    if promo_code and discount_amount > 0:
        discount_percent = promo_code.get('discount_percent')
        if discount_percent:
            discount_info = f"""
            <tr>
                <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка по промокоду {promo_code.get('code')} ({discount_percent}%):</td>
                <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
            </tr>
            """
        else:
            discount_info = f"""
            <tr>
                <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка по промокоду {promo_code.get('code')}:</td>
                <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
            </tr>
            """
    elif discount_amount > 0:
        discount_info = f"""
        <tr>
            <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка:</td>
            <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
        </tr>
        """
    
    # Определяем, является ли пользователь незарегистрированным
    # Если user_id отсутствует, добавляем ссылку для отписки
    unsubscribe_section = ""
    email = order_data.get('email', '')
    order_id = order_data.get('id', '')
    
    if not order_data.get('user_id') and email and order_id:
        # Формируем ссылку для отписки
        unsubscribe_link = f"{settings.FRONTEND_URL}/orders/{order_id}/unsubscribe?email={email}"
        unsubscribe_section = f"""
        <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 12px; text-align: center;">
            <p>
                Вы получили это письмо, так как дали согласие на получение уведомлений о статусе заказа.<br>
                Если вы больше не хотите получать уведомления о заказе, <a href="{unsubscribe_link}" style="color: #4a5568;">нажмите здесь для отписки</a>
            </p>
        </div>
        """
    
    # Формируем HTML-шаблон
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Подтверждение заказа #{order_data.get('order_number')}</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h1 style="color: #4a5568; margin: 0;">Ваш заказ подтвержден</h1>
            <p style="font-size: 18px; margin-top: 10px;">Заказ #{order_data.get('order_number')}</p>
        </div>
        
        <div style="padding: 0 20px;">
            <p>Здравствуйте, {order_data.get('full_name', 'уважаемый клиент')}!</p>
            <p>Благодарим вас за заказ в нашем магазине. Ваш заказ был успешно создан и находится в обработке.</p>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные заказа:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Номер заказа:</strong></td>
                    <td>{order_data.get('order_number')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Дата:</strong></td>
                    <td>{formatted_date}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Статус:</strong></td>
                    <td>{status}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Способ оплаты:</strong></td>
                    <td>{order_data.get('payment_method', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Способ доставки:</strong></td>
                    <td>{order_data.get('delivery_method', 'Н/Д')}</td>
                </tr>
                {f'<tr><td style="padding: 5px 0;"><strong>Промокод:</strong></td><td>{promo_code.get("code")}</td></tr>' if promo_code else ''}
            </table>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Список товаров:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <thead>
                    <tr style="background-color: #f1f5f9;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Наименование</th>
                        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Кол-во</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Цена</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Сумма</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
                <tfoot>
                    {discount_info}
                    <tr>
                        <td colspan="3" style="padding: 10px; text-align: right; font-weight: bold;">Итого:</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{order_data.get('total_price', total):.2f} ₽</td>
                    </tr>
                </tfoot>
            </table>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные доставки:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Получатель:</strong></td>
                    <td>{order_data.get('full_name', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Телефон:</strong></td>
                    <td>{order_data.get('phone', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Email:</strong></td>
                    <td>{order_data.get('email', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Адрес доставки:</strong></td>
                    <td>
                        {order_data.get('region', '')}, 
                        {order_data.get('city', '')}, 
                        {order_data.get('street', '')},
                    </td>
                </tr>
            </table>
            
            <p>Мы свяжемся с вами, как только заказ будет готов к отправке.</p>
            <p>Если у вас возникли вопросы по заказу, напишите нам на электронную почту или позвоните по телефону поддержки.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;">
                <p>С уважением,<br>Команда "Косметик-стор"</p>
            </div>
            
            {unsubscribe_section}
        </div>
    </body>
    </html>
    """
    
    return html


def create_status_update_email_content(order_data):
    """
    Создает HTML-содержимое для письма с уведомлением об изменении статуса заказа
    
    Args:
        order_data (dict): Данные о заказе
        
    Returns:
        str: HTML-содержимое письма
    """
    # Получаем статус - может быть как строкой, так и словарем
    status = order_data.get('status', 'Новый')
    if isinstance(status, dict):
        status = status.get('name', 'Новый')

    # Отладочное логирование для промокода и скидки
    # Берем promo_code из promo_code или promo_code_dict
    promo_code = order_data.get('promo_code') or order_data.get('promo_code_dict')
    discount_amount = order_data.get('discount_amount', 0)
    
    if promo_code:
        logger.info("Промокод в create_status_update_email_content: %s", promo_code)
    else:
        logger.warning("Промокод отсутствует в create_status_update_email_content для заказа %s", order_data.get('order_number'))
        
    logger.info("Сумма скидки в create_status_update_email_content: %s", discount_amount)

    # Формируем таблицу с товарами
    items_html = ""
    total = 0
    
    for item in order_data.get('items', []):
        price = item.get('product_price', 0)
        quantity = item.get('quantity', 1)
        item_total = price * quantity
        total += item_total
        
        items_html += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.get('product_name', 'Товар')}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">{quantity}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{price:.2f} ₽</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{item_total:.2f} ₽</td>
        </tr>
        """

    # Форматируем дату из ISO формата в читаемый вид
    formatted_date = "Н/Д"
    created_at = order_data.get('created_at', '')
    
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))           
            formatted_date = f"{dt.day}-{dt.month}-{dt.year}"
        except ValueError as e:
            logger.warning("Ошибка при форматировании даты: %s", e)
            formatted_date = created_at.split('T')[0] if 'T' in created_at else created_at

    # Информация о промокоде и скидке
    discount_info = ""
    
    if promo_code and discount_amount > 0:
        discount_percent = promo_code.get('discount_percent')
        if discount_percent:
            discount_info = f"""
            <tr>
                <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка по промокоду {promo_code.get('code')} ({discount_percent}%):</td>
                <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
            </tr>
            """
        else:
            discount_info = f"""
            <tr>
                <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка по промокоду {promo_code.get('code')}:</td>
                <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
            </tr>
            """
    elif discount_amount > 0:
        discount_info = f"""
        <tr>
            <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка:</td>
            <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
        </tr>
        """
    
    # Определяем, является ли пользователь незарегистрированным
    # Если user_id отсутствует, добавляем ссылку для отписки
    unsubscribe_section = ""
    email = order_data.get('email', '')
    order_id = order_data.get('id', '')
    
    if not order_data.get('user_id') and email and order_id:
        # Формируем ссылку для отписки
        unsubscribe_link = f"{settings.FRONTEND_URL}/orders/{order_id}/unsubscribe?email={email}"
        unsubscribe_section = f"""
        <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 12px; text-align: center;">
            <p>
                Вы получили это письмо, так как дали согласие на получение уведомлений о статусе заказа.<br>
                Если вы больше не хотите получать уведомления о заказе, <a href="{unsubscribe_link}" style="color: #4a5568;">нажмите здесь для отписки</a>
            </p>
        </div>
        """
        
    # Формируем HTML-шаблон
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Изменение статуса заказа #{order_data.get('order_number')}</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h1 style="color: #4a5568; margin: 0;">Статус заказа изменен</h1>
            <p style="font-size: 18px; margin-top: 10px;">Заказ #{order_data.get('order_number')}</p>
        </div>
        
        <div style="padding: 0 20px;">
            <p>Здравствуйте, {order_data.get('full_name', 'уважаемый клиент')}!</p>
            <p>Статус вашего заказа был изменен на <strong>"{status}"</strong>.</p>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные заказа:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Номер заказа:</strong></td>
                    <td>{order_data.get('order_number')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Дата:</strong></td>
                    <td>{formatted_date}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Новый статус:</strong></td>
                    <td><strong>{status}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Сумма заказа:</strong></td>
                    <td>{order_data.get('total_price', 0):.2f} ₽</td>
                </tr>
                {f'<tr><td style="padding: 5px 0;"><strong>Промокод:</strong></td><td>{promo_code.get("code")}</td></tr>' if promo_code else ''}
            </table>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Список товаров:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <thead>
                    <tr style="background-color: #f1f5f9;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Наименование</th>
                        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Кол-во</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Цена</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Сумма</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
                <tfoot>
                    {discount_info}
                    <tr>
                        <td colspan="3" style="padding: 10px; text-align: right; font-weight: bold;">Итого:</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{order_data.get('total_price', total):.2f} ₽</td>
                    </tr>
                </tfoot>
            </table>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные доставки:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Получатель:</strong></td>
                    <td>{order_data.get('full_name', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Телефон:</strong></td>
                    <td>{order_data.get('phone', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Email:</strong></td>
                    <td>{order_data.get('email', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Адрес доставки:</strong></td>
                    <td>
                        {order_data.get('region', '')}, 
                        {order_data.get('city', '')}, 
                        {order_data.get('street', '')},
                    </td>
                </tr>
            </table>
            
            <p>Если у вас возникли вопросы по заказу, напишите нам на электронную почту или позвоните по телефону поддержки.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;">
                <p>С уважением,<br>Команда "Косметик-стор"</p>
            </div>
            
            {unsubscribe_section}
        </div>
    </body>
    </html>
    """
    
    return html


def create_registration_email_content(activation_data):
    """
    Создает HTML-содержимое для письма с подтверждением регистрации
    
    Args:
        activation_data (dict): Данные для активации аккаунта
        
    Returns:
        str: HTML-содержимое письма
    """
    activation_link = activation_data.get('activation_link', '#')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Подтверждение регистрации</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h1 style="color: #4a5568; margin: 0;">Подтверждение регистрации</h1>
            <p style="font-size: 18px; margin-top: 10px;">Kosmetik-Store</p>
        </div>
        
        <div style="padding: 0 20px;">
            <p>Здравствуйте!</p>
            <p>Благодарим вас за регистрацию в интернет-магазине Kosmetik-Store.</p>
            <p>Для завершения регистрации и активации вашей учетной записи, пожалуйста, нажмите на кнопку ниже:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{activation_link}" style="background-color: #4a5568; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">Подтвердить регистрацию</a>
            </div>
            
            <p>Если кнопка не работает, скопируйте и вставьте следующую ссылку в адресную строку браузера:</p>
            <p style="word-break: break-all; background-color: #f1f5f9; padding: 10px; border-radius: 4px;">{activation_link}</p>
            
            <p>Если вы не регистрировались на нашем сайте, проигнорируйте это письмо.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;">
                <p>С уважением,<br>Команда "Косметик-стор"</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def create_password_reset_email_content(reset_data):
    """
    Создает HTML-содержимое для письма со сбросом пароля
    
    Args:
        reset_data (dict): Данные для сброса пароля
        
    Returns:
        str: HTML-содержимое письма
    """
    reset_link = reset_data.get('reset_link', '#')
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='UTF-8'>
        <title>Сброс пароля</title>
    </head>
    <body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;'>
        <div style='background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;'>
            <h1 style='color: #4a5568; margin: 0;'>Сброс пароля</h1>
            <p style='font-size: 18px; margin-top: 10px;'>Kosmetik-Store</p>
        </div>
        <div style='padding: 0 20px;'>
            <p>Здравствуйте!</p>
            <p>Вы запросили сброс пароля для своей учетной записи.</p>
            <p>Для установки нового пароля, пожалуйста, нажмите на кнопку ниже:</p>
            <div style='text-align: center; margin: 30px 0;'>
                <a href='{reset_link}' style='background-color: #4a5568; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>Сбросить пароль</a>
            </div>
            <p>Если кнопка не работает, скопируйте и вставьте следующую ссылку в адресную строку браузера:</p>
            <p style='word-break: break-all; background-color: #f1f5f9; padding: 10px; border-radius: 4px;'>{reset_link}</p>
            <p>Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.</p>
            <div style='margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;'>
                <p>С уважением,<br>Команда "Косметик-стор"</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html 