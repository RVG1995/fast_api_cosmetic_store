/**
 * Файл с константами для приложения
 */

// Базовый URL API для хука useApi
export const API_URL = 'http://localhost:8088/api';

// API URLs для различных сервисов
export const API_URLS = {
  AUTH_SERVICE: 'http://localhost:8088/api',
  PRODUCT_SERVICE: 'http://localhost:8088/api',
  PRODUCT: 'http://localhost:8088/api',
  CART_SERVICE: 'http://localhost:8088/api',
  ORDER_SERVICE: 'http://localhost:8088/api',
  REVIEW_SERVICE: 'http://localhost:8088/api',
  PAYMENT_SERVICE: 'http://localhost:8088/api',
  USER: 'http://localhost:8088/api',
  CONTENT: 'http://localhost:8088/api',
  NOTIFICATION: 'http://localhost:8088/api',
  NOTIFICATION_SERVICE_URL: 'http://localhost:8088/api',
  DELIVERY_SERVICE: 'http://localhost:8088/api',
  FAVORITE_SERVICE: 'http://localhost:8088/api/favorites'
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
  USER_DATA: 'user_data',
  CART_DATA: 'cart_data'
}; 