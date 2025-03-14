import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, isAdmin, isSuperAdmin } = useAuth();
  
  console.log('AdminRoute - user:', user);
  console.log('AdminRoute - isAdmin:', isAdmin);
  console.log('AdminRoute - isSuperAdmin:', isSuperAdmin);
  
  // Если все еще загружается, показываем загрузчик
  if (loading) {
    return (
      <div className="container d-flex justify-content-center align-items-center" style={{ height: '300px' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </div>
      </div>
    );
  }
  
  // Проверяем, авторизован ли пользователь и имеет ли права администратора
  if (!user) {
    // Пользователь не авторизован, перенаправляем на страницу входа
    return <Navigate to="/login" replace />;
  }
  
  // Безопасная проверка админских прав
  const hasAdminRights = () => {
    try {
      return isAdmin && typeof isAdmin === 'function' && isAdmin();
    } catch (error) {
      console.error('Ошибка при проверке прав администратора:', error);
      return false;
    }
  };
  
  // Безопасная проверка прав суперадмина
  const hasSuperAdminRights = () => {
    try {
      return isSuperAdmin && typeof isSuperAdmin === 'function' && isSuperAdmin();
    } catch (error) {
      console.error('Ошибка при проверке прав суперадминистратора:', error);
      return false;
    }
  };
  
  // Если требуется суперадминистратор, проверяем эту роль
  if (requireSuperAdmin && !hasSuperAdminRights()) {
    return (
      <div className="container">
        <div className="alert alert-danger text-center" role="alert">
          <h4 className="alert-heading">Доступ запрещен</h4>
          <p>Для доступа к этой странице требуются права суперадминистратора.</p>
        </div>
      </div>
    );
  }
  
  // Если пользователь не админ (и не суперадмин), запрещаем доступ
  if (!hasAdminRights()) {
    return (
      <div className="container">
        <div className="alert alert-danger text-center" role="alert">
          <h4 className="alert-heading">Доступ запрещен</h4>
          <p>У вас нет прав для доступа к административной панели.</p>
        </div>
      </div>
    );
  }
  
  // Если все проверки пройдены, показываем содержимое
  return children;
};

export default AdminRoute; 