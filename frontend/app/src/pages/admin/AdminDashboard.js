import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { adminAPI } from '../../utils/api';
import { formatPrice } from '../../utils/helpers';
import '../../styles/AdminDashboard.css';

const AdminDashboard = () => {
  const { user, isSuperAdmin } = useAuth();
  const [stats, setStats] = useState({
    usersCount: 0,
    productsCount: 0,
    ordersCount: 0,
    totalOrdersRevenue: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Загрузка статистики при монтировании компонента
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const statsData = await adminAPI.getDashboardStats();
        setStats(statsData);
        setError(null);
      } catch (err) {
        console.error('Ошибка при загрузке статистики:', err);
        setError('Не удалось загрузить статистику. Пожалуйста, попробуйте позже.');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="admin-dashboard">
      <h1 className="mb-4">Административная панель</h1>
      
      <div className="alert alert-info">
        <h5 className="alert-heading">Добро пожаловать, {user?.first_name}!</h5>
        <p>Вы авторизованы как {isSuperAdmin() ? 'суперадминистратор' : 'администратор'}.</p>
      </div>
      
      {/* Блок для статистики системы - переместили в начало */}
      <div className="row mb-4">
        <div className="col-12">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-graph-up admin-card-icon"></i>
              <h3>Статистика системы</h3>
            </div>
            <div className="admin-card-body">
              {loading ? (
                <div className="text-center py-3">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Загрузка...</span>
                  </div>
                  <p className="mt-2">Загрузка статистики...</p>
                </div>
              ) : error ? (
                <div className="alert alert-danger">{error}</div>
              ) : (
                <div className="row stats">
                  <div className="col-md-3 stat-item">
                    <div className="stat-value">{stats.usersCount}</div>
                    <div className="stat-label">Пользователей</div>
                  </div>
                  <div className="col-md-3 stat-item">
                    <div className="stat-value">{stats.productsCount}</div>
                    <div className="stat-label">Товаров</div>
                  </div>
                  <div className="col-md-3 stat-item">
                    <div className="stat-value">{stats.ordersCount}</div>
                    <div className="stat-label">Заказов</div>
                  </div>
                  <div className="col-md-3 stat-item">
                    <div className="stat-value">{formatPrice(stats.totalOrdersRevenue)}</div>
                    <div className="stat-label">Сумма заказов</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
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
        
        {/* Управление категориями */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-folder-fill admin-card-icon"></i>
              <h3>Категории</h3>
            </div>
            <div className="admin-card-body">
              <p>Управление категориями товаров. Добавление, редактирование и удаление категорий.</p>
              <Link to="/admin/categories" className="btn btn-primary">Управление категориями</Link>
            </div>
          </div>
        </div>
        
        {/* Управление подкатегориями */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-diagram-3-fill admin-card-icon"></i>
              <h3>Подкатегории</h3>
            </div>
            <div className="admin-card-body">
              <p>Управление подкатегориями товаров. Привязка к категориям, редактирование и удаление.</p>
              <Link to="/admin/subcategories" className="btn btn-primary">Управление подкатегориями</Link>
            </div>
          </div>
        </div>
        
        {/* Управление брендами */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-tag-fill admin-card-icon"></i>
              <h3>Бренды</h3>
            </div>
            <div className="admin-card-body">
              <p>Управление брендами товаров. Добавление новых брендов, редактирование и удаление.</p>
              <Link to="/admin/brands" className="btn btn-primary">Управление брендами</Link>
            </div>
          </div>
        </div>
        
        {/* Управление странами */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-globe admin-card-icon"></i>
              <h3>Страны</h3>
            </div>
            <div className="admin-card-body">
              <p>Управление странами-производителями. Добавление, редактирование и удаление стран.</p>
              <Link to="/admin/countries" className="btn btn-primary">Управление странами</Link>
            </div>
          </div>
        </div>
        
        {/* Управление корзинами */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-cart-fill admin-card-icon"></i>
              <h3>Корзины</h3>
            </div>
            <div className="admin-card-body">
              <p>Просмотр и управление корзинами пользователей. Анализ заброшенных корзин.</p>
              <Link to="/admin/carts" className="btn btn-primary">Управление корзинами</Link>
            </div>
          </div>
        </div>
        
        {/* Управление заказами */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-bag-check-fill admin-card-icon"></i>
              <h3>Заказы</h3>
            </div>
            <div className="admin-card-body">
              <p>Просмотр и управление заказами пользователей. Изменение статусов заказов.</p>
              <Link to="/admin/orders" className="btn btn-primary">Управление заказами</Link>
            </div>
          </div>
        </div>
        
        {/* Управление статусами заказов */}
        <div className="col-md-4 mb-4">
          <div className="admin-card">
            <div className="admin-card-header">
              <i className="bi bi-list-check admin-card-icon"></i>
              <h3>Статусы заказов</h3>
            </div>
            <div className="admin-card-body">
              <p>Управление статусами заказов. Создание и редактирование статусов для отслеживания заказов.</p>
              <Link to="/admin/order-statuses" className="btn btn-primary">Управление статусами заказов</Link>
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
    </div>
  );
};

export default AdminDashboard; 