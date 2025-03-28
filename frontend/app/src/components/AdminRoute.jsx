import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, isAdmin, isSuperAdmin, checkPermissions } = useAuth();
  const [permissionChecked, setPermissionChecked] = useState(false);
  const [hasPermission, setHasPermission] = useState(false);
  const navigate = useNavigate();

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

  // Проверка прав доступа
  useEffect(() => {
    if (!loading && user) {
      console.log('AdminRoute: проверка прав доступа');
      console.log('isAdmin:', isAdmin);
      
      if (!isAdmin) {
        console.error('Отказано в доступе: пользователь не является администратором');
        navigate('/');
      }
    }
  }, [loading, user, isAdmin, navigate]);

  // Проверка прав администратора выполнена выше
  if (!loading && user && permissionChecked) {
    // Если требуется проверка на суперадмина и она не пройдена, показываем отказ
    if (requireSuperAdmin && !hasPermission) {
      return (
        <div className="container">
          <div className="alert alert-danger">
            <h4>Доступ запрещен</h4>
            <p>Для доступа к этой странице требуются права суперадминистратора.</p>
          </div>
        </div>
      );
    }
    
    // В других случаях - отображаем содержимое
    return children;
  }
  
  // Если что-то загружается или пользователь не авторизован - показываем загрузчик
  return <LoadingSpinner message="Проверка прав доступа..." />;
};

export default AdminRoute;
