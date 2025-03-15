import React, { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';
import { API_URLS, STORAGE_KEYS } from '../utils/constants';

// URL сервиса заказов
const ORDER_SERVICE_URL = API_URLS.ORDER_SERVICE;
// В бэкенде API префикс не используется
const API_PREFIX = '';

// Создаем контекст для заказов
const OrderContext = createContext();

// Хук для использования контекста заказов
export const useOrders = () => {
  return useContext(OrderContext);
};

// Провайдер контекста заказов
export const OrderProvider = ({ children }) => {
  const { token, user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [currentOrder, setCurrentOrder] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Конфигурация заголовков с токеном авторизации
  const getConfig = useCallback(() => {
    // Пытаемся получить токен из контекста аутентификации
    let authToken = token;
    
    // Если токен не найден в контексте, пробуем получить из localStorage
    if (!authToken) {
      authToken = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      console.log("Получен токен из localStorage:", authToken ? `${authToken.substring(0, 20)}...` : "Токен не найден");
    } else {
      console.log("Получен токен из контекста:", `${authToken.substring(0, 20)}...`);
    }
    
    if (!authToken) {
      console.error("ВНИМАНИЕ: Не найден токен авторизации ни в контексте, ни в localStorage!");
    }
    
    // Формируем заголовки
    const headers = {
      'Content-Type': 'application/json'
    };
    
    // Добавляем токен только если он существует
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    const config = { headers };
    
    console.log("Сформированы заголовки запроса:", {
      Authorization: headers.Authorization ? `${headers.Authorization.substring(0, 30)}...` : 'Нет токена',
      'Content-Type': headers['Content-Type']
    });
    
    return config;
  }, [token]);

  // Проверка наличия токена
  const hasToken = useCallback(() => {
    const hasLocalToken = !!localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    const hasContextToken = !!token;
    console.log(`Статус токена: localStorage=${hasLocalToken}, context=${hasContextToken}`);
    return hasContextToken || hasLocalToken;
  }, [token]);

  // Получение списка заказов пользователя
  const fetchUserOrders = useCallback(async (page = 1, size = 10, statusId = null) => {
    // Проверяем наличие токена в контексте или localStorage
    if (!hasToken()) {
      console.warn("Попытка получить заказы пользователя без авторизации");
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Исправлено: роут для получения заказов текущего пользователя
      let url = `${ORDER_SERVICE_URL}${API_PREFIX}/orders?page=${page}&size=${size}`;
      if (statusId) {
        url += `&status_id=${statusId}`;
      }
      
      console.log("Запрос заказов пользователя:", url);
      const config = getConfig();
      console.log("Заголовки запроса:", config);
      
      const response = await axios.get(url, config);
      console.log("Ответ сервера:", response.data);
      
      setOrders(response.data.items);
      return response.data;
    } catch (err) {
      console.error("Полная ошибка при получении заказов:", err);
      
      // Обработка ошибки валидации
      if (err.response?.status === 422 && err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // Формируем текстовое сообщение из массива ошибок валидации
          const errorMsg = err.response.data.detail
            .map(e => `${e.loc[e.loc.length - 1]}: ${e.msg}`)
            .join(', ');
          setError(errorMsg);
        } else {
          setError(err.response.data.detail);
        }
      } else {
        setError(err.response?.data?.detail || err.message || 'Не удалось получить заказы');
      }
      
      return null;
    } finally {
      setLoading(false);
    }
  }, [hasToken, getConfig]);

  // Получение одного заказа по ID
  const fetchOrder = useCallback(async (orderId) => {
    if (!token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(
        `${ORDER_SERVICE_URL}${API_PREFIX}/orders/${orderId}`, 
        getConfig()
      );
      setCurrentOrder(response.data);
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось получить информацию о заказе');
      console.error('Ошибка при получении заказа:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, getConfig]);

  // Создание нового заказа
  const createOrder = useCallback(async (orderData) => {
    setLoading(true);
    setError(null);
    
    // Проверяем наличие токена
    const isAuthenticated = hasToken();
    console.log("Статус аутентификации при создании заказа:", isAuthenticated ? "Пользователь аутентифицирован" : "Пользователь не аутентифицирован");
    
    console.log("Исходные данные заказа:", orderData);
    console.log("URL:", `${ORDER_SERVICE_URL}${API_PREFIX}/orders`);
    
    try {
      // Проверка наличия обязательных полей
      if (!orderData.fullName && !orderData.shipping_address?.full_name) {
        setError("Необходимо указать ФИО получателя");
        return null;
      }
      
      if (!orderData.region && !orderData.shipping_address?.state) {
        setError("Необходимо указать регион доставки");
        return null;
      }
      
      if (!orderData.city && !orderData.shipping_address?.city) {
        setError("Необходимо указать город");
        return null;
      }
      
      if (!orderData.street && !orderData.shipping_address?.address_line1) {
        setError("Необходимо указать адрес");
        return null;
      }
      
      // Подготовка данных в новом формате
      const newOrderData = {
        items: orderData.items,
        full_name: orderData.shipping_address?.full_name || orderData.fullName || "",
        email: orderData.contact_email || orderData.email || "",
        phone: orderData.contact_phone || orderData.phone || "",
        region: orderData.shipping_address?.state || orderData.region || "",
        city: orderData.shipping_address?.city || orderData.city || "",
        street: orderData.shipping_address?.address_line1 || orderData.street || "",
        comment: orderData.notes || orderData.comment || ""
      };
      
      // Проверяем итоговый объект на наличие всех обязательных полей
      const requiredFields = ['full_name', 'phone', 'region', 'city', 'street'];
      const missingFields = requiredFields.filter(field => !newOrderData[field]);
      
      if (missingFields.length > 0) {
        const fieldNames = {
          full_name: 'ФИО получателя',
          email: 'Email',
          phone: 'Телефон',
          region: 'Регион',
          city: 'Город',
          street: 'Адрес'
        };
        
        const errorMsg = `Необходимо заполнить следующие поля: ${missingFields.map(f => fieldNames[f]).join(', ')}`;
        setError(errorMsg);
        return null;
      }
      
      console.log("Преобразованные данные заказа:", newOrderData);
      
      // Определяем конфигурацию заголовков
      const config = getConfig();
      console.log("Используемые заголовки:", config);
      
      const response = await axios.post(
        `${ORDER_SERVICE_URL}${API_PREFIX}/orders`, 
        newOrderData,
        config
      );
      
      console.log("Ответ сервера:", response.data);
      return response.data;
    } catch (err) {
      console.error("Полная ошибка при создании заказа:", err);
      console.error("Ответ сервера:", err.response);
      
      let errorMessage = 'Не удалось создать заказ';
      
      // Обработка ошибок валидации (422 Unprocessable Entity)
      if (err.response?.status === 422 && err.response?.data?.detail) {
        const validationErrors = err.response.data.detail;
        if (Array.isArray(validationErrors)) {
          // Собираем сообщения об ошибках валидации
          errorMessage = validationErrors.map(error => {
            const field = error.loc[error.loc.length - 1];
            return `Ошибка в поле "${field}": ${error.msg}`;
          }).join('. ');
        } else if (typeof validationErrors === 'string') {
          errorMessage = validationErrors;
        }
      } 
      // Дополнительная проверка на ошибку авторизации
      else if (err.response?.status === 401) {
        errorMessage = "Для оформления заказа необходима авторизация. Пожалуйста, войдите в систему.";
      } 
      // Другие ошибки от сервера
      else if (err.response?.data?.detail) {
        errorMessage = typeof err.response.data.detail === 'string' 
          ? err.response.data.detail 
          : 'Ошибка на сервере';
      }
      
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [getConfig, hasToken, setError, setLoading]);

  // Отмена заказа
  const cancelOrder = useCallback(async (orderId, reason) => {
    if (!token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(
        `${ORDER_SERVICE_URL}${API_PREFIX}/orders/${orderId}/cancel`,
        { notes: reason },
        getConfig()
      );
      
      // Обновляем текущий заказ, если это он
      if (currentOrder && currentOrder.id === orderId) {
        setCurrentOrder(response.data);
      }
      
      // Обновляем список заказов
      setOrders(prevOrders => 
        prevOrders.map(order => 
          order.id === orderId ? response.data : order
        )
      );
      
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось отменить заказ');
      console.error('Ошибка при отмене заказа:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, getConfig, currentOrder]);

  // Получение статусов заказов
  const fetchOrderStatuses = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Исправлено: путь до статусов заказов с API_PREFIX
      console.log("Запрос статусов заказов:", `${ORDER_SERVICE_URL}${API_PREFIX}/order-statuses`);
      
      // Делаем запрос без аутентификации, так как статусы заказов публичны
      const response = await axios.get(
        `${ORDER_SERVICE_URL}${API_PREFIX}/order-statuses`
      );
      
      console.log("Ответ со статусами заказов:", response.data);
      return response.data || [];
    } catch (err) {
      console.error("Полная ошибка при получении статусов заказов:", err);
      setError(err.response?.data?.detail || 'Не удалось получить статусы заказов');
      
      // Если получена ошибка 404 (роутер не настроен), возвращаем заглушечные данные
      if (err.response?.status === 404) {
        console.log("Роутер статусов не найден, возвращаем заглушечные данные");
        return [
          { id: 1, name: "Новый", description: "Новый заказ", color: "#3498db", allow_cancel: true, is_final: false, sort_order: 1 },
          { id: 2, name: "В обработке", description: "Заказ в обработке", color: "#f39c12", allow_cancel: true, is_final: false, sort_order: 2 },
          { id: 3, name: "Отправлен", description: "Заказ отправлен", color: "#2ecc71", allow_cancel: false, is_final: false, sort_order: 3 },
          { id: 4, name: "Доставлен", description: "Заказ доставлен", color: "#27ae60", allow_cancel: false, is_final: true, sort_order: 4 },
          { id: 5, name: "Отменен", description: "Заказ отменен", color: "#e74c3c", allow_cancel: false, is_final: true, sort_order: 5 }
        ];
      }
      
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  // Получение заказов пользователя
  const getUserOrders = useCallback(async (params = {}) => {
    if (!hasToken()) {
      console.warn("Попытка получить заказы пользователя без авторизации");
      setError("Для просмотра заказов необходима авторизация");
      return { items: [], total: 0, page: 1, limit: 10 };
    }
    
    // Получаем ID пользователя
    const userData = user || JSON.parse(localStorage.getItem(STORAGE_KEYS.USER_DATA) || "{}");
    const userId = userData?.id || null;
    
    if (!userId) {
      console.warn("Не удалось определить ID пользователя");
      setError("Не удалось определить данные пользователя. Пожалуйста, войдите в систему повторно.");
      return { items: [], total: 0, page: 1, limit: 10 };
    }
    
    setLoading(true);
    setError(null);
    
    try {
      console.log("Запрос заказов пользователя с параметрами:", params);
      const config = getConfig();
      console.log("Заголовки запроса:", JSON.stringify(config.headers));
      
      // Преобразуем параметры для соответствия API
      const adjustedParams = { ...params };
      if (adjustedParams.limit) {
        adjustedParams.size = adjustedParams.limit;
        delete adjustedParams.limit;
      }
      
      const url = `${ORDER_SERVICE_URL}${API_PREFIX}/orders`;
      console.log("URL запроса:", url);
      
      // Исправлено: получаем заказы пользователя через API_PREFIX
      const response = await axios.get(url, { 
        ...config,
        params: adjustedParams
      });
      
      console.log("Ответ сервера:", response.data);
      return response.data || { items: [], total: 0, page: 1, limit: 10 };
    } catch (err) {
      console.error("Полная ошибка при получении заказов пользователя:", err);
      console.error("Статус ошибки:", err.response?.status);
      console.error("Ответ от сервера:", err.response?.data);
      
      if (err.response?.status === 401) {
        setError("Для просмотра заказов необходима авторизация. Пожалуйста, войдите в систему.");
      } else if (err.response?.status === 403) {
        setError("Доступ запрещен. У вас недостаточно прав для просмотра этих заказов.");
      } else {
        setError(err.response?.data?.detail || 'Не удалось получить список заказов');
      }
      
      return { items: [], total: 0, page: 1, limit: 10 };
    } finally {
      setLoading(false);
    }
  }, [hasToken, getConfig, user]);
  
  // Получение всех заказов (для администраторов)
  const getAllOrders = useCallback(async (params = {}) => {
    if (!hasToken()) {
      console.warn("Попытка получить все заказы без авторизации");
      return { items: [], total: 0, page: 1, limit: 10 };
    }
    
    // Проверяем, является ли пользователь админом
    const userData = user || JSON.parse(localStorage.getItem(STORAGE_KEYS.USER_DATA) || "{}");
    const isAdmin = userData?.is_admin || userData?.is_super_admin;
    
    if (!isAdmin) {
      console.warn("Попытка получить все заказы без прав администратора");
      setError("Для доступа к списку заказов необходимы права администратора");
      return { items: [], total: 0, page: 1, limit: 10 };
    }
    
    setLoading(true);
    setError(null);
    
    try {
      console.log("Запрос всех заказов с параметрами:", params);
      const config = getConfig();
      console.log("Заголовки запроса:", JSON.stringify(config.headers));
      
      // Преобразуем параметр limit в size, если он присутствует
      const adjustedParams = { ...params };
      if (adjustedParams.limit) {
        adjustedParams.size = adjustedParams.limit;
        delete adjustedParams.limit;
      }
      console.log("Преобразованные параметры:", adjustedParams);
      
      const url = `${ORDER_SERVICE_URL}${API_PREFIX}/admin/orders`;
      console.log("URL запроса:", url);
      
      // Исправлено: маршрут для админских заказов с API_PREFIX
      const response = await axios.get(url, { 
        ...config,
        params: adjustedParams
      });
      
      console.log("Ответ сервера:", response.data);
      return response.data || { items: [], total: 0, page: 1, limit: 10 };
    } catch (err) {
      console.error("Полная ошибка при получении всех заказов:", err);
      console.error("Тип ошибки:", err.name);
      console.error("Сообщение ошибки:", err.message);
      console.error("Ответ от сервера:", err.response?.data);
      console.error("Статус ошибки:", err.response?.status);
      
      // Обработка ошибок авторизации
      if (err.response?.status === 401) {
        setError("Для доступа к списку заказов необходима авторизация. Пожалуйста, войдите в систему.");
      } else if (err.response?.status === 403) {
        setError("Доступ запрещен. У вас недостаточно прав для просмотра всех заказов.");
      } else if (err.response?.status === 422 && err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // Формируем текстовое сообщение из массива ошибок валидации
          const errorMsg = err.response.data.detail
            .map(e => `${e.loc[e.loc.length - 1]}: ${e.msg}`)
            .join(', ');
          setError(errorMsg);
        } else {
          setError(err.response.data.detail);
        }
      } else {
        setError(err.response?.data?.detail || err.message || 'Не удалось получить список всех заказов');
      }
      
      return { items: [], total: 0, page: 1, limit: 10 };
    } finally {
      setLoading(false);
    }
  }, [hasToken, getConfig, user]);

  // Обновление статуса заказа (для администраторов)
  const updateOrderStatus = useCallback(async (orderId, statusData) => {
    if (!token) return null;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.put(
        `${ORDER_SERVICE_URL}${API_PREFIX}/admin/orders/${orderId}/status`, 
        statusData,
        getConfig()
      );
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось обновить статус заказа');
      console.error('Ошибка при обновлении статуса заказа:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, getConfig]);

  // Получение одного заказа по ID (для администраторов)
  const getAdminOrderById = useCallback(async (orderId) => {
    if (!token) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(
        `${ORDER_SERVICE_URL}${API_PREFIX}/admin/orders/${orderId}`, 
        getConfig()
      );
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Не удалось получить информацию о заказе');
      console.error('Ошибка при получении заказа:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, getConfig]);

  // Значение контекста
  const contextValue = {
    orders,
    loading,
    error,
    setError,
    currentOrder,
    fetchUserOrders,
    getOrderById: fetchOrder,
    getOrderStatuses: fetchOrderStatuses,
    updateOrderStatus,
    cancelOrder,
    createOrder,
    getUserOrders,
    getAllOrders,
    getAdminOrderById
  };

  return (
    <OrderContext.Provider value={contextValue}>
      {children}
    </OrderContext.Provider>
  );
};

export default OrderContext; 