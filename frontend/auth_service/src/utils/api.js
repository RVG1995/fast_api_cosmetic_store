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
    // Не устанавливаем Content-Type здесь, чтобы axios мог определить правильный заголовок
    // в зависимости от типа данных
    timeout: 10000 // Таймаут в миллисекундах
  });
};

// Создаем отдельные экземпляры для каждого сервиса
const authApi = createApiInstance(API_URLS.AUTH);
const userApi = createApiInstance(API_URLS.USER);
const contentApi = createApiInstance(API_URLS.CONTENT);
const notificationApi = createApiInstance(API_URLS.NOTIFICATION);
const productApi = createApiInstance(API_URLS.PRODUCT);

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
      
      // Добавляем bearer токен в заголовок Authorization, если он есть в localStorage
      const token = localStorage.getItem('access_token');
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
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
      
      // Проверяем, содержит ли ответ новый токен
      if (response.data && response.data.access_token) {
        console.log(`[${serviceName} API] Получен новый токен в ответе`);
        localStorage.setItem('access_token', response.data.access_token);
      }
      
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
        // Удаляем токен при 401 ошибке
        localStorage.removeItem('access_token');
        // При необходимости можно добавить редирект на страницу входа
        // window.location.href = '/login';
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
setupInterceptors(productApi, 'Product');

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
    }).then(response => {
      // Сохраняем токен в localStorage
      if (response.data && response.data.access_token) {
        localStorage.setItem('access_token', response.data.access_token);
        console.log('Токен сохранен в localStorage из login API');
      }
      return response;
    });
  },
  register: (userData) => authApi.post('/auth/register', userData),
  logout: () => authApi.post('/auth/logout').then(response => {
    // Удаляем токен из localStorage
    localStorage.removeItem('access_token');
    console.log('Токен удален из localStorage из logout API');
    return response;
  }),
  getCurrentUser: () => authApi.get('/auth/users/me'),
  activateUser: (token) => authApi.get(`/auth/activate/${token}`).then(response => {
    // Сохраняем токен в localStorage при активации
    if (response.data && response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      console.log('Токен сохранен в localStorage из activate API');
    }
    return response;
  }),
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

// API для работы с продуктами
export const productAPI = {
  // Продукты
  getProducts: () => {
    return productApi.get('/products').then(response => {
      console.log('API getProducts response:', response.data);
      return response;
    });
  },
  getProductById: (id) => productApi.get(`/products/${id}`),
  
  // Заменяем метод createProduct для поддержки загрузки файлов
  createProduct: (data) => {
    console.log('createProduct вызван с данными:', data);
    
    // Проверка наличия всех обязательных полей
    const requiredFields = ['name', 'price', 'stock', 'country_id', 'brand_id', 'category_id'];
    const missingFields = requiredFields.filter(field => !data[field] && data[field] !== 0);
    
    if (missingFields.length > 0) {
      console.error('Отсутствуют обязательные поля:', missingFields);
      return Promise.reject(new Error(`Отсутствуют обязательные поля: ${missingFields.join(', ')}`));
    }
    
    // Если данные включают файл изображения, используем FormData
    if (data.image instanceof File) {
      console.log('Используем FormData для отправки с изображением');
      const formData = new FormData();
      
      // Добавляем все поля данных в FormData
      formData.append('name', data.name);
      formData.append('price', data.price.toString());
      if (data.description) {
        formData.append('description', data.description);
      }
      formData.append('stock', data.stock.toString());
      formData.append('country_id', data.country_id.toString());
      formData.append('brand_id', data.brand_id.toString());
      formData.append('category_id', data.category_id.toString());
      
      // Добавляем subcategory_id, если оно существует
      if (data.subcategory_id) {
        formData.append('subcategory_id', data.subcategory_id.toString());
      }
      
      // Добавляем файл изображения
      formData.append('image', data.image);
      
      console.log('FormData готова для отправки:', {
        name: data.name,
        price: data.price,
        description: data.description,
        stock: data.stock,
        category_id: data.category_id,
        subcategory_id: data.subcategory_id,
        country_id: data.country_id,
        brand_id: data.brand_id,
        image: data.image.name
      });
      
      // Отправляем на эндпоинт /products
      return productApi.post('/products', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
    } else {
      // Даже если изображения нет, все равно используем FormData для совместимости с апи
      console.log('Используем FormData для отправки без изображения');
      const formData = new FormData();
      
      // Добавляем все поля данных в FormData
      formData.append('name', data.name);
      formData.append('price', data.price.toString());
      if (data.description) {
        formData.append('description', data.description);
      }
      formData.append('stock', data.stock.toString());
      formData.append('country_id', data.country_id.toString());
      formData.append('brand_id', data.brand_id.toString());
      formData.append('category_id', data.category_id.toString());
      
      // Добавляем subcategory_id, если оно существует
      if (data.subcategory_id) {
        formData.append('subcategory_id', data.subcategory_id.toString());
      }
      
      return productApi.post('/products', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
    }
  },
  
  // Обновляем метод updateProduct с поддержкой загрузки файлов
  updateProduct: (id, data) => {
    console.log(`updateProduct вызван для ID=${id} с данными:`, data);
    
    // Всегда используем FormData для универсальности
    const formData = new FormData();
    
    // Добавляем все поля данных в FormData с правильной конвертацией типов
    if (data.name) formData.append('name', data.name);
    if (data.price !== undefined) formData.append('price', data.price.toString());
    if (data.description !== undefined) formData.append('description', data.description);
    if (data.stock !== undefined) formData.append('stock', data.stock.toString());
    if (data.country_id) formData.append('country_id', data.country_id.toString());
    if (data.brand_id) formData.append('brand_id', data.brand_id.toString());
    if (data.category_id) formData.append('category_id', data.category_id.toString());
    
    // Явно проверяем subcategory_id, даже если это пустая строка или null
    if (data.subcategory_id) {
      formData.append('subcategory_id', data.subcategory_id.toString());
    } else if (data.subcategory_id === '' || data.subcategory_id === null) {
      // Явно указываем пустую строку для отсутствующей подкатегории
      formData.append('subcategory_id', '');
    }
    
    // Добавляем файл изображения, только если он есть
    if (data.image instanceof File) {
      formData.append('image', data.image);
      console.log('Добавлено изображение:', data.image.name);
    }
    
    console.log('FormData готова для отправки');
    
    // Отправляем всегда на эндпоинт /products/{id}/form
    return productApi.put(`/products/${id}/form`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  deleteProduct: (id) => productApi.delete(`/products/${id}`),
  
  // Категории
  getCategories: () => productApi.get('/categories'),
  getCategoryById: (id) => productApi.get(`/categories/${id}`),
  createCategory: (data) => productApi.post('/categories', data),
  updateCategory: (id, data) => productApi.put(`/categories/${id}`, data),
  deleteCategory: (id) => productApi.delete(`/categories/${id}`),
  
  // Бренды
  getBrands: () => productApi.get('/brands'),
  getBrandById: (id) => productApi.get(`/brands/${id}`),
  createBrand: (data) => productApi.post('/brands', data),
  updateBrand: (id, data) => productApi.put(`/brands/${id}`, data),
  deleteBrand: (id) => productApi.delete(`/brands/${id}`),
  
  // Страны
  getCountries: () => productApi.get('/countries'),
  getCountryById: (id) => productApi.get(`/countries/${id}`),
  createCountry: (data) => productApi.post('/countries', data),
  updateCountry: (id, data) => productApi.put(`/countries/${id}`, data),
  deleteCountry: (id) => productApi.delete(`/countries/${id}`),
  
  // Подкатегории
  getSubcategories: () => productApi.get('/subcategories'),
  getSubcategoryById: (id) => productApi.get(`/subcategories/${id}`),
  createSubcategory: (data) => productApi.post('/subcategories', data),
  updateSubcategory: (id, data) => productApi.put(`/subcategories/${id}`, data),
  deleteSubcategory: (id) => productApi.delete(`/subcategories/${id}`),
};

// Экспортируем все API и инстансы для возможного прямого использования
const apiExports = {
  authApi,
  userApi,
  contentApi,
  notificationApi,
  productApi,
  authAPI,
  userAPI,
  adminAPI,
  contentAPI,
  notificationAPI,
  productAPI
};

export default apiExports; 