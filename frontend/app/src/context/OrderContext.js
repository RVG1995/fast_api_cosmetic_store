import React, { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';
import { API_URLS, STORAGE_KEYS } from '../utils/constants';

// URL сервиса заказов
const ORDER_SERVICE_URL = API_URLS.ORDER_SERVICE;
// Префикс API не используется, так как пути уже определены в роутерах бэкенда
// Корректные пути: /orders, /admin/orders, /order-statuses
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

  // Функция для получения конфигурации запроса
  const getConfig = useCallback(() => {
    // Получаем актуальный токен
    const actualToken = token || localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    
    if (!actualToken) {
      console.warn('Токен отсутствует. Запрос может быть отклонен.');
      return {};
    }
    
    // Проверяем, не истек ли токен
    try {
      if (actualToken) {
        const tokenParts = actualToken.split('.');
        if (tokenParts.length === 3) {
          const payload = JSON.parse(atob(tokenParts[1]));
          const expTime = payload.exp * 1000; // переводим в миллисекунды
          const now = Date.now();
          
          if (expTime < now) {
            console.error('ВНИМАНИЕ: Токен истек!');
          }
        }
      }
    } catch (err) {
      console.error('Ошибка при проверке токена:', err);
    }
    
    return {
      headers: {
        'Authorization': `Bearer ${actualToken}`,
        'Content-Type': 'application/json'
      }
    };
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
      // Формируем URL запроса
      let url = `${ORDER_SERVICE_URL}/orders?page=${page}&size=${size}`;
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
    console.log('Вызов fetchOrder с ID:', orderId);
    const actualToken = token || localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    
    if (!actualToken) {
      console.error('Попытка получить заказ без токена авторизации');
      setError('Для просмотра заказа необходима авторизация');
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    // Маршрут определен в бэкенде как /orders/{order_id}
    const url = `${ORDER_SERVICE_URL}/orders/${orderId}`;
    console.log('URL запроса заказа:', url);
    console.log('Токен присутствует:', !!actualToken);
    
    try {
      const config = getConfig();
      console.log('Конфигурация запроса:', JSON.stringify(config));
      console.log('Заголовки запроса:', {
        Authorization: config?.headers?.Authorization ? 'Bearer xxx...' : 'Отсутствует',
        ContentType: config?.headers?.['Content-Type']
      });
      
      const response = await axios.get(url, config);
      console.log('Ответ от сервера fetchOrder:', response.status, response.data);
      
      // Записываем данные заказа в состояние
      setCurrentOrder(response.data);
      
      // Возвращаем данные для использования компонентом
      return response.data;
    } catch (error) {
      console.error('Ошибка при получении заказа:', error);
      
      // Анализируем ошибку
      if (error.response) {
        // Обработка ответа с ошибкой от сервера
        console.error('Статус ошибки:', error.response.status);
        console.error('Данные ошибки:', error.response.data);
        
        if (error.response.status === 401) {
          setError('Для просмотра заказа необходима авторизация');
        } else if (error.response.status === 403) {
          setError('У вас нет прав для просмотра этого заказа');
        } else if (error.response.status === 404) {
          setError('Заказ не найден');
        } else {
          setError(`Ошибка сервера: ${error.response.data.detail || 'Неизвестная ошибка'}`);
        }
      } else if (error.request) {
        // Обработка отсутствия ответа от сервера
        console.error('Нет ответа от сервера:', error.request);
        setError('Не удалось получить ответ от сервера. Проверьте подключение к интернету');
      } else {
        // Другие ошибки
        console.error('Ошибка при настройке запроса:', error.message);
        setError(`Ошибка запроса: ${error.message}`);
      }
      
      setLoading(false);
      return null;
    }
  }, [token, ORDER_SERVICE_URL, getConfig, setCurrentOrder]);

  // Создание нового заказа
  const createOrder = useCallback(async (orderData) => {
    setLoading(true);
    setError(null);
    
    // Проверяем наличие токена
    const isAuthenticated = hasToken();
    console.log("Статус аутентификации при создании заказа:", isAuthenticated ? "Пользователь аутентифицирован" : "Пользователь не аутентифицирован");
    
    console.log("Исходные данные заказа:", orderData);
    console.log("URL:", `${ORDER_SERVICE_URL}/orders`);
    
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
        `${ORDER_SERVICE_URL}/orders`, 
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
    console.log('===== НАЧАЛО ОТМЕНЫ ЗАКАЗА =====');
    console.log('ID заказа:', orderId);
    console.log('Причина отмены:', reason);
    console.log('Наличие токена:', !!token);
    
    if (!token) {
      console.error('Нет токена авторизации для отмены заказа');
      const localToken = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      if (!localToken) {
        setError('Для отмены заказа необходима авторизация');
        console.error('Токен не найден ни в контексте, ни в localStorage');
        return null;
      }
      console.log('Токен найден в localStorage');
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      console.log('Конфигурация запроса:', JSON.stringify({
        headers: {
          Authorization: config.headers?.Authorization ? 'Bearer xxx...' : 'Отсутствует',
          'Content-Type': config.headers?.['Content-Type']
        }
      }));
      
      const url = `${ORDER_SERVICE_URL}/orders/${orderId}/cancel`;
      console.log('URL для отмены заказа:', url);
      
      // Проверка всех полей, переданных в запрос
      const requestData = { notes: reason };
      console.log('Данные запроса:', JSON.stringify(requestData));
      
      console.log('Отправка POST запроса для отмены заказа...');
      const response = await axios.post(
        url,
        requestData,
        config
      );
      
      console.log('Ответ сервера для отмены заказа:', response.status);
      console.log('Данные ответа:', response.data);
      
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
      console.error('===== ОШИБКА ПРИ ОТМЕНЕ ЗАКАЗА =====');
      console.error('Тип ошибки:', err.name);
      console.error('Сообщение ошибки:', err.message);
      
      if (err.response) {
        console.error('Статус ошибки:', err.response.status);
        console.error('Данные ошибки:', err.response.data);
        setError(err.response?.data?.detail || 'Не удалось отменить заказ');
      } else if (err.request) {
        console.error('Запрос был отправлен, но ответ не получен:', err.request);
        setError('Сервер не отвечает. Пожалуйста, повторите попытку позже.');
      } else {
        console.error('Произошла ошибка при настройке запроса:', err.message);
        setError(`Ошибка при отмене заказа: ${err.message}`);
      }
      
      return null;
    } finally {
      setLoading(false);
      console.log('===== ЗАВЕРШЕНИЕ ОТМЕНЫ ЗАКАЗА =====');
    }
  }, [token, getConfig, currentOrder]);

  // Получение статусов заказов
  const fetchOrderStatuses = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log("Запрос статусов заказов:", `${ORDER_SERVICE_URL}/order-statuses`);
      
      // Делаем запрос без аутентификации, так как статусы заказов публичны
      const response = await axios.get(
        `${ORDER_SERVICE_URL}/order-statuses`
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
      
      const url = `${ORDER_SERVICE_URL}/orders`;
      console.log("URL запроса:", url);
      
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
    // Проверяем наличие токена
    if (!hasToken()) {
      console.warn("Попытка получить все заказы без авторизации");
      setError("Для доступа к списку заказов необходима авторизация");
      return { items: [], total: 0, page: 1, limit: 10 };
    }
    
    // Проверяем права администратора
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
      
      // Убедимся, что page является числом
      if (adjustedParams.page && typeof adjustedParams.page !== 'number') {
        const parsed = parseInt(adjustedParams.page, 10);
        if (!isNaN(parsed)) {
          adjustedParams.page = parsed;
        } else {
          adjustedParams.page = 1;
          console.warn(`Некорректное значение page: "${adjustedParams.page}", установлено в 1`);
        }
      }
      
      // Убедимся, что size является числом
      if (adjustedParams.size && typeof adjustedParams.size !== 'number') {
        const parsed = parseInt(adjustedParams.size, 10);
        if (!isNaN(parsed)) {
          adjustedParams.size = parsed;
        } else {
          adjustedParams.size = 10;
          console.warn(`Некорректное значение size: "${adjustedParams.size}", установлено в 10`);
        }
      }
      
      console.log("Преобразованные параметры:", adjustedParams);
      
      const url = `${ORDER_SERVICE_URL}/admin/orders`;
      console.log("URL запроса:", url);
      
      const response = await axios.get(url, { 
        ...config,
        params: adjustedParams
      });
      
      console.log("Ответ сервера:", response.data);
      
      // Проверяем корректность ответа
      const data = response.data || { items: [], total: 0, page: 1, size: 10, pages: 1 };
      
      // Проверяем и конвертируем числовые значения
      data.total = typeof data.total === 'number' ? data.total : 0;
      data.page = typeof data.page === 'number' ? data.page : 1;
      data.size = typeof data.size === 'number' ? data.size : 10;
      data.pages = typeof data.pages === 'number' ? data.pages : Math.max(1, Math.ceil(data.total / data.size));
      
      // Проверяем наличие массива items
      if (!Array.isArray(data.items)) {
        console.error("Ответ не содержит массив items:", data);
        data.items = [];
      }
      
      return data;
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
      
      return { items: [], total: 0, page: 1, size: 10, pages: 1 };
    } finally {
      setLoading(false);
    }
  }, [hasToken, getConfig, user]);

  // Обновление статуса заказа (для администраторов)
  const updateOrderStatus = useCallback(async (orderId, statusData) => {
    console.log('Запрос на обновление статуса заказа:', { orderId, statusData });
    
    if (!token) {
      console.error('Попытка обновить статус заказа без токена авторизации');
      const localToken = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      
      if (!localToken) {
        setError('Для обновления статуса заказа необходима авторизация');
        return null;
      }
    }
    
    // Проверяем права администратора
    const userData = user || JSON.parse(localStorage.getItem(STORAGE_KEYS.USER_DATA) || "{}");
    const isAdmin = userData?.is_admin || userData?.is_super_admin;
    console.log('Проверка прав администратора:', { isAdmin, userData });
    
    if (!isAdmin) {
      console.error('Попытка обновить статус заказа без прав администратора');
      setError('Для обновления статуса заказа необходимы права администратора');
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Используем специальный эндпоинт для обновления статуса заказа
      const url = `${ORDER_SERVICE_URL}/admin/orders/${orderId}/status`;
      const config = getConfig();
      console.log('Отправка запроса на обновление статуса:', { url, statusData, config: { headers: config.headers } });
      
      // Отправляем POST запрос
      const response = await axios.post(url, statusData, config);
      console.log('Ответ на запрос обновления статуса:', { status: response.status, data: response.data });
      
      if (response.status >= 200 && response.status < 300) {
        return response.data;
      } else {
        console.error('Неожиданный статус ответа:', response.status);
        setError(`Неожиданный статус ответа: ${response.status}`);
        return null;
      }
    } catch (err) {
      console.error('Ошибка при обновлении статуса заказа:', err);
      let errorMessage = 'Не удалось обновить статус заказа';
      
      if (err.response) {
        errorMessage = err.response.data.detail || errorMessage;
      } else if (err.request) {
        errorMessage = 'Сервер не отвечает. Проверьте соединение с интернетом.';
      } else {
        errorMessage = `Ошибка: ${err.message}`;
      }
      
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [token, user, getConfig]);

  // Получение одного заказа по ID (для администраторов)
  const getAdminOrderById = useCallback(async (orderId) => {
    console.log('Вызов getAdminOrderById с ID:', orderId);
    const actualToken = token || localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    
    if (!actualToken) {
      console.error('Попытка получить заказ администратором без токена авторизации');
      setError('Для доступа к заказу необходима авторизация администратора');
      return null;
    }
    
    // Проверка прав администратора
    const userData = user || JSON.parse(localStorage.getItem(STORAGE_KEYS.USER_DATA) || "{}");
    const isAdmin = userData?.is_admin || userData?.is_super_admin;
    
    if (!isAdmin) {
      console.error('Пользователь не имеет прав администратора');
      setError('Доступ запрещен. Требуются права администратора');
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    // Маршрут определен в бэкенде как /admin/orders/{order_id}
    const url = `${ORDER_SERVICE_URL}/admin/orders/${orderId}`;
    console.log('Запрос заказа администратором:', url);
    console.log('Токен присутствует:', !!actualToken);
    console.log('Пользователь админ:', isAdmin);
    
    try {
      const config = getConfig();
      console.log('Конфигурация запроса:', JSON.stringify(config));
      console.log('Заголовки запроса:', {
        Authorization: config?.headers?.Authorization ? 'Bearer xxx...' : 'Отсутствует',
        ContentType: config?.headers?.['Content-Type']
      });
      
      const response = await axios.get(url, config);
      console.log('Ответ от сервера getAdminOrderById:', response.status, response.data);
      
      // Записываем данные заказа в состояние
      setCurrentOrder(response.data);
      
      // Возвращаем данные для использования компонентом
      return response.data;
    } catch (error) {
      console.error('Ошибка при получении заказа администратором:', error);
      
      // Анализируем ошибку
      if (error.response) {
        // Обработка ответа с ошибкой от сервера
        console.error('Статус ошибки:', error.response.status);
        console.error('Данные ошибки:', error.response.data);
        
        if (error.response.status === 401) {
          setError('Для доступа к заказу необходима авторизация');
        } else if (error.response.status === 403) {
          setError('У вас нет прав администратора для просмотра этого заказа');
        } else if (error.response.status === 404) {
          setError('Заказ не найден');
        } else {
          setError(`Ошибка сервера: ${error.response.data.detail || 'Неизвестная ошибка'}`);
        }
      } else if (error.request) {
        // Обработка отсутствия ответа от сервера
        console.error('Нет ответа от сервера:', error.request);
        setError('Не удалось получить ответ от сервера. Проверьте подключение к интернету');
      } else {
        // Другие ошибки
        console.error('Ошибка при настройке запроса:', error.message);
        setError(`Ошибка запроса: ${error.message}`);
      }
      
      setLoading(false);
      return null;
    }
  }, [token, user, ORDER_SERVICE_URL, getConfig, setCurrentOrder]);

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