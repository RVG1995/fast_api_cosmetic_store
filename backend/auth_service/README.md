# Auth Service

## Настройка окружения

1. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

2. Заполните переменные окружения в файле `.env`:
- `MAIL_USERNAME` - email адрес для отправки писем
- `MAIL_PASSWORD` - пароль от почты (для Gmail нужно использовать пароль приложения)
- `MAIL_FROM` - email адрес отправителя
- `MAIL_PORT` - порт SMTP сервера (по умолчанию 587 для Gmail, 465 для Yandex)
- `MAIL_SERVER` - SMTP сервер (например, smtp.gmail.com или smtp.yandex.ru)
- `MAIL_STARTTLS` - использовать STARTTLS (True/False)
- `MAIL_SSL_TLS` - использовать SSL/TLS (True/False)

### Настройка почтового сервера

#### Для Gmail:
1. Включите двухфакторную аутентификацию в настройках Google Account
2. Создайте пароль приложения:
   - Перейдите в настройки безопасности Google Account
   - Найдите "Пароли приложений"
   - Создайте новый пароль для приложения
   - Используйте этот пароль в `MAIL_PASSWORD`
   - Используйте порт 587 и STARTTLS=True

#### Для Yandex:
1. Включите доступ к почте с помощью пароля приложения
2. Создайте пароль приложения в настройках
3. Используйте порт 465 и SSL_TLS=True

## Установка зависимостей
```bash
pip install -r requirements.txt
``` 