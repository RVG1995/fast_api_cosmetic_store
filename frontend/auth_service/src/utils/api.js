import axios from 'axios';
import { API_URLS } from './constants';

/**
 * Создает экземпляр axios с настройками для указанного сервиса
 * @param {string} baseURL - Базовый URL сервиса
 * @returns {AxiosInstance} - Настроенный экземпляр axios
 */
const createApiInstance = (baseURL) => {
  return axios.create({
    baseURL,
    withCredentials: true,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 10000 // Таймаут в миллисекундах
  });
};

// Создаем отдельные экземпляры для каждого сервиса
const authApi = createApiInstance(API_URLS.AUTH);
const userApi = createApiInstance(API_URLS.USER);
const contentApi = createApiInstance(API_URLS.CONTENT);
const notificationApi = createApiInstance(API_URLS.NOTIFICATION);

// Интерцептор для обработки ошибок и отладки
const setupInterceptors = (api, serviceName) => {
  // Интерцептор запросов для отладки
  api.interceptors.request.use(
    (config) => {
      console.log(`[${serviceName} API] Запрос:`, { 
        url: config.url, 
        method: config.method,
        data: config.data,
        headers: config.headers
      });
      return config;
    },
    (error) => {
      console.error(`[${serviceName} API] Ошибка запроса:`, error);
      return Promise.reject(error);
    }
  );

  // Интерцептор ответов для отладки и обработки ошибок
  api.interceptors.response.use(
    (response) => {
      console.log(`[${serviceName} API] Успешный ответ:`, { 
        url: response.config.url,
        status: response.status,
        data: response.data
      });
      return response;
    },
    (error) => {
      console.error(`[${serviceName} API] Ошибка ответа:`, { 
        url: error.config?.url,
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      });
      
      // Обработка ошибок авторизации (401)
      if (error.response && error.response.status === 401) {
        console.log('Ошибка авторизации, перенаправление на страницу входа');
        // При необходимости можно добавить редирект на страницу входа
      }
      return Promise.reject(error);
    }
  );
  return api;
};

// Применяем интерцепторы ко всем API с названием сервиса для отладки
setupInterceptors(authApi, 'Auth');
setupInterceptors(userApi, 'User');
setupInterceptors(contentApi, 'Content');
setupInterceptors(notificationApi, 'Notification');

// API для работы с аутентификацией
export const authAPI = {
  login: (credentials) => {
    // Создаем объект FormData для отправки данных в формате x-www-form-urlencoded
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    return authApi.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
  },
  register: (userData) => authApi.post('/auth/register', userData),
  logout: () => authApi.post('/auth/logout'),
  getCurrentUser: () => authApi.get('/auth/users/me'),
  activateUser: (token) => authApi.get(`/auth/activate/${token}`),
};

// API для работы с пользователями
export const userAPI = {
  updateProfile: (userData) => userApi.patch('/users/me', userData),
  getUserById: (userId) => userApi.get(`/users/${userId}`),
  getUsers: (params) => userApi.get('/users', { params }),
};

// API для работы с админ-панелью 
export const adminAPI = {
  getAllUsers: () => authApi.get('/admin/users'),
  activateUser: (userId) => authApi.patch(`/admin/users/${userId}/activate`),
  makeAdmin: (userId) => authApi.patch(`/admin/users/${userId}/make-admin`),
  deleteUser: (userId) => authApi.delete(`/admin/users/${userId}`),
  checkAdminAccess: () => authApi.get('/admin/check-access'),
  checkSuperAdminAccess: () => authApi.get('/admin/check-super-access'),
};

// API для работы с контентом
export const contentAPI = {
  getArticles: () => contentApi.get('/articles'),
  getArticleById: (id) => contentApi.get(`/articles/${id}`),
  createArticle: (data) => contentApi.post('/articles', data),
  updateArticle: (id, data) => contentApi.put(`/articles/${id}`, data),
  deleteArticle: (id) => contentApi.delete(`/articles/${id}`),
};

// API для работы с уведомлениями
export const notificationAPI = {
  getNotifications: () => notificationApi.get('/notifications'),
  markAsRead: (id) => notificationApi.patch(`/notifications/${id}/read`),
  deleteNotification: (id) => notificationApi.delete(`/notifications/${id}`),
};

// Экспортируем все API и инстансы для возможного прямого использования
export default {
  authApi,
  userApi,
  contentApi,
  notificationApi,
  authAPI,
  userAPI,
  adminAPI,
  contentAPI,
  notificationAPI
}; 