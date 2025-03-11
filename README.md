# Личный сайт с микросервисной архитектурой

Проект представляет собой веб-приложение, построенное с использованием микросервисной архитектуры. Включает сервисы аутентификации, управления пользователями, контентом и уведомлениями.

## Структура проекта

```
/
├── backend/            # Бэкенд на FastAPI
│   ├── auth_service/   # Сервис аутентификации
│   └── ...
└── frontend/           # Фронтенд на React
    ├── auth_service/   # Клиентская часть для аутентификации
    └── ...
```

## Технологии

### Бэкенд:
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- JWT для аутентификации

### Фронтенд:
- React
- React Router
- Axios
- Bootstrap
- Context API для управления состоянием

## Начало работы

### Установка и запуск бэкенда

1. Создайте виртуальное окружение и активируйте его:
   ```bash
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   ```

2. Установите зависимости:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Создайте файл `.env` в директории `backend/auth_service` с необходимыми переменными окружения:
   ```
   DATABASE_URL=postgresql://user:password@localhost/db_name
   SECRET_KEY=your_secret_key
   MAIL_USERNAME=your_email@example.com
   MAIL_PASSWORD=your_email_password
   MAIL_FROM=your_email@example.com
   MAIL_PORT=587
   MAIL_SERVER=smtp.example.com
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=admin_password
   ```

4. Запустите сервис аутентификации:
   ```bash
   cd backend/auth_service
   python main.py
   ```

### Установка и запуск фронтенда

1. Установите зависимости:
   ```bash
   cd frontend/auth_service
   npm install
   ```

2. Запустите фронтенд:
   ```bash
   npm start
   ```

## Функциональность

- Регистрация и аутентификация пользователей
- Активация учетной записи по email
- Административная панель для управления пользователями
- Личный кабинет пользователя

## Микросервисы

- **Auth Service** (порт 8001): Управление аутентификацией и авторизацией
- **User Service** (порт 8002): Управление пользовательскими данными
- **Content Service** (порт 8003): Управление контентом
- **Notification Service** (порт 8004): Управление уведомлениями 