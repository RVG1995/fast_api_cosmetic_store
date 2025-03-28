/**
 * Файл с константами для приложения
 */

// Базовый URL API для хука useApi
export const API_URL = 'http://localhost:8000';

// API URLs для различных сервисов
export const API_URLS = {
  AUTH_SERVICE: process.env.REACT_APP_AUTH_SERVICE_URL || 'http://localhost:8000',
  PRODUCT_SERVICE: process.env.REACT_APP_PRODUCT_SERVICE_URL || 'http://localhost:8001',
  PRODUCT: process.env.REACT_APP_PRODUCT_SERVICE_URL || 'http://localhost:8001',
  CART_SERVICE: process.env.REACT_APP_CART_SERVICE_URL || 'http://localhost:8002',
  ORDER_SERVICE: process.env.REACT_APP_ORDER_SERVICE_URL || 'http://localhost:8003',
  REVIEW_SERVICE: process.env.REACT_APP_REVIEW_SERVICE_URL || 'http://localhost:8004',
  PAYMENT_SERVICE: process.env.REACT_APP_PAYMENT_SERVICE_URL || 'http://localhost:8005',
  USER: 'http://localhost:8006',       // Сервис пользователей (если будет)
  CONTENT: 'http://localhost:8007',    // Сервис контента (если будет)
  NOTIFICATION: 'http://localhost:8008' // Сервис уведомлений (если будет)
};

// Маршруты
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  ACTIVATE: '/activate',
  USER: '/user',
  USER_CHANGE_PASSWORD: '/user/change-password',
  ADMIN: '/admin',
  ADMIN_USERS: '/admin/users',
  ADMIN_PERMISSIONS: '/admin/permissions',
  ADMIN_PRODUCTS: '/admin/products',
  ADMIN_CATEGORIES: '/admin/categories',
  ADMIN_SUBCATEGORIES: '/admin/subcategories',
  ADMIN_BRANDS: '/admin/brands',
  ADMIN_COUNTRIES: '/admin/countries',
  ADMIN_CARTS: '/admin/carts',
  ADMIN_REVIEWS: '/admin/reviews',
  REGISTRATION_CONFIRMATION: '/registration-confirmation',
  PRODUCTS: '/products',
  CATEGORIES: '/categories',
  BRANDS: '/brands',
  CART: '/cart',
  REVIEWS: '/reviews'
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