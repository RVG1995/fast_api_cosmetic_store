import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import { useState, useEffect } from 'react';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, checkPermission } = useAuth();
  const [hasPermission, setHasPermission] = useState(false);
  const [permissionLoading, setPermissionLoading] = useState(true);

  useEffect(() => {
    console.log("AdminRoute: Проверка прав доступа...");
    console.log("Текущий пользователь:", user);
    console.log("Требуется super admin:", requireSuperAdmin);
    
    const checkAccess = async () => {
      if (!user) {
        console.log("AdminRoute: Пользователь не авторизован");
        setPermissionLoading(false);
        return;
      }

      try {
        // Проверяем соответствующие разрешения через API
        const permission = requireSuperAdmin ? 'super_admin_access' : 'admin_access';
        console.log(`AdminRoute: Запрашиваем разрешение ${permission}`);
        
        // Непосредственный вызов проверки разрешений
        const hasAccess = await checkPermission(permission);
        console.log(`AdminRoute: Результат проверки разрешения:`, hasAccess);
        
        setHasPermission(hasAccess);
      } catch (error) {
        console.error('AdminRoute: Ошибка при проверке разрешений:', error);
        setHasPermission(false);
      } finally {
        setPermissionLoading(false);
      }
    };

    if (checkPermission && !loading) {
      checkAccess();
    }
  }, [user, requireSuperAdmin, checkPermission, loading]);

  // Добавляем дополнительное логирование
  useEffect(() => {
    console.log("AdminRoute состояние:", {
      loading,
      permissionLoading,
      hasPermission,
      userExists: !!user
    });
  }, [loading, permissionLoading, hasPermission, user]);

  if (loading || permissionLoading) {
    console.log("AdminRoute: Отображение загрузки");
    return <LoadingSpinner />;
  }

  if (!user) {
    console.log("AdminRoute: Перенаправление на страницу логина");
    return <Navigate to="/login" />;
  }
  
  if (!hasPermission) {
    console.log("AdminRoute: Нет доступа, перенаправление на главную");
    return <Navigate to="/" />;
  }

  console.log("AdminRoute: Доступ разрешен, отображение содержимого");
  return children;
};

export default AdminRoute;
