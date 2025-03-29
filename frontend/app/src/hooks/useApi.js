import { useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { API_URL } from '../utils/constants';

/**
 * Хук для выполнения API-запросов с автоматическим добавлением токена авторизации
 * @returns {Object} Методы для работы с API
 */
export function useApi() {
  const [loading, setLoading] = useState(false);
  const { token, logout } = useAuth();

  /**
   * Выполнение API-запроса
   * @param {string} endpoint - Конечная точка API (например, '/products')
   * @param {Object} options - Опции запроса
   * @returns {Promise<Object>} Результат запроса
   */
  const apiRequest = useCallback(async (endpoint, options = {}) => {
    setLoading(true);
    
    try {
      const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;
      
      // Формируем заголовки запроса
      const headers = {
        'Content-Type': 'application/json',
        ...options.headers
      };
      
      // Добавляем токен авторизации, если он есть
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(url, {
        ...options,
        headers
      });
      
      // Обрабатываем возможные ошибки авторизации
      if (response.status === 401) {
        // Если токен недействителен, выходим из системы
        logout();
        return { 
          success: false, 
          message: 'Ваша сессия истекла. Пожалуйста, войдите снова.' 
        };
      }
      
      // Пытаемся получить JSON-ответ
      let data;
      try {
        data = await response.json();
      } catch (error) {
        return { 
          success: false, 
          message: 'Не удалось получить ответ от сервера' 
        };
      }
      
      // Проверяем успешность запроса
      if (!response.ok) {
        return {
          success: false,
          message: data.detail || data.message || 'Произошла ошибка при запросе к серверу',
          errors: data.errors || null,
          status: response.status,
          data
        };
      }
      
      // Возвращаем успешный ответ
      return {
        success: true,
        data,
        status: response.status
      };
    } catch (error) {
      console.error('API request error:', error);
      return {
        success: false,
        message: 'Не удалось подключиться к серверу. Проверьте ваше интернет-соединение.',
        error
      };
    } finally {
      setLoading(false);
    }
  }, [token, logout]);
  
  return {
    apiRequest,
    loading
  };
}

export default useApi;