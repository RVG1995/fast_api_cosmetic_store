import { createContext, useContext, useEffect, useState } from "react";
import { authAPI, adminAPI } from "../utils/api";

// Создаем контекст аутентификации
const AuthContext = createContext();

// Хук для использования контекста
export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      console.log("Checking authentication...");
      const res = await authAPI.getCurrentUser();
      console.log("Auth successful:", res.data);
      setUser(res.data);
    } catch (error) {
      console.error("Auth error:", error.response?.data || error.message);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const logout = async () => {
    try {
      await authAPI.logout();
      setUser(null);
    } catch (error) {
      console.error("Ошибка при выходе:", error);
    }
  };

  // Новые функции для проверки ролей
  const isAdmin = () => {
    // Если у пользователя есть явные флаги (AdminUserReadSchema)
    if (user && 'is_admin' in user) {
      return user.is_admin || user.is_super_admin;
    }
    
    // Если флагов нет, но есть доступ к админ-эндпоинту, пользователь является админом
    // (эта проверка сработает при первом обращении к админ-странице)
    if (user) {
      // Проверяем доступ к админ-панели без блокировки интерфейса
      adminAPI.checkAdminAccess()
      .then(() => {
        // Если успешно, обновляем данные пользователя
        checkAuth();
        return true;
      })
      .catch(() => {
        return false;
      });
    }
    
    return false;
  };

  const isSuperAdmin = () => {
    // Если у пользователя есть явные флаги (AdminUserReadSchema)
    if (user && 'is_super_admin' in user) {
      return user.is_super_admin;
    }
    
    // Если флагов нет, но есть доступ к суперадмин-эндпоинту, пользователь является суперадмином
    if (user) {
      // Проверяем доступ к суперадмин-панели без блокировки интерфейса
      adminAPI.checkSuperAdminAccess()
      .then(() => {
        // Если успешно, обновляем данные пользователя
        checkAuth();
        return true;
      })
      .catch(() => {
        return false;
      });
    }
    
    return false;
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      setUser, 
      loading, 
      logout, 
      isAdmin, 
      isSuperAdmin,
      refreshAuth: checkAuth
    }}>
      {children}
    </AuthContext.Provider>
  );
};
