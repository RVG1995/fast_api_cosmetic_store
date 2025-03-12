import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import '../../styles/AdminDashboard.css';

const AdminDashboard = () => {
  const { user, isSuperAdmin } = useAuth();

  return (
    <div className="admin-dashboard">
      <h1 className="mb-4">Административная панель</h1>
      
      <div className="alert alert-info">
        <h5 className="alert-heading">Добро пожаловать, {user?.first_name}!</h5>
        <p>Вы авторизованы как {isSuperAdmin() ? 'суперадминистратор' : 'администратор'}.</p>
      </div>
      
      <div className="row mb-4">
        {/* Управление пользователями */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-people-fill admin-card-icon"></i>
              <h3>Пользователи</h3>
            </div>
            <div className="admin-card-body">
              <p>Управление пользователями системы. Активация учетных записей, назначение ролей и редактирование профилей.</p>
              <Link to="/admin/users" className="btn btn-primary">Управление пользователями</Link>
            </div>
          </div>
        </div>
        
        {/* Управление товарами */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-box-seam admin-card-icon"></i>
              <h3>Товары</h3>
            </div>
            <div className="admin-card-body">
              <p>Управление каталогом товаров. Добавление, редактирование и удаление товаров в системе.</p>
              <Link to="/admin/products" className="btn btn-primary">Управление товарами</Link>
            </div>
          </div>
        </div>
        
        {/* Блок для суперадминов */}
        {isSuperAdmin() && (
          <div className="col-md-4 mb-4">
            <div className="admin-card">
              <div className="admin-card-header">
                <i className="bi bi-shield-lock-fill admin-card-icon"></i>
                <h3>Права доступа</h3>
              </div>
              <div className="admin-card-body">
                <p>Управление правами доступа к системе. Добавление и редактирование ролей в системе.</p>
                <Link to="/admin/permissions" className="btn btn-primary">Настройка прав</Link>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <div className="row">
        {/* Статистика */}
        <div className="col-12">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-graph-up admin-card-icon"></i>
              <h3>Статистика системы</h3>
            </div>
            <div className="admin-card-body">
              <div className="row stats">
                <div className="col-md-3 stat-item">
                  <div className="stat-value">125</div>
                  <div className="stat-label">Пользователей</div>
                </div>
                <div className="col-md-3 stat-item">
                  <div className="stat-value">48</div>
                  <div className="stat-label">Товаров</div>
                </div>
                <div className="col-md-3 stat-item">
                  <div className="stat-value">12</div>
                  <div className="stat-label">Категорий</div>
                </div>
                <div className="col-md-3 stat-item">
                  <div className="stat-value">230</div>
                  <div className="stat-label">Запросов сегодня</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard; 