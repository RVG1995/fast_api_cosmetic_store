import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import { useState, useEffect } from 'react';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, isAdmin, isSuperAdmin, checkPermissions } = useAuth();
  const [permissionChecked, setPermissionChecked] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);

  useEffect(() => {
    const verifyPermissions = async () => {
      try {
        // Проверка прав доступа через сервер
        const permission = requireSuperAdmin ? 'super_admin' : 'admin';
        const hasAccess = await checkPermissions(permission, 'admin_panel', null);
        setHasPermission(hasAccess);
      } catch (error) {
        console.error('Ошибка при проверке прав доступа:', error);
        setHasPermission(false);
      } finally {
        setPermissionChecked(true);
      }
    };

    if (user && !loading) {
      verifyPermissions();
    }
  }, [user, loading, checkPermissions, requireSuperAdmin]);

  if (loading || (user && !permissionChecked)) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" />;
  }

  // Сначала проверяем права доступа через API, если эта проверка выполнена
  if (permissionChecked && !hasPermission) {
    // Если серверная проверка не пройдена, используем клиентскую проверку как запасной вариант
    if (requireSuperAdmin && !isSuperAdmin()) {
      return <Navigate to="/" />;
    }
    
    if (!isAdmin()) {
      return <Navigate to="/" />;
    }
  }

  return children;
};

export default AdminRoute;
