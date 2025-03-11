/**
 * Файл с константами для приложения
 */

// API URLs для различных микросервисов
export const API_URLS = {
  AUTH: 'http://localhost:8001',       // Сервис аутентификации
  USER: 'http://localhost:8002',       // Сервис пользователей
  CONTENT: 'http://localhost:8003',    // Сервис контента
  NOTIFICATION: 'http://localhost:8004' // Сервис уведомлений
};

// Маршруты
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  ACTIVATE: '/activate',
  USER: '/user',
  ADMIN: '/admin',
  ADMIN_USERS: '/admin/users',
  ADMIN_PERMISSIONS: '/admin/permissions',
  REGISTRATION_CONFIRMATION: '/registration-confirmation'
};

// Сообщения об ошибках
export const ERROR_MESSAGES = {
  LOGIN_FAILED: 'Неверный email или пароль',
  REGISTRATION_FAILED: 'Ошибка при регистрации. Пожалуйста, попробуйте позже.',
  SERVER_ERROR: 'Ошибка соединения с сервером',
  UNAUTHORIZED: 'Необходимо войти в систему',
  FORBIDDEN: 'Недостаточно прав для доступа',
  ACTIVATION_REQUIRED: 'Пожалуйста, подтвердите свой email'
};

// Задержки и таймауты
export const TIMEOUTS = {
  REDIRECT_AFTER_ACTIVATION: 1500,  // ms
  REDIRECT_AFTER_LOGIN: 500,       // ms
  SESSION_TIMEOUT: 30 * 60 * 1000  // 30 минут
};

// Локальные ключи хранилища
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_DATA: 'user_data'
}; 