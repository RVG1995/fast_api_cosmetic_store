import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
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
  refreshAuth: async () => {},
  isAuthenticated: false
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
      console.log("Проверка аутентификации...");
      console.log("Текущие куки документа:", document.cookie);
      const res = await authAPI.getCurrentUser();
      setUser(res.data);
      setError(null);

      if (res.data && res.data.id) {
        // Права
        try {
          const permRes = await authAPI.checkPermissions('admin_access');
          if (permRes.data && (permRes.data.is_admin !== undefined || permRes.data.is_super_admin !== undefined)) {
            setUser(prevUser => ({
              ...prevUser,
              is_admin: permRes.data.is_admin,
              is_super_admin: permRes.data.is_super_admin
            }));
          }
        } catch (permError) {
          console.error("Ошибка при проверке разрешений при инициализации:", permError);
        }

        // Профиль
        try {
          const profileRes = await authAPI.getUserProfile();
          if (profileRes?.data) {
            setUser(prevUser => ({
              ...prevUser,
              ...profileRes.data
            }));
          }
        } catch (profileError) {
          console.error("Ошибка при получении профиля пользователя:", profileError);
        }
      }
    } catch (error) {
      console.error("Auth error:", error.response?.data || error.message);
      console.error("Статус ошибки:", error.response?.status);
      console.error("Заголовки ответа:", error.response?.headers);
      setUser(null);
      setError(error.response?.data?.detail || error.message);
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
      await authAPI.login(credentials);
      // После успешного логина сразу делаем новый запрос для получения данных пользователя
      await checkAuth();
      return { success: true };
    } catch (error) {
      console.error("Ошибка при входе:", error);
      console.error("Статус ошибки:", error.response?.status);
      console.error("Данные ошибки:", error.response?.data);
      setError(error.response?.data?.detail || error.message);
      return { success: false, error: error.response?.data?.detail || error.message };
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
      setUser(null);
      setError(null);
      navigate('/login');
    } catch (error) {
      console.error("Ошибка при выходе:", error);
      setUser(null);
      setError(error.response?.data?.detail || error.message);
    }
  };

  // Функции для проверки ролей
  const isAdmin = Boolean(user?.is_admin || user?.is_super_admin);

  const isSuperAdmin = () => {
    try {
      // Прямая проверка флага суперадмина из ответа сервера
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

  // Асинхронная проверка прав через специальный эндпоинт
  const checkPermission = async (permission, resourceType, resourceId) => {
    try {
      if (!user) return false;
      
      console.log('Вызов checkPermission с параметрами:', { permission, resourceType, resourceId });
      
      const res = await authAPI.checkPermissions(permission, resourceType, resourceId);
      console.log('Результат проверки разрешений:', res.data);
      
      // Если получили информацию об админских правах - обновляем состояние пользователя
      if (res.data?.is_admin !== undefined) {
        setUser(prevUser => ({
          ...prevUser,
          is_admin: res.data.is_admin,
          is_super_admin: res.data.is_super_admin
        }));
      }
      
      return res.data?.has_permission === true;
    } catch (error) {
      console.error("Ошибка при проверке разрешений:", error);
      return false;
    }
  };

  // Функция получения полного профиля пользователя
  const getUserProfile = useCallback(async () => {
    try {
      if (!user) return null;
      const res = await authAPI.getUserProfile();
      return res.data;
    } catch (error) {
      console.error("Ошибка при получении профиля:", error);
      return null;
    }
  }, []);

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
    login,
    checkPermission,
    getUserProfile,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};
