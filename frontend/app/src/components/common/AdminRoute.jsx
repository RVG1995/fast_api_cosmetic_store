import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, checkPermission } = useAuth();
  const [hasPermission, setHasPermission] = useState(false);
  const [permissionLoading, setPermissionLoading] = useState(true);

  useEffect(() => {
    if (!user || loading || !checkPermission) return;

    let cancelled = false;
    setPermissionLoading(true);

    const checkAccess = async () => {
      try {
        const permission = requireSuperAdmin ? 'super_admin_access' : 'admin_access';
        const hasAccess = await checkPermission(permission);
        if (!cancelled) setHasPermission(hasAccess);
      } catch {
        if (!cancelled) setHasPermission(false);
      } finally {
        if (!cancelled) setPermissionLoading(false);
      }
    };

    checkAccess();

    return () => { cancelled = true; };
  }, [user, user?.id, requireSuperAdmin, checkPermission, loading]);

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

AdminRoute.propTypes = {
  children: PropTypes.node.isRequired,
  requireSuperAdmin: PropTypes.bool,
};
