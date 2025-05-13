import React, { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';
import { API_URLS } from '../utils/constants';

// URL сервиса заказов
const ORDER_SERVICE_URL = API_URLS.ORDER_SERVICE;
// Префикс API не используется, так как пути уже определены в роутерах бэкенда
// Корректные пути: /orders, /admin/orders, /order-statuses

// Создаем контекст для заказов
const OrderContext = createContext();

// Хук для использования контекста заказов
export const useOrders = () => {
  return useContext(OrderContext);
};

// Провайдер контекста заказов
export const OrderProvider = ({ children }) => {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [currentOrder, setCurrentOrder] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [promoCode, setPromoCode] = useState(null);

  // Функция для получения конфигурации запроса
  const getConfig = useCallback(() => {
    console.log('getConfig: document.cookie =', document.cookie);
    return {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json'
      }
    };
  }, []);

  // Проверка авторизации пользователя
  const isAuthenticated = useCallback(() => {
    return !!user; // Проверяем наличие пользователя в контексте
  }, [user]);

  // Получение списка заказов пользователя
  const fetchUserOrders = useCallback(async (page = 1, size = 10, statusId = null) => {
    // Проверяем авторизацию пользователя
    if (!isAuthenticated()) {
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
  }, [isAuthenticated, getConfig]);

  // Получение одного заказа по ID
  const fetchOrder = useCallback(async (orderId) => {
    console.log('Вызов fetchOrder с ID:', orderId);
    
    if (!isAuthenticated()) {
      console.error('Попытка получить заказ без авторизации');
      setError('Для просмотра заказа необходима авторизация');
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    // Маршрут определен в бэкенде как /orders/{order_id}
    const url = `${ORDER_SERVICE_URL}/orders/${orderId}`;
    console.log('URL запроса заказа:', url);
    
    try {
      const config = getConfig();
      console.log('Конфигурация запроса:', JSON.stringify(config));
      
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
  }, [isAuthenticated, getConfig]);

  // Получение статистики заказов пользователя
  const getUserOrderStatistics = useCallback(async () => {
    console.log('Вызов getUserOrderStatistics');
    if (!user) {
      console.error('Попытка получить статистику заказов без авторизации');
      setError('Для просмотра статистики необходима авторизация');
      return null;
    }
    setLoading(true);
    setError(null);
    const url = `${ORDER_SERVICE_URL}/orders/statistics`;
    console.log('URL запроса статистики заказов:', url);
    try {
      const config = getConfig();
      console.log('Заголовки запроса:', {
        Authorization: config?.headers?.Authorization ? 'Bearer xxx...' : 'Отсутствует',
        ContentType: config?.headers?.['Content-Type']
      });
      const response = await axios.get(url, config);
      console.log('Ответ от сервера getUserOrderStatistics:', response.status, response.data);
      return response.data;
    } catch (error) {
      console.error('Ошибка при получении статистики заказов:', error);
      if (error.response) {
        if (error.response.status === 401) {
          setError('Для просмотра статистики необходима авторизация');
        } else {
          setError(`Ошибка сервера: ${error.response.data.detail || 'Неизвестная ошибка'}`);
        }
      } else if (error.request) {
        setError('Не удалось получить ответ от сервера. Проверьте подключение к интернету');
      } else {
        setError(`Ошибка запроса: ${error.message}`);
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, [user, getConfig]);

  // Создание нового заказа
  const createOrder = async (orderData) => {
    setLoading(true);
    setError(null);
    
    // Проверяем наличие токена
    const userAuthenticated = isAuthenticated();
    console.log("Статус аутентификации при создании заказа:", userAuthenticated ? "Пользователь аутентифицирован" : "Пользователь не аутентифицирован");
    
    console.log("Исходные данные заказа:", orderData);
    console.log("Текущий промокод в контексте:", promoCode);
    console.log("URL:", `${ORDER_SERVICE_URL}/orders`);
    
    try {
      // Проверка наличия обязательных полей
      if (!orderData.fullName && !orderData.full_name && !orderData.shipping_address?.full_name) {
        setError("Необходимо указать ФИО получателя");
        return null;
      }
      
      if (!orderData.delivery_address && !orderData.shipping_address?.address) {
        setError("Необходимо указать адрес доставки");
        return null;
      }
      
      // Подготовка данных в новом формате
      const newOrderData = {
        items: orderData.items,
        full_name: orderData.shipping_address?.full_name || orderData.full_name || orderData.fullName || "",
        email: orderData.contact_email || orderData.email || "",
        phone: orderData.contact_phone || orderData.phone || "",
        delivery_address: orderData.shipping_address?.address || orderData.delivery_address || "",
        comment: orderData.notes || orderData.comment || "",
        personal_data_agreement: Boolean(orderData.personal_data_agreement || orderData.personalDataAgreement),
        receive_notifications: Boolean(orderData.receive_notifications)
      };
      
      // Добавляем информацию о типе доставки и пункте выдачи BoxBerry
      if (orderData.delivery_type) {
        newOrderData.delivery_type = orderData.delivery_type;
      }
      
      if (orderData.boxberry_point_id) {
        newOrderData.boxberry_point_id = orderData.boxberry_point_id;
      }
      
      if (orderData.boxberry_point_address) {
        newOrderData.boxberry_point_address = orderData.boxberry_point_address;
      }
      
      if (orderData.boxberry_city_code) {
        newOrderData.boxberry_city_code = orderData.boxberry_city_code;
      }
      
      // Для обратной совместимости с существующим кодом
      if (orderData.is_boxberry_pickup && !newOrderData.delivery_type) {
        newOrderData.delivery_type = "boxberry";
      }
      
      // Добавляем промокод, если он есть
      if (promoCode) {
        // Если есть promoCode.code, используем его (текстовый код промокода)
        if (promoCode.code) {
          newOrderData.promo_code = promoCode.code;
          console.log("Добавлен промокод в данные заказа:", promoCode.code);
        }
        
        // Если есть promoCode.id, используем его (ID промокода в базе данных)
        if (promoCode.id) {
          newOrderData.promo_code_id = promoCode.id;
          console.log("Добавлен ID промокода в данные заказа:", promoCode.id);
        }
      }
      
      // Проверяем итоговый объект на наличие всех обязательных полей
      const requiredFields = ['full_name', 'phone', 'delivery_address', 'personal_data_agreement'];
      const missingFields = requiredFields.filter(field => !newOrderData[field]);
      
      if (missingFields.length > 0) {
        const fieldNames = {
          full_name: 'ФИО получателя',
          email: 'Email',
          phone: 'Телефон',
          delivery_address: 'Адрес доставки',
          personal_data_agreement: 'Согласие на обработку персональных данных'
        };
        
        const errorMsg = `Необходимо заполнить следующие поля: ${missingFields.map(f => fieldNames[f]).join(', ')}`;
        setError(errorMsg);
        return null;
      }
      
      console.log("Преобразованные данные заказа:", newOrderData);
      
      // Определяем конфигурацию заголовков
      const config = getConfig();
      console.log("Используемые заголовки:", config);
      
      console.log("Финальные данные заказа для отправки:", JSON.stringify(newOrderData));
      
      const response = await axios.post(
        `${ORDER_SERVICE_URL}/orders`, 
        newOrderData,
        config
      );
      
      const data = response.data;
      console.log("Ответ сервера после создания заказа:", data);
      
      // Очищаем промокод после успешного создания заказа
      clearPromoCode();
      
      setLoading(false);
      return data;
    } catch (error) {
      console.error("Ошибка при создании заказа:", error);
      
      if (error.response) {
        console.error("Детали ошибки:", error.response.data);
        
        // Проверяем формат ошибки
        if (error.response.data.detail && Array.isArray(error.response.data.detail)) {
          const errorMessages = error.response.data.detail.map(err => {
            // Извлекаем понятное сообщение из ошибки
            if (typeof err.msg === 'string') {
              // Удаляем префикс "Value error, " если он есть
              const cleanMsg = err.msg.replace('Value error, ', '');
              
              // Добавляем название поля, если оно есть
              const fieldName = err.loc && err.loc.length > 1 ? err.loc[1] : '';
              const fieldLabels = {
                'full_name': 'ФИО',
                'email': 'Email',
                'phone': 'Телефон',
                'delivery_address': 'Адрес доставки',
                'comment': 'Комментарий',
                'promo_code': 'Промокод'
              };
              
              const fieldLabel = fieldLabels[fieldName] || fieldName;
              
              return fieldLabel ? `${fieldLabel}: ${cleanMsg}` : cleanMsg;
            }
            return typeof err === 'object' ? JSON.stringify(err) : String(err);
          }).join('. ');
          
          setError(errorMessages);
        } else if (error.response.data.detail && typeof error.response.data.detail === 'string') {
          setError(error.response.data.detail);
        } else {
          setError("Ошибка при создании заказа. Попробуйте еще раз.");
        }
      } else {
        setError("Ошибка соединения с сервером. Проверьте подключение к интернету.");
      }
      
      setLoading(false);
      return null;
    }
  };

  // Отмена заказа
  const cancelOrder = useCallback(async (orderId, reason) => {
    console.log('===== НАЧАЛО ОТМЕНЫ ЗАКАЗА =====');
    console.log('ID заказа:', orderId);
    console.log('Причина отмены:', reason);
  
    
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
  }, [ getConfig, currentOrder]);

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
    if (!isAuthenticated()) {
      console.warn("Попытка получить заказы пользователя без авторизации");
      setError("Для просмотра заказов необходима авторизация");
      return { items: [], total: 0, page: 1, limit: 10 };
    }
    
    // Получаем ID пользователя
    const userData = user;
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
  }, [isAuthenticated, getConfig, user]);
  
  // Получение всех заказов (для администраторов)
  const getAllOrders = useCallback(async (params = {}) => {
    // Проверяем наличие токена
    if (!isAuthenticated()) {
      console.warn("Попытка получить все заказы без авторизации");
      setError("Для доступа к списку заказов необходима авторизация");
      return { items: [], total: 0, page: 1, limit: 10 };
    }
    
    // Проверяем права администратора
    const userData = user ;
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
  }, [isAuthenticated, getConfig, user]);

  // Обновление статуса заказа (для администраторов)
  const updateOrderStatus = useCallback(async (orderId, statusData) => {
    console.log('Запрос на обновление статуса заказа:', { orderId, statusData });
    
    
    
    // Проверяем права администратора
    const userData = user ;
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
        errorMessage = err.message || errorMessage;
      }
      
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [getConfig, user]);

  // Обновление статуса оплаты заказа (для администраторов)
  const updateOrderPaymentStatus = useCallback(async (orderId, isPaid) => {
    console.log('Запрос на обновление статуса оплаты заказа:', { orderId, isPaid });
    
    // Проверяем права администратора
    const userData = user;
    const isAdmin = userData?.is_admin || userData?.is_super_admin;
    console.log('Проверка прав администратора:', { isAdmin, userData });
    
    if (!isAdmin) {
      console.error('Попытка обновить статус оплаты заказа без прав администратора');
      setError('Для обновления статуса оплаты заказа необходимы права администратора');
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Используем PUT эндпоинт для обновления заказа
      const url = `${ORDER_SERVICE_URL}/admin/orders/${orderId}`;
      const config = getConfig();
      const updateData = { is_paid: isPaid };
      
      console.log('Отправка запроса на обновление статуса оплаты:', { url, updateData, config: { headers: config.headers } });
      
      // Отправляем PUT запрос
      const response = await axios.put(url, updateData, config);
      console.log('Ответ на запрос обновления статуса оплаты:', { status: response.status, data: response.data });
      
      if (response.status >= 200 && response.status < 300) {
        return response.data;
      } else {
        console.error('Неожиданный статус ответа:', response.status);
        setError(`Неожиданный статус ответа: ${response.status}`);
        return null;
      }
    } catch (err) {
      console.error('Ошибка при обновлении статуса оплаты заказа:', err);
      let errorMessage = 'Не удалось обновить статус оплаты заказа';
      
      if (err.response) {
        errorMessage = err.response.data.detail || errorMessage;
      } else if (err.request) {
        errorMessage = 'Сервер не отвечает. Проверьте соединение с интернетом.';
      } else {
        errorMessage = err.message || errorMessage;
      }
      
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [getConfig, user]);

  // Обновление товаров в заказе (для администраторов)
  const updateOrderItems = useCallback(async (orderId, itemsData) => {
    console.log('Запрос на обновление товаров в заказе:', { orderId, itemsData });
    
    // Проверяем права администратора
    const userData = user;
    const isAdmin = userData?.is_admin || userData?.is_super_admin;
    console.log('Проверка прав администратора:', { isAdmin, userData });
    
    if (!isAdmin) {
      console.error('Попытка обновить товары в заказе без прав администратора');
      setError('Для обновления товаров в заказе необходимы права администратора');
      return null;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Используем POST эндпоинт для обновления товаров в заказе
      const url = `${ORDER_SERVICE_URL}/admin/orders/${orderId}/items`;
      const config = getConfig();
      
      console.log('Отправка запроса на обновление товаров в заказе:', { url, itemsData, config: { headers: config.headers } });
      
      // Отправляем POST запрос
      const response = await axios.post(url, itemsData, config);
      console.log('Ответ на запрос обновления товаров в заказе:', { status: response.status, data: response.data });
      
      if (response.status >= 200 && response.status < 300) {
        return response.data;
      } else {
        console.error('Неожиданный статус ответа:', response.status);
        setError(`Неожиданный статус ответа: ${response.status}`);
        return null;
      }
    } catch (err) {
      console.error('Ошибка при обновлении товаров в заказе:', err);
      let errorMessage = 'Не удалось обновить товары в заказе';
      
      if (err.response) {
        errorMessage = err.response.data.detail || errorMessage;
        
        // Обработка валидационных ошибок
        if (err.response.data.errors) {
          const errors = err.response.data.errors;
          const errorMessages = [];
          
          for (const key in errors) {
            errorMessages.push(`${key}: ${errors[key]}`);
          }
          
          errorMessage = errorMessages.join('\n');
        }
      } else if (err.request) {
        errorMessage = 'Сервер не отвечает. Проверьте соединение с интернетом.';
      } else {
        errorMessage = err.message || errorMessage;
      }
      
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [getConfig, user]);

  // Получение одного заказа по ID (для администраторов)
  const getAdminOrderById = useCallback(async (orderId) => {
    console.log('Вызов getAdminOrderById с ID:', orderId);
  
    
    // Проверка прав администратора
    const userData = user;
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
    console.log('Токен присутствует:');
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
  }, [user, getConfig, setCurrentOrder]);

  // Проверка промокода
  const checkPromoCode = useCallback(async (code, email, phone) => {
    console.log(`Проверка промокода: ${code}, email: ${email}, phone: ${phone}`);
    setLoading(true);
    setError(null);
    
    try {
      const config = getConfig();
      const response = await axios.post(
        `${ORDER_SERVICE_URL}/promo-codes/check`, 
        { code, email, phone },
        config
      );
      
      console.log("Ответ сервера при проверке промокода:", response.data);
      
      if (response.data.is_valid) {
        // Сохраняем информацию о промокоде в состоянии
        setPromoCode({
          code,
          discountPercent: response.data.discount_percent,
          discountAmount: response.data.discount_amount,
          message: response.data.message,
          // Сохраняем ID промокода
          promoCodeId: response.data.promo_code?.id
        });
      } else {
        setPromoCode(null);
        setError(response.data.message);
      }
      
      return response.data;
    } catch (err) {
      console.error("Ошибка при проверке промокода:", err);
      setPromoCode(null);
      
      // Обработка объектов ошибок и преобразование их в строки
      let errorMessage = "Не удалось проверить промокод";
      
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          // Если ошибка представлена массивом объектов (валидация FastAPI)
          errorMessage = err.response.data.detail
            .map(item => {
              if (typeof item === 'string') return item;
              if (typeof item === 'object') return item.msg || JSON.stringify(item);
              return String(item);
            })
            .join('. ');
        } else if (typeof err.response.data.detail === 'object') {
          // Если ошибка - объект
          errorMessage = err.response.data.detail.msg || JSON.stringify(err.response.data.detail);
        } else {
          // Если ошибка - строка или другой тип
          errorMessage = String(err.response.data.detail);
        }
      }
      
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [getConfig]);
  
  // Очистка промокода
  const clearPromoCode = useCallback(() => {
    setPromoCode(null);
  }, []);

  // Расчет скидки на основе промокода
  const calculateDiscount = useCallback((totalPrice) => {
    if (!promoCode) return 0;
    
    if (promoCode.discountPercent) {
      // Скидка в процентах
      return Math.floor(totalPrice * promoCode.discountPercent / 100);
    } else if (promoCode.discountAmount) {
      // Фиксированная скидка
      return Math.min(promoCode.discountAmount, totalPrice);
    }
    
    return 0;
  }, [promoCode]);

  // Создание заказа из админки
  const createAdminOrder = async (orderData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post(
        `${ORDER_SERVICE_URL}/admin/orders`, 
        orderData, 
        { withCredentials: true }
      );
      
      console.log('Ответ от сервера createAdminOrder:', response.data);
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Ошибка при создании заказа';
      console.error('Ошибка при создании заказа из админки:', errorMsg);
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

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
    updateOrderPaymentStatus,
    updateOrderItems,
    cancelOrder,
    createOrder,
    getUserOrders,
    getAllOrders,
    getAdminOrderById,
    getUserOrderStatistics,
    
    // Функции для работы с промокодами
    promoCode,
    checkPromoCode,
    clearPromoCode,
    calculateDiscount,
    createAdminOrder
  };

  return (
    <OrderContext.Provider value={contextValue}>
      {children}
    </OrderContext.Provider>
  );
};

export default OrderContext; 