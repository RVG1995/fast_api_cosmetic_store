import axios from 'axios';
import { API_URLS, STORAGE_KEYS } from './constants';

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
const authApi = createApiInstance(API_URLS.AUTH_SERVICE);
const userApi = createApiInstance(API_URLS.USER);
const contentApi = createApiInstance(API_URLS.CONTENT);
const notificationApi = createApiInstance(API_URLS.NOTIFICATION);
const productApi = createApiInstance(API_URLS.PRODUCT_SERVICE);
const cartApi = createApiInstance(API_URLS.CART_SERVICE);

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
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log(`[${serviceName} API] Добавлен токен авторизации: ${token.substring(0, 15)}...`);
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
        localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, response.data.access_token);
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
        localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
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
setupInterceptors(cartApi, 'Cart');

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
        localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, response.data.access_token);
        console.log('Токен сохранен в localStorage из login API');
      }
      return response;
    });
  },
  register: (userData) => authApi.post('/auth/register', userData),
  logout: () => authApi.post('/auth/logout').then(response => {
    // Удаляем токен из localStorage
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
    console.log('Токен удален из localStorage из logout API');
    return response;
  }),
  getCurrentUser: () => authApi.get('/auth/users/me'),
  activateUser: (token) => authApi.get(`/auth/activate/${token}`).then(response => {
    // Сохраняем токен в localStorage при активации
    if (response.data && response.data.access_token) {
      localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, response.data.access_token);
      console.log('Токен сохранен в localStorage из activate API');
    }
    return response;
  }),
  changePassword: (passwordData) => authApi.post('/auth/change-password', passwordData),
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
  removeAdmin: (userId) => authApi.patch(`/admin/users/${userId}/remove-admin`),
  deleteUser: (userId) => authApi.delete(`/admin/users/${userId}`),
  checkAdminAccess: () => authApi.get('/admin/check-access'),
  checkSuperAdminAccess: () => authApi.get('/admin/check-super-access'),
  getDashboardStats: async () => {
    try {
      // Получаем количество пользователей
      const usersResponse = await authApi.get('/admin/users');
      const usersCount = usersResponse.data.length || 0;
      
      // Получаем количество товаров
      const productsResponse = await productApi.get('/admin/products', { 
        params: { page: 1, limit: 1 } 
      });
      const productsCount = productsResponse.data.total || 0;
      
      // Получаем количество заказов
      const ordersApi = createApiInstance(API_URLS.ORDER_SERVICE);
      setupInterceptors(ordersApi, 'Orders');
      const ordersResponse = await ordersApi.get('/admin/orders', {
        params: { page: 1, size: 1 }
      });
      const ordersCount = ordersResponse.data.total || 0;
      
      // В реальном приложении здесь был бы запрос для получения количества запросов,
      // но для демонстрации будем использовать случайное число
      const requestsCount = Math.floor(Math.random() * 500) + 100;
      
      return {
        usersCount,
        productsCount,
        ordersCount,
        requestsCount
      };
    } catch (error) {
      console.error('Ошибка при получении статистики для админ-панели:', error);
      // Возвращаем значения по умолчанию в случае ошибки
      return {
        usersCount: 0,
        productsCount: 0,
        ordersCount: 0,
        requestsCount: 0
      };
    }
  }
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
  searchProducts: (searchTerm) => {
    console.log('searchProducts вызван с параметром:', searchTerm);
    
    return productApi.get('/products/search', { 
      params: { name: searchTerm }
    }).then(response => {
      console.log('API searchProducts ответ успешно получен');
      return response;
    }).catch(error => {
      console.error('Ошибка в API searchProducts:', error);
      throw error;
    });
  },
  
  getProducts: (page = 1, pageSize = 10, filters = {}, sort = null) => {
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
    
    return productApi.get('/products', { params }).then(response => {
      console.log('API getProducts ответ успешно получен');
      console.log('Параметры запроса были:', { page, pageSize, filters, sort });
      console.log('Данные ответа (первые 2 товара):', response.data?.items?.slice(0, 2).map(item => ({
        id: item.id,
        name: item.name,
        price: item.price
      })));
      return response;
    }).catch(error => {
      console.error('Ошибка в API getProducts:', error);
      console.error('Параметры запроса были:', { page, pageSize, filters, sort });
      throw error;
    });
  },
  // Метод для получения всех продуктов для админки (включая товары с stock=0)
  getAdminProducts: (page = 1, pageSize = 10, category_id = null, subcategory_id = null, brand_id = null, country_id = null, sort = null) => {
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
    
    return productApi.get('/admin/products', { params }).then(response => {
      console.log('API getAdminProducts ответ успешно получен');
      console.log('Параметры запроса были:', { page, pageSize, category_id, subcategory_id, brand_id, country_id, sort });
      console.log('Данные ответа (первые 2 товара):', response.data?.items?.slice(0, 2).map(item => ({
        id: item.id,
        name: item.name,
        price: item.price
      })));
      return response;
    }).catch(error => {
      console.error('Ошибка в API getAdminProducts:', error);
      console.error('Параметры запроса были:', { page, pageSize, category_id, subcategory_id, brand_id, country_id, sort });
      throw error;
    });
  },
  getProductById: (id, timestamp = '') => {
    const url = timestamp ? `/products/${id}${timestamp}` : `/products/${id}`;
    return productApi.get(url);
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
  getCategoryById: (id) => productApi.get(`/categories/${id}`),
  
  // Получение подкатегории по ID
  getSubcategoryById: (id) => productApi.get(`/subcategories/${id}`),
  
  // Получение страны по ID
  getCountryById: (id) => productApi.get(`/countries/${id}`),
  
  // Получение бренда по ID
  getBrandById: (id) => productApi.get(`/brands/${id}`),
  
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
  createCategory: (data) => productApi.post('/categories', data),
  updateCategory: (id, data) => productApi.put(`/categories/${id}`, data),
  deleteCategory: (id) => productApi.delete(`/categories/${id}`),
  
  // Бренды
  getBrands: () => productApi.get('/brands'),
  createBrand: (data) => productApi.post('/brands', data),
  updateBrand: (id, data) => productApi.put(`/brands/${id}`, data),
  deleteBrand: (id) => productApi.delete(`/brands/${id}`),
  
  // Страны
  getCountries: () => productApi.get('/countries'),
  createCountry: (data) => productApi.post('/countries', data),
  updateCountry: (id, data) => productApi.put(`/countries/${id}`, data),
  deleteCountry: (id) => productApi.delete(`/countries/${id}`),
  
  // Подкатегории
  getSubcategories: () => productApi.get('/subcategories'),
  createSubcategory: (data) => productApi.post('/subcategories', data),
  updateSubcategory: (id, data) => productApi.put(`/subcategories/${id}`, data),
  deleteSubcategory: (id) => productApi.delete(`/subcategories/${id}`),
};

// Экспортируем объект с методами для работы с корзиной
export const cartAPI = {
  /**
   * Получает текущую корзину пользователя
   * @returns {Promise<Object>} - Данные корзины
   */
  getCart: () => {
    return cartApi.get('/cart');
  },

  /**
   * Получает краткую информацию о корзине (количество товаров и общая стоимость)
   * @returns {Promise<Object>} - Краткая информация о корзине
   */
  getCartSummary: () => {
    return cartApi.get('/cart/summary');
  },

  /**
   * Добавляет товар в корзину
   * @param {number} productId - ID товара
   * @param {number} quantity - Количество товара
   * @returns {Promise<Object>} - Обновленная корзина
   */
  addToCart: (productId, quantity) => {
    return cartApi.post('/cart/items', {
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
  updateCartItem: (itemId, quantity) => {
    return cartApi.put(`/cart/items/${itemId}`, {
      quantity: quantity
    });
  },

  /**
   * Удаляет товар из корзины
   * @param {number} itemId - ID элемента корзины
   * @returns {Promise<Object>} - Обновленная корзина
   */
  removeFromCart: (itemId) => {
    return cartApi.delete(`/cart/items/${itemId}`);
  },

  /**
   * Очищает корзину (удаляет все товары)
   * @returns {Promise<Object>} - Пустая корзина
   */
  clearCart: () => {
    return cartApi.delete('/cart');
  },

  /**
   * Объединяет корзины при авторизации пользователя
   * @param {string} [sessionId] - Идентификатор сессии для корзины (необязательный)
   * @returns {Promise<Object>} - Объединенная корзина
   */
  mergeCarts: (sessionId) => {
    let url = '/cart/merge';
    
    // Если передан sessionId, добавляем его как query параметр
    if (sessionId) {
      url += `?url_session_id=${sessionId}`;
    }
    
    return cartApi.post(url);
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
  cartService
};

export default apiExports; 