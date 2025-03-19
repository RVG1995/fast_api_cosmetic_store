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
      console.log("Проверка аутентификации...");
      console.log("Текущие куки документа:", document.cookie);
      
      const res = await authAPI.getCurrentUser();
      console.log("Auth successful:", res.data);
      
      setUser(res.data);
      setError(null);
      
      // Сразу после загрузки базовой информации о пользователе проверяем его разрешения
      if (res.data && res.data.id) {
        try {
          console.log("Загружаем информацию о разрешениях пользователя...");
          // Запрос для проверки админских прав
          const permRes = await authAPI.checkPermissions('admin_access');
          console.log("Результат проверки разрешений:", permRes.data);
          
          // Обновляем данные о пользователе с учетом его прав
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
      const response = await authAPI.login(credentials);
      
      // Сохраняем токен для использования микросервисами через заголовки
      if (response.data.access_token) {
        console.log('Токен сохранен в localStorage для микросервисов');
      }
      
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
      // Удаляем токен из localStorage при выходе      navigate('/login');
    } catch (error) {
      console.error("Ошибка при выходе:", error);
      setUser(null);
      setError(error.response?.data?.detail || error.message);
      // Всё равно удаляем токен из localStorage
    }
  };

  // Функции для проверки ролей
  const isAdmin = () => {
    try {
      // Проверяем сначала прямые флаги из ответа сервера
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
  const getUserProfile = async () => {
    try {
      if (!user) return null;
      
      const res = await authAPI.getUserProfile();
      return res.data;
    } catch (error) {
      console.error("Ошибка при получении профиля:", error);
      return null;
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
    login,
    checkPermission,
    getUserProfile
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};
