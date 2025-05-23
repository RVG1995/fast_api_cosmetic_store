import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const AdminDashboard = () => {
  const { user, isAdmin, isSuperAdmin } = useAuth();

  return (
    <div className="container py-5">
      <div className="row">
        <div className="col-12 mb-4">
          <div className="card shadow-sm">
            <div className="card-header bg-primary text-white">
              <h2 className="fs-4 mb-0">Панель администратора</h2>
            </div>
            <div className="card-body">
              <p className="lead">
                Добро пожаловать, {user.first_name} {user.last_name}!
              </p>
              <p>
                У вас есть доступ к управлению системой. Выберите раздел из меню ниже.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="row">
        <div className="col-md-4 mb-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body text-center">
              <i className="bi bi-people fs-1 text-primary mb-3"></i>
              <h3 className="fs-5">Управление пользователями</h3>
              <p className="mb-4">Просмотр, активация и управление пользователями</p>
              <Link to="/admin/users" className="btn btn-primary">
                Перейти
              </Link>
            </div>
          </div>
        </div>

        <div className="col-md-4 mb-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body text-center">
              <i className="bi bi-box-seam fs-1 text-success mb-3"></i>
              <h3 className="fs-5">Управление товарами</h3>
              <p className="mb-4">Добавление, редактирование и удаление товаров</p>
              <Link to="/admin/products" className="btn btn-success">
                Перейти
              </Link>
            </div>
          </div>
        </div>

        <div className="col-md-4 mb-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body text-center">
              <i className="bi bi-gear fs-1 text-warning mb-3"></i>
              <h3 className="fs-5">Настройки системы</h3>
              <p className="mb-4">Настройка параметров работы магазина</p>
              <Link to="/admin/settings" className="btn btn-warning">
                Перейти
              </Link>
            </div>
          </div>
        </div>

        <div className="col-md-4 mb-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body text-center">
              <i className="bi bi-diagram-3 fs-1 text-info mb-3"></i>
              <h3 className="fs-5">Воронка Boxberry</h3>
              <p className="mb-4">Настройка соответствия статусов Boxberry и заказов</p>
              <Link to="/admin/boxberry-funnel" className="btn btn-info">
                Перейти
              </Link>
            </div>
          </div>
        </div>

        {isSuperAdmin() && (
          <div className="col-md-4 mb-4">
            <div className="card h-100 shadow-sm border-danger">
              <div className="card-body text-center">
                <i className="bi bi-shield-lock fs-1 text-danger mb-3"></i>
                <h3 className="fs-5">Управление правами</h3>
                <p className="mb-4">Назначение администраторов и управление правами доступа</p>
                <Link to="/admin/permissions" className="btn btn-danger">
                  Перейти
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
