import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, isAdmin, isSuperAdmin } = useAuth();
  
  console.log('AdminRoute - user:', user);
  console.log('AdminRoute - isAdmin:', isAdmin);
  console.log('AdminRoute - isSuperAdmin:', isSuperAdmin);
  
  // Проверка прав администратора
  const checkAdmin = () => {
    console.log('AdminRoute - isAdmin:', isAdmin);
    console.log('AdminRoute - user:', user);
    
    // Ожидаем загрузку данных пользователя
    if (loading) {
      return false;
    }
    
    // Проверяем авторизацию и админские права
    return !!user && isAdmin;
  };
  
  // Ожидаем загрузку данных аутентификации
  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '100vh' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </div>
      </div>
    );
  }

  // Проверка аутентификации
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  // Проверка админских прав
  if (!checkAdmin()) {
    console.error('Access Denied: User does not have admin rights');
    // Перенаправляем на главную страницу при отсутствии прав
    return <Navigate to="/" replace />;
  }
  
  // Если все проверки пройдены, показываем содержимое
  return children;
};

export default AdminRoute; 