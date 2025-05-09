import axios from 'axios';
import { API_URLS } from './constants';

/**
 * Создает экземпляр axios с настройками для указанного сервиса
 * @param {string} baseURL - Базовый URL сервиса
 * @returns {AxiosInstance} - Настроенный экземпляр axios
 */
const createApiInstance = (baseURL) => {
  const instance = axios.create({
    baseURL,
    withCredentials: true,  // Важно для автоматической передачи куки
    xsrfCookieName: false,  // Отключаем XSRF для упрощения
    timeout: 10000 // Таймаут в миллисекундах
  });
  
  return instance;
};

// Создаем отдельные экземпляры для каждого сервиса
const authApi = createApiInstance(API_URLS.AUTH_SERVICE);
const userApi = createApiInstance(API_URLS.USER);
const contentApi = createApiInstance(API_URLS.CONTENT);
const notificationApi = createApiInstance(API_URLS.NOTIFICATION);
const productApi = createApiInstance(API_URLS.PRODUCT_SERVICE);
const cartApi = createApiInstance(API_URLS.CART_SERVICE);
const orderApi = createApiInstance(API_URLS.ORDER_SERVICE);
const reviewApi = createApiInstance(API_URLS.REVIEW_SERVICE);

// Интерцептор для обработки ошибок и отладки
const setupInterceptors = (api, serviceName) => {
  // Интерцептор запросов для отладки
  api.interceptors.request.use(
    (config) => {
      console.log(`[${serviceName} API] Запрос:`, { 
        url: config.url, 
        method: config.method,
        data: config.data,
        headers: config.headers,
        withCredentials: config.withCredentials,
        cookies: document.cookie // Выводим текущие куки
      });
      
      // Гарантируем передачу куки для каждого запроса
      config.withCredentials = true;
      
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
      
      // Проверяем, содержит ли ответ новый токен и сохраняем его для межсервисной передачи
      if (response.data && response.data.access_token) {
        console.log(`[${serviceName} API] Получен новый токен в ответе, сохраняем его для микросервисов`);
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
        console.log('Ошибка авторизации (401): Токен истек или недействителен');
        // Не делаем window.location.href! Пусть обработка будет на уровне компонентов/guard'ов
        // window.location.href = '/login?expired=true';
        // Можно тут диспатчить глобальный алерт, если нужно
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
setupInterceptors(cartApi, 'Cart');
setupInterceptors(orderApi, 'Order');
setupInterceptors(reviewApi, 'Review');

// API для работы с аутентификацией
export const authAPI = {
  login: async (credentials) => {
    // Создаем объект FormData для отправки данных в формате x-www-form-urlencoded
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    return await authApi.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
  },
  register: async (userData) => {
    // Убедимся, что поля соответствуют ожидаемым на бэкенде
    const registrationData = {
      first_name: userData.first_name,
      last_name: userData.last_name,
      email: userData.email,
      password: userData.password,
      confirm_password: userData.confirm_password,
      personal_data_agreement: userData.personal_data_agreement || false,
      notification_agreement: userData.notification_agreement || false
    };
    
    return await authApi.post('/auth/register', registrationData);
  },
  logout: async () => await authApi.post('/auth/logout'),
  getCurrentUser: async () => await authApi.get('/auth/users/me'),
  getUserProfile: async () => await authApi.get('/auth/users/me/profile'),
  checkPermissions: async (permission, resourceType, resourceId) => {
    const params = {};
    if (permission) params.permission = permission;
    if (resourceType) params.resource_type = resourceType;
    if (resourceId) params.resource_id = resourceId;
    
    console.log('authAPI: Запрос проверки разрешений с параметрами:', params);
    
    try {
      // Прямой вызов эндпоинта с правильным URL относительно базового URL сервиса
      const response = await authApi.get('/auth/users/me/permissions', { 
        params,
        withCredentials: true,  // Гарантируем отправку куки
      });
      console.log('authAPI: Успешный ответ проверки разрешений:', response.data);
      return response;
    } catch (error) {
      console.error('authAPI: Ошибка проверки разрешений:', error.response?.data || error.message);
      console.error('authAPI: Статус ошибки:', error.response?.status);
      throw error;
    }
  },
  activateUser: async (token) => await authApi.get(`/auth/activate/${token}`),
  changePassword: async (passwordData) => await authApi.post('/auth/change-password', passwordData),
  updateProfile: async (profileData) => await authApi.patch('/auth/users/me/profile', profileData),
  requestPasswordReset: async (email) => await authApi.post('/auth/request-password-reset', { email }),
  resetPassword: async ({ token, new_password, confirm_password }) => await authApi.post('/auth/reset-password', { token, new_password, confirm_password }),
  
  // Методы для работы с сессиями
  getUserSessions: async () => await authApi.get('/auth/users/me/sessions'),
  revokeSession: async (sessionId) => await authApi.post(`/auth/users/me/sessions/${sessionId}/revoke`),
  revokeAllSessions: async () => await authApi.post('/auth/users/me/sessions/revoke-all'),
};

// API для работы с пользователями
export const userAPI = {
  updateProfile: async (userData) => await userApi.patch('/users/me', userData),
  getUserById: async (userId) => await userApi.get(`/users/${userId}`),
  getUsers: async (params) => await userApi.get('/users', { params }),
};

// API для работы с админ-панелью 
export const adminAPI = {
  getAllUsers: async () => await authApi.get('/auth/all/users'),
  createUser: async (userData) => {
    const { is_admin, ...userFields } = userData;
    return await authApi.post('/auth/users', userFields, { params: { is_admin } });
  },
  activateUser: async (userId) => await authApi.patch(`/admin/users/${userId}/activate`),
  makeAdmin: async (userId) => await authApi.patch(`/admin/users/${userId}/make-admin`),
  removeAdmin: async (userId) => await authApi.patch(`/admin/users/${userId}/remove-admin`),
  deleteUser: async (userId) => await authApi.delete(`/admin/users/${userId}`),
  toggleUserActive: async (userId) => await authApi.patch(`/auth/users/${userId}/toggle-active`),
  checkAdminAccess: async () => await authApi.get('/admin/check-access'),
  checkSuperAdminAccess: async () => await authApi.get('/admin/check-super-access'),
  
  // Статистика
  getDashboardStats: async () => {
    try {
      // Получаем количество пользователей
      const usersResponse = await authApi.get('/admin/users');
      const usersCount = usersResponse.data.length || 0;
      
      // Получаем количество товаров
      const productsResponse = await productApi.get('products/admin', { 
        params: { page: 1, limit: 1 } 
      });
      const productsCount = productsResponse.data.total || 0;
      
      // Получаем количество заказов и статистику по заказам
      const ordersApi = createApiInstance(API_URLS.ORDER_SERVICE);
      setupInterceptors(ordersApi, 'Orders');
      
      // Получаем общую статистику заказов
      const orderStatsResponse = await ordersApi.get('/admin/orders/statistics');
      const orderStats = orderStatsResponse.data || {};
      
      // Получаем количество заказов
      const ordersResponse = await ordersApi.get('/admin/orders', {
        params: { page: 1, size: 1 }
      });
      const ordersCount = ordersResponse.data.total || 0;
      
      // Общая сумма заказов
      const totalOrdersRevenue = orderStats.total_revenue || 0;
      
      return {
        usersCount,
        productsCount,
        ordersCount,
        totalOrdersRevenue
      };
    } catch (error) {
      console.error('Ошибка при получении статистики для админ-панели:', error);
      // Возвращаем значения по умолчанию в случае ошибки
      return {
        usersCount: 0,
        productsCount: 0,
        ordersCount: 0,
        totalOrdersRevenue: 0
      };
    }
  },
  
  // Получение статистики по заказам за указанный период
  getOrderStatsByDate: async (dateFrom = null, dateTo = null) => {
    try {
      const ordersApi = createApiInstance(API_URLS.ORDER_SERVICE);
      setupInterceptors(ordersApi, 'Orders');
      
      // Формируем параметры запроса
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      
      console.log('Запрос статистики заказов по периоду с параметрами:', params);
      
      // Получаем статистику заказов за указанный период
      const response = await ordersApi.get('/admin/orders/statistics/report', { params });
      
      return response.data;
    } catch (error) {
      console.error('Ошибка при получении статистики заказов по периоду:', error);
      throw error;
    }
  },
  
  // Генерация отчета по заказам
  generateOrderReport: async (format, dateFrom = null, dateTo = null) => {
    try {
      const ordersApi = createApiInstance(API_URLS.ORDER_SERVICE);
      setupInterceptors(ordersApi, 'Orders');
      
      // Формируем параметры запроса
      const params = { format };
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      
      console.log('Запрос генерации отчета по заказам с параметрами:', params);
      
      // Запрашиваем отчет в нужном формате
      const response = await ordersApi.get('/admin/orders/reports/download', { 
        params,
        responseType: 'blob' // Указываем, что ответ ожидается в виде файла
      });
      
      // Создаем временную ссылку для скачивания файла
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      // Формируем имя файла в зависимости от формата
      const date = new Date().toISOString().split('T')[0];
      let filename = `orders_report_${date}`;
      
      // Добавляем правильное расширение файла
      switch(format.toLowerCase()) {
        case 'csv':
          filename += '.csv';
          break;
        case 'excel':
          filename += '.xlsx';
          break;
        case 'pdf':
          filename += '.pdf';
          break;
        case 'word':
          filename += '.docx';
          break;
        default:
          filename += `.${format.toLowerCase()}`;
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      
      // Удаляем ссылку
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      return true;
    } catch (error) {
      console.error('Ошибка при получении отчета:', error);
      throw error;
    }
  }
};

// API для работы с контентом
export const contentAPI = {
  getArticles: async () => await contentApi.get('/articles'),
  getArticleById: async (id) => await contentApi.get(`/articles/${id}`),
  createArticle: async (data) => await contentApi.post('/articles', data),
  updateArticle: async (id, data) => await contentApi.put(`/articles/${id}`, data),
  deleteArticle: async (id) => await contentApi.delete(`/articles/${id}`),
};

// API для работы с уведомлениями
export const notificationAPI = {
  getNotifications: async () => await notificationApi.get('/notifications'),
  markAsRead: async (id) => await notificationApi.patch(`/notifications/${id}/read`),
  deleteNotification: async (id) => await notificationApi.delete(`/notifications/${id}`),
  // Методы для работы с настройками уведомлений
  getSettings: async () => {
    const { data } = await notificationApi.get('/notifications/settings');
    return data;
  },
  updateSetting: async (eventType, payload) => {
    const { data } = await notificationApi.patch(
      '/notifications/settings',
      payload,
      { params: { event_type: eventType } }
    );
    return data;
  }
};

// API для работы с продуктами
export const productAPI = {
  // Продукты
  searchProducts: async (searchTerm) => {
    console.log('searchProducts вызван с параметром:', searchTerm);
    
    try {
      const response = await productApi.get('/products/search', { 
        params: { name: searchTerm }
      });
      console.log('API searchProducts ответ успешно получен');
      return response;
    } catch (error) {
      console.error('Ошибка в API searchProducts:', error);
      throw error;
    }
  },
  
  getProducts: async (page = 1, pageSize = 10, filters = {}, sort = null) => {
    console.log('getProducts вызван с параметрами:', { page, pageSize, filters, sort });
    
    // Формируем параметры запроса
    const params = {
      page,
      limit: pageSize,
      ...filters
    };
    
    // Добавляем параметр сортировки, если он указан, или используем 'newest' по умолчанию
    params.sort = sort || 'newest';
    console.log(`Добавляем параметр сортировки: sort=${params.sort}`);
    
    console.log('Итоговые параметры запроса:', params);
    
    try {
      const response = await productApi.get('/products', { params });
      console.log('API getProducts ответ успешно получен');
      console.log('Параметры запроса были:', { page, pageSize, filters, sort });
      console.log('Данные ответа (первые 2 товара):', response.data?.items?.slice(0, 2).map(item => ({
        id: item.id,
        name: item.name,
        price: item.price
      })));
      return response;
    } catch (error) {
      console.error('Ошибка в API getProducts:', error);
      console.error('Параметры запроса были:', { page, pageSize, filters, sort });
      throw error;
    }
  },
  // Метод для получения всех продуктов для админки (включая товары с stock=0)
  getAdminProducts: async (page = 1, pageSize = 10, category_id = null, subcategory_id = null, brand_id = null, country_id = null, sort = null) => {
    console.log('getAdminProducts вызван с параметрами:', { page, pageSize, category_id, subcategory_id, brand_id, country_id, sort });
    
    // Формируем параметры запроса
    const params = {
      page,
      limit: pageSize
    };
    
    // Добавляем параметры фильтрации, если они указаны
    if (category_id) params.category_id = category_id;
    if (subcategory_id) params.subcategory_id = subcategory_id;
    if (brand_id) params.brand_id = brand_id;
    if (country_id) params.country_id = country_id;
    
    // Добавляем параметр сортировки, если он указан, или используем 'newest' по умолчанию
    params.sort = sort || 'newest';
    console.log(`Добавляем параметр сортировки: sort=${params.sort}`);
    
    console.log('Итоговые параметры запроса:', params);
    
    try {
      const response = await productApi.get('products/admin', { params });
      console.log('API getAdminProducts ответ успешно получен');
      console.log('Параметры запроса были:', { page, pageSize, category_id, subcategory_id, brand_id, country_id, sort });
      console.log('Данные ответа (первые 2 товара):', response.data?.items?.slice(0, 2).map(item => ({
        id: item.id,
        name: item.name,
        price: item.price
      })));
      return response;
    } catch (error) {
      console.error('Ошибка в API getAdminProducts:', error);
      console.error('Параметры запроса были:', { page, pageSize, category_id, subcategory_id, brand_id, country_id, sort });
      throw error;
    }
  },
  getProductById: async (id, timestamp = '') => {
    const url = timestamp ? `/products/${id}${timestamp}` : `/products/${id}`;
    return await productApi.get(url);
  },
  
  // Получение похожих товаров
  getRelatedProducts: async (productId, categoryId, subcategoryId) => {
    console.log('getRelatedProducts вызван с параметрами:', { productId, categoryId, subcategoryId });
    
    // Пробуем найти товары по категории и подкатегории
    if (categoryId && subcategoryId) {
      // Формируем параметры запроса
      const params = {
        page: 1,
        limit: 4, // Увеличиваем лимит, чтобы было больше шансов найти похожие товары
        category_id: categoryId,
        subcategory_id: subcategoryId
      };
      
      console.log('Отправляем запрос с параметрами (категория + подкатегория):', params);
      
      try {
        const response = await productApi.get('/products', { params });
        console.log('API getRelatedProducts ответ (категория + подкатегория):', response);
        
        if (response.data && response.data.items) {
          // Фильтруем, чтобы исключить текущий товар
          const filtered = response.data.items.filter(item => item.id !== parseInt(productId));
          console.log('Отфильтрованные похожие товары (категория + подкатегория):', filtered.length, 'шт.');
          
          // Если нашли хотя бы один товар, возвращаем результат
          if (filtered.length > 0) {
            console.log('Возвращаем похожие товары по категории и подкатегории');
            return filtered;
          }
        }
      } catch (error) {
        console.error('Ошибка при поиске товаров по категории и подкатегории:', error);
      }
    }
    
    // Если по подкатегории не нашли или произошла ошибка, ищем только по категории
    if (categoryId) {
      const params = {
        page: 1,
        limit: 4, // Увеличиваем лимит еще больше
        category_id: categoryId
      };
      
      console.log('Отправляем запрос с параметрами (только категория):', params);
      
      try {
        const response = await productApi.get('/products', { params });
        console.log('API getRelatedProducts ответ (только категория):', response);
        
        if (response.data && response.data.items) {
          // Фильтруем, чтобы исключить текущий товар
          const filtered = response.data.items.filter(item => item.id !== parseInt(productId));
          console.log('Отфильтрованные похожие товары (только категория):', filtered.length, 'шт.');
          
          return filtered;
        }
      } catch (error) {
        console.error('Ошибка при поиске товаров по категории:', error);
      }
    }
    
    // Если ничего не нашли или произошла ошибка, возвращаем пустой массив
    console.log('Не удалось найти похожие товары, возвращаем пустой массив');
    return [];
  },
  
  // Получение категории по ID
  getCategoryById: async (id) => await productApi.get(`/categories/${id}`),
  
  // Получение подкатегории по ID
  getSubcategoryById: async (id) => await productApi.get(`/subcategories/${id}`),
  
  // Получение страны по ID
  getCountryById: async (id) => await productApi.get(`/countries/${id}`),
  
  // Получение бренда по ID
  getBrandById: async (id) => await productApi.get(`/brands/${id}`),
  
  // Заменяем метод createProduct для поддержки загрузки файлов
  createProduct: async (data) => {
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
      return await productApi.post('/products', formData, {
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
      
      return await productApi.post('/products', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
    }
  },
  
  // Обновляем метод updateProduct с поддержкой загрузки файлов
  updateProduct: async (id, data) => {
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
    return await productApi.put(`/products/${id}/form`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },
  
  deleteProduct: async (id) => await productApi.delete(`/products/${id}`),
  
  // Категории
  getCategories: async () => {
    try {
      return await productApi.get('/categories', {
        headers: {
          'Cache-Control': 'no-cache',
          'If-Modified-Since': '0'
        }
      });
    } catch (error) {
      console.error("Ошибка в getCategories:", error);
      throw error;
    }
  },
  createCategory: async (data) => await productApi.post('/categories', data),
  updateCategory: async (id, data) => await productApi.put(`/categories/${id}`, data),
  deleteCategory: async (id) => await productApi.delete(`/categories/${id}`),
  
  // Бренды
  getBrands: async () => {
    try {
      return await productApi.get('/brands', {
        headers: {
          'Cache-Control': 'no-cache',
          'If-Modified-Since': '0'
        }
      });
    } catch (error) {
      console.error("Ошибка в getBrands:", error);
      throw error;
    }
  },
  createBrand: async (data) => await productApi.post('/brands', data),
  updateBrand: async (id, data) => await productApi.put(`/brands/${id}`, data),
  deleteBrand: async (id) => await productApi.delete(`/brands/${id}`),
  
  // Страны
  getCountries: async () => {
    try {
      // Добавляем дополнительные заголовки для решения проблем с CORS
      return await productApi.get('/countries', {
        headers: {
          'Cache-Control': 'no-cache',
          'If-Modified-Since': '0'
        }
      });
    } catch (error) {
      console.error("Ошибка в getCountries:", error);
      throw error;
    }
  },
  createCountry: async (data) => await productApi.post('/countries', data),
  updateCountry: async (id, data) => await productApi.put(`/countries/${id}`, data),
  deleteCountry: async (id) => await productApi.delete(`/countries/${id}`),
  
  // Подкатегории
  getSubcategories: async () => {
    try {
      return await productApi.get('/subcategories', {
        headers: {
          'Cache-Control': 'no-cache',
          'If-Modified-Since': '0'
        }
      });
    } catch (error) {
      console.error("Ошибка в getSubcategories:", error);
      throw error;
    }
  },
  createSubcategory: async (data) => await productApi.post('/subcategories', data),
  updateSubcategory: async (id, data) => await productApi.put(`/subcategories/${id}`, data),
  deleteSubcategory: async (id) => await productApi.delete(`/subcategories/${id}`),
  
  getProductsBatch: async (ids) => {
    if (!ids || !ids.length) return [];
    const response = await productApi.post('/products/open-batch', { product_ids: ids });
    return response.data;
  },
};

// Экспортируем объект с методами для работы с корзиной
export const cartAPI = {
  /**
   * Получает текущую корзину пользователя
   * @returns {Promise<Object>} - Данные корзины
   */
  getCart: async () => {
    return await cartApi.get('/cart');
  },

  /**
   * Получает краткую информацию о корзине (количество товаров и общая стоимость)
   * @returns {Promise<Object>} - Краткая информация о корзине
   */
  getCartSummary: async () => {
    return await cartApi.get('/cart/summary');
  },

  /**
   * Добавляет товар в корзину
   * @param {number} productId - ID товара
   * @param {number} quantity - Количество товара
   * @returns {Promise<Object>} - Обновленная корзина
   */
  addToCart: async (productId, quantity) => {
    return await cartApi.post('/cart/items', {
      product_id: productId,
      quantity: quantity
    });
  },

  /**
   * Обновляет количество товара в корзине
   * @param {number} itemId - ID элемента корзины
   * @param {number} quantity - Новое количество товара
   * @returns {Promise<Object>} - Обновленная корзина
   */
  updateCartItem: async (itemId, quantity) => {
    return await cartApi.put(`/cart/items/${itemId}`, {
      quantity: quantity
    });
  },

  /**
   * Удаляет товар из корзины
   * @param {number} itemId - ID элемента корзины
   * @returns {Promise<Object>} - Обновленная корзина
   */
  removeFromCart: async (itemId) => {
    return await cartApi.delete(`/cart/items/${itemId}`);
  },

  /**
   * Очищает корзину (удаляет все товары)
   * @returns {Promise<Object>} - Пустая корзина
   */
  clearCart: async () => {
    return await cartApi.delete('/cart');
  },

  /**
   * Объединяет корзины при авторизации пользователя
   * @param {Array} items - Массив товаров из localStorage
   * @returns {Promise<Object>} - Объединенная корзина
   */
  mergeCarts: async (items) => {
    return await cartApi.post('/cart/merge', { items });
  }
};

// API для работы с корзинами
export const cartService = {
  // Получение списка всех корзин (для администратора)
  getAllCarts: async (page = 1, pageSize = 10, filter = 'all', sort = 'newest') => {
    console.log('cartService.getAllCarts вызван с параметрами:', { page, pageSize, filter, sort });
    
    const params = {
      page,
      page_size: pageSize,
    };
    
    if (filter !== 'all') {
      params.filter = filter;
    }
    
    if (sort) {
      params.sort = sort;
    }
    
    try {
      const response = await cartApi.get('/admin/carts', { params });
      console.log('API getAllCarts ответ успешно получен, общее количество:', response.data.total);
      return response.data;
    } catch (error) {
      console.error('Ошибка в API getAllCarts:', error);
      throw error;
    }
  },
  
  // Получение детальной информации о корзине (для администратора)
  getCartById: async (cartId) => {
    console.log(`cartService.getCartById вызван с cartId: ${cartId}`);
    try {
      const response = await cartApi.get(`/admin/carts/${cartId}`);
      console.log('API getCartById ответ успешно получен:', response.data);
      return response.data;
    } catch (error) {
      console.error('Ошибка в API getCartById:', error);
      throw error;
    }
  },
  
  // Получение корзины пользователя или создание новой
  getUserCart: async () => {
    console.log('cartService.getUserCart вызван');
    try {
      const response = await cartApi.get('/cart');
      console.log('API getUserCart ответ успешно получен:', response.data);
      return response.data;
    } catch (error) {
      console.error('Ошибка в API getUserCart:', error);
      throw error;
    }
  },
  
  // Добавление товара в корзину
  addToCart: async (productId, quantity = 1) => {
    console.log(`cartService.addToCart вызван с productId: ${productId}, quantity: ${quantity}`);
    try {
      const response = await cartApi.post('/cart/items', {
        product_id: productId,
        quantity
      });
      console.log('API addToCart ответ успешно получен:', response.data);
      return response.data;
    } catch (error) {
      console.error('Ошибка в API addToCart:', error);
      throw error;
    }
  },
  
  // Обновление количества товара в корзине
  updateCartItem: async (itemId, quantity) => {
    console.log(`cartService.updateCartItem вызван с itemId: ${itemId}, quantity: ${quantity}`);
    try {
      const response = await cartApi.put(`/cart/items/${itemId}`, {
        quantity
      });
      console.log('API updateCartItem ответ успешно получен:', response.data);
      return response.data;
    } catch (error) {
      console.error('Ошибка в API updateCartItem:', error);
      throw error;
    }
  },
  
  // Удаление товара из корзины
  removeCartItem: async (itemId) => {
    console.log(`cartService.removeCartItem вызван с itemId: ${itemId}`);
    try {
      const response = await cartApi.delete(`/cart/items/${itemId}`);
      console.log('API removeCartItem ответ успешно получен');
      return response.data;
    } catch (error) {
      console.error('Ошибка в API removeCartItem:', error);
      throw error;
    }
  },
  
  // Очистка корзины
  clearCart: async () => {
    console.log('cartService.clearCart вызван');
    try {
      const response = await cartApi.delete('/cart/items');
      console.log('API clearCart ответ успешно получен');
      return response.data;
    } catch (error) {
      console.error('Ошибка в API clearCart:', error);
      throw error;
    }
  },
  
  // Создание кода доступа для шаринга корзины
  shareCart: async () => {
    console.log('cartService.shareCart вызван');
    try {
      const response = await cartApi.post('/cart/share', {});
      console.log('API shareCart ответ успешно получен:', response.data);
      return response.data;
    } catch (error) {
      console.error('Ошибка в API shareCart:', error);
      throw error;
    }
  },
  
  // Загрузка шаринговой корзины
  loadSharedCart: async (shareCode, mergeStrategy = 'merge') => {
    console.log(`cartService.loadSharedCart вызван с shareCode: ${shareCode}, mergeStrategy: ${mergeStrategy}`);
    try {
      const response = await cartApi.post('/cart/load', {
        share_code: shareCode,
        merge_strategy: mergeStrategy
      });
      console.log('API loadSharedCart ответ успешно получен:', response.data);
      return response.data;
    } catch (error) {
      console.error('Ошибка в API loadSharedCart:', error);
      throw error;
    }
  }
};

// API для работы с отзывами
export const reviewAPI = {
  // Публичные методы для работы с отзывами о товарах
  getProductReviews: async (productId, page = 1, pageSize = 10) => {
    return await reviewApi.get(`/reviews/products/${productId}`, {
      params: { page, limit: pageSize }
    });
  },
  
  createProductReview: async (productId, data) => {
    return await reviewApi.post('/reviews/products', {
      ...data,
      product_id: productId
    });
  },
  
  getProductStats: async (productId) => {
    return await reviewApi.get(`/reviews/products/${productId}/stats`);
  },
  
  getBatchProductStats: async (productIds) => {
    console.log('Вызов API getBatchProductStats для товаров:', productIds);
    try {
      const response = await reviewApi.post('/reviews/products/batch-stats', {
        product_ids: productIds
      });
      console.log('API getBatchProductStats ответ успешно получен:', response.data);
      return response;
    } catch (error) {
      console.error('Ошибка в API getBatchProductStats:', error);
      throw error;
    }
  },
  
  // Публичные методы для работы с отзывами о магазине
  getStoreReviews: async (page = 1, pageSize = 10) => {
    return await reviewApi.get('/reviews/store/all', {
      params: { page, limit: pageSize }
    });
  },
  
  createStoreReview: async (data) => {
    return await reviewApi.post('/reviews/store', data);
  },
  
  getStoreStats: async () => {
    return await reviewApi.get('/reviews/store/stats');
  },
  
  // Общие методы для всех типов отзывов
  getReview: async (reviewId) => {
    return await reviewApi.get(`/reviews/${reviewId}`);
  },
  
  addReaction: async (reviewId, reactionType) => {
    console.log(`Вызов API addReaction для отзыва ${reviewId} с типом ${reactionType}`);
    try {
      const response = await reviewApi.post(`/reviews/reactions`, {
        review_id: reviewId,
        reaction_type: reactionType
      });
      
      console.log(`API addReaction ответ успешно получен, статус: ${response.status}`, response.data);
      // Убедимся, что данные о реакциях есть в объекте
      if (!response.data.reaction_stats) {
        console.error('В ответе API addReaction отсутствуют данные о реакциях:', response.data);
        // Добавим данные по умолчанию, если их нет в ответе
        response.data.reaction_stats = { likes: 0, dislikes: 0 };
      }
      return response.data;
    } catch (error) {
      console.error('Ошибка в API addReaction:', error);
      throw error;
    }
  },
  
  deleteReaction: async (reviewId) => {
    console.log(`Вызов API deleteReaction для отзыва ${reviewId}`);
    try {
      const response = await reviewApi.post(`/reviews/reactions/delete`, {
        review_id: reviewId
      });
      
      console.log(`API deleteReaction ответ успешно получен, статус: ${response.status}`, response.data);
      // Убедимся, что данные о реакциях есть в объекте
      if (!response.data.reaction_stats) {
        console.error('В ответе API deleteReaction отсутствуют данные о реакциях:', response.data);
        // Добавим данные по умолчанию, если их нет в ответе
        response.data.reaction_stats = { likes: 0, dislikes: 0 };
      }
      return response.data;
    } catch (error) {
      console.error('Ошибка в API deleteReaction:', error);
      throw error;
    }
  },
  
  // Проверка прав на оставление отзыва
  checkReviewPermissions: async (productId = null) => {
    const params = productId ? { product_id: productId } : {};
    return await reviewApi.get('/reviews/permissions/check', { params });
  },
  
  // Методы для администратора
  admin: {
    getProductReviews: async (productId, page = 1, pageSize = 10) => {
      return await reviewApi.get(`/admin/reviews/products/${productId}`, {
        params: { page, limit: pageSize, include_hidden: true }
      });
    },
    
    getStoreReviews: async (page = 1, pageSize = 10) => {
      return await reviewApi.get('/admin/reviews/store', {
        params: { page, limit: pageSize, include_hidden: true }
      });
    },
    
    getReview: async (reviewId) => {
      return await reviewApi.get(`/admin/reviews/${reviewId}`);
    },
    
    toggleReviewVisibility: async (reviewId) => {
      // Получаем текущий статус отзыва, а затем устанавливаем противоположный
      try {
        const response = await reviewApi.get(`/admin/reviews/${reviewId}`);
        const review = response.data;
        const newStatus = !review.is_hidden;
        
        const updateResponse = await reviewApi.patch(`/admin/reviews/${reviewId}`, {
          is_hidden: newStatus
        });
        return updateResponse.data;
      } catch (error) {
        console.error('Ошибка в toggleReviewVisibility:', error);
        throw error;
      }
    },
    
    addComment: async (reviewId, content) => {
      const response = await reviewApi.post(`/admin/reviews/comments`, {
        review_id: reviewId,
        content
      });
      return response.data;
    },
    
    deleteComment: async (reviewId, commentId) => {
      return await reviewApi.delete(`/admin/reviews/${reviewId}/comments/${commentId}`);
    }
  }
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
  productAPI,
  cartAPI,
  cartService,
  reviewAPI
};

export default apiExports; 