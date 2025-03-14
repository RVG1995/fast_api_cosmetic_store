import React, { createContext, useContext, useEffect, useState } from "react";
import { authAPI } from "../utils/api";
import { useNavigate } from 'react-router-dom';

// Создаем контекст аутентификации
const AuthContext = createContext({
  user: null,
  loading: true,
  error: null,
  isAdmin: () => false,
  isSuperAdmin: () => false,
  isActivated: () => false,
  logout: async () => {},
  login: async () => {},
  refreshAuth: async () => {}
});

// Кастомный хук для удобного использования контекста
export const useAuth = () => {
  return useContext(AuthContext);
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const checkAuth = async () => {
    try {
      console.log("Checking authentication...");
      const res = await authAPI.getCurrentUser();
      console.log("Auth successful:", res.data);
      
      // Если получили пользователя, но в localStorage нет токена, 
      // значит он только в куках - сохраним в localStorage для заголовков
      if (res.data && !localStorage.getItem('access_token') && res.headers?.authorization) {
        const token = res.headers.authorization.replace('Bearer ', '');
        localStorage.setItem('access_token', token);
        console.log('Токен сохранен в localStorage');
      }
      
      setUser(res.data);
      setError(null);
    } catch (error) {
      console.error("Auth error:", error.response?.data || error.message);
      setUser(null);
      setError(error.response?.data?.detail || error.message);
      // Если ошибка аутентификации, удаляем токен
      localStorage.removeItem('access_token');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Оборачиваем в блок try-catch для предотвращения ошибок при монтировании
    try {
      checkAuth();
    } catch (err) {
      console.error("Error in auth check:", err);
      setLoading(false);
      setError("Ошибка при проверке аутентификации");
    }
  }, []);

  // Функция для входа в систему
  const login = async (credentials) => {
    try {
      const response = await authAPI.login(credentials);
      // Сохраняем токен в localStorage
      if (response.data.access_token) {
        localStorage.setItem('access_token', response.data.access_token);
        console.log('Токен сохранен при входе:', response.data.access_token.substring(0, 20) + '...');
      }
      await checkAuth(); // Обновляем данные пользователя
      return { success: true };
    } catch (error) {
      console.error("Ошибка при входе:", error);
      setError(error.response?.data?.detail || error.message);
      return { success: false, error: error.response?.data?.detail || error.message };
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
      setUser(null);
      setError(null);
      // Удаляем токен из localStorage
      localStorage.removeItem('access_token');
      console.log('Токен удален при выходе');
      navigate('/login');
    } catch (error) {
      console.error("Ошибка при выходе:", error);
      setUser(null);
      setError(error.response?.data?.detail || error.message);
      // Всё равно удаляем токен на случай ошибки
      localStorage.removeItem('access_token');
    }
  };

  // Функции для проверки ролей
  const isAdmin = () => {
    try {
      // Проверяем сначала прямые флаги из JWT-токена в ответе сервера
      if (user && 'is_admin' in user) {
        console.log('Проверка админа по is_admin:', user.is_admin);
        return Boolean(user.is_admin || user.is_super_admin);
      }
      
      // Для обратной совместимости, если точных флагов нет
      console.log('Проверка админа через другие поля (для совместимости)');
      return false;
    } catch (e) {
      console.error("Ошибка при проверке прав администратора:", e);
      return false;
    }
  };

  const isSuperAdmin = () => {
    try {
      // Прямая проверка флага суперадмина из JWT
      if (user && 'is_super_admin' in user) {
        console.log('Проверка суперадмина по is_super_admin:', user.is_super_admin);
        return Boolean(user.is_super_admin);
      }
      
      console.log('Проверка суперадмина через другие поля (для совместимости)');
      return false;
    } catch (e) {
      console.error("Ошибка при проверке прав суперадминистратора:", e);
      return false;
    }
  };

  // Функция для проверки активации пользователя
  const isActivated = () => {
    try {
      if (user && 'is_active' in user) {
        return Boolean(user.is_active);
      }
      
      // По умолчанию считаем пользователя активным, если мы получили его данные
      return Boolean(user);
    } catch (e) {
      console.error("Ошибка при проверке активации пользователя:", e);
      return false;
    }
  };

  const contextValue = {
    user, 
    setUser, 
    loading, 
    logout, 
    isAdmin, 
    isSuperAdmin,
    isActivated,
    error,
    refreshAuth: checkAuth,
    login
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};
