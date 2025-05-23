import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import { useState, useEffect } from 'react';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, isAdmin, isSuperAdmin, checkPermissions } = useAuth();
  const [permissionChecked, setPermissionChecked] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const location = useLocation();

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

  if (loading) return <LoadingSpinner message="Проверка прав доступа..." />;
  if (!user) return <Navigate to="/login" />;
  if (!isAdmin) {
    return (
      <>
        <Navigate to="/" />
        <div style={{display: 'none'}} aria-hidden="true" />
      </>
    );
  }
  if (requireSuperAdmin && permissionChecked && !hasPermission) {
    return (
      <>
        <Navigate to="/" />
        <div style={{display: 'none'}} aria-hidden="true" />
      </>
    );
  }
  return children;
};

export default AdminRoute;
