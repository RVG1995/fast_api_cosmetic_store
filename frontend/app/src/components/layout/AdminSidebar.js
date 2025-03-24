import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Nav } from 'react-bootstrap';
import { 
  MdDashboard, 
  MdPerson, 
  MdCategory, 
  MdInventory, 
  MdBranding, 
  MdPublic, 
  MdShoppingCart,
  MdSecurity,
  MdReceipt,
  MdAssignment,
  MdPayment
} from 'react-icons/md';
import { useAuth } from '../../context/AuthContext';

// Стилизованный компонент для панели администратора
const AdminSidebar = () => {
  const location = useLocation();
  const { user } = useAuth();
  const isSuperAdmin = user?.role === 'super_admin';

  // Проверка активного пути
  const isActive = (path) => {
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  return (
    <div className="admin-sidebar bg-dark text-white p-3">
      <h5 className="sidebar-heading d-flex justify-content-between align-items-center px-3 mb-4">
        <span>Панель администратора</span>
      </h5>
      <Nav className="flex-column">
        <Nav.Item>
          <Link 
            to="/admin" 
            className={`nav-link ${isActive('/admin') && !isActive('/admin/users') && !isActive('/admin/products') ? 'active' : ''}`}
          >
            <MdDashboard className="me-2" /> Дашборд
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/users" 
            className={`nav-link ${isActive('/admin/users') ? 'active' : ''}`}
          >
            <MdPerson className="me-2" /> Пользователи
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/products" 
            className={`nav-link ${isActive('/admin/products') ? 'active' : ''}`}
          >
            <MdInventory className="me-2" /> Товары
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/categories" 
            className={`nav-link ${isActive('/admin/categories') ? 'active' : ''}`}
          >
            <MdCategory className="me-2" /> Категории
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/subcategories" 
            className={`nav-link ${isActive('/admin/subcategories') ? 'active' : ''}`}
          >
            <MdCategory className="me-2" /> Подкатегории
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/brands" 
            className={`nav-link ${isActive('/admin/brands') ? 'active' : ''}`}
          >
            <MdBranding className="me-2" /> Бренды
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/countries" 
            className={`nav-link ${isActive('/admin/countries') ? 'active' : ''}`}
          >
            <MdPublic className="me-2" /> Страны
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/carts" 
            className={`nav-link ${isActive('/admin/carts') ? 'active' : ''}`}
          >
            <MdShoppingCart className="me-2" /> Корзины
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/orders" 
            className={`nav-link ${isActive('/admin/orders') ? 'active' : ''}`}
          >
            <MdReceipt className="me-2" /> Заказы
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/order-statuses" 
            className={`nav-link ${isActive('/admin/order-statuses') ? 'active' : ''}`}
          >
            <MdAssignment className="me-2" /> Статусы заказов
          </Link>
        </Nav.Item>
        <Nav.Item>
          <Link 
            to="/admin/payment-statuses" 
            className={`nav-link ${isActive('/admin/payment-statuses') ? 'active' : ''}`}
          >
            <MdPayment className="me-2" /> Статусы оплаты
          </Link>
        </Nav.Item>
        {isSuperAdmin && (
          <Nav.Item>
            <Link 
              to="/admin/permissions" 
              className={`nav-link ${isActive('/admin/permissions') ? 'active' : ''}`}
            >
              <MdSecurity className="me-2" /> Права доступа
            </Link>
          </Nav.Item>
        )}
      </Nav>
    </div>
  );
};

export default AdminSidebar; 