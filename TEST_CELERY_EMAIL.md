# Тестирование отправки email через Celery в auth_service

Это руководство по тестированию интеграции Celery для отправки email в сервисе аутентификации.

## Предварительные шаги

1. Настройте файл `.env` для Celery:

```bash
cd backend/celery_service
# Отредактируйте .env файл, добавив настройки SMTP для вашей почты
# Для Gmail потребуется создать пароль приложения: https://myaccount.google.com/apppasswords
nano .env
```

Пример содержимого `.env` файла:
```
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password  # пароль приложения, не ваш обычный пароль
MAIL_FROM=your_email@gmail.com
MAIL_PORT=465
MAIL_SERVER=smtp.gmail.com
MAIL_STARTTLS=False
MAIL_SSL_TLS=True
```

2. Установите необходимые зависимости для всех сервисов:

```bash
cd backend/auth_service
pip install -r requirements.txt

cd ../celery_service
pip install -r requirements.txt
```

## Запуск тестирования

1. Запустите Redis (если не запущен):

```bash
docker run -d --name redis-celery -p 6379:6379 redis:7.2-alpine
```

2. Запустите сервис Celery:

```bash
cd backend/celery_service
./run_dev.sh worker
```

3. В отдельном терминале запустите Flower для мониторинга задач:

```bash
cd backend/celery_service
./run_dev.sh flower
```

4. В третьем терминале запустите микросервис auth_service:

```bash
cd backend/auth_service
uvicorn main:app --reload --port 8000
```

## Тестирование отправки email

1. Откройте браузер и перейдите на страницу регистрации: http://localhost:3000/register

2. Заполните форму регистрации с валидными данными и отправьте.

3. После успешной регистрации проверьте:
   - Логи в терминале с Celery worker (должно быть сообщение о выполнении задачи `auth.send_verification_email`)
   - Мониторинг Flower: http://localhost:5555 (должна быть задача в статусе Completed)
   - Вашу почту (должно прийти письмо с ссылкой для активации)

## Проверка результатов

Если все настроено правильно:
1. В логах Celery worker вы увидите сообщение об успешной отправке email
2. На ваш email придет письмо со ссылкой для активации
3. В Flower вы увидите задачу `auth.send_verification_email` в статусе Completed

## Возможные проблемы и их решение

1. **Ошибка подключения к Redis**: Убедитесь, что Redis запущен и доступен на порту 6379.

2. **Ошибка аутентификации SMTP**: 
   - Проверьте правильность настроек SMTP в файле `.env`
   - Для Gmail убедитесь, что вы используете пароль приложения, а не обычный пароль
   - Проверьте, что двухфакторная аутентификация включена в вашей учетной записи Google

3. **Задача не отправляется**:
   - Проверьте логи auth_service на наличие ошибок
   - Убедитесь, что задача `auth.send_verification_email` правильно зарегистрирована в Celery

4. **Задача отправляется, но email не приходит**:
   - Проверьте папку Спам в вашей почте
   - Убедитесь, что порт 465 (или другой указанный) не блокируется файрволом 