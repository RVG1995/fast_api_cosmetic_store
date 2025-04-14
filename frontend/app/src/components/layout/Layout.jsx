// src/components/layout/Layout.jsx

import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useCategories } from "../../context/CategoryContext";
import React, { useEffect, useState } from 'react';
import ProductSearch from "../ProductSearch";
import CartIcon from "../cart/CartIcon";
import { CartProvider } from "../../context/CartContext";
import ScrollToTopButton from "./ScrollToTopButton";
import OfflineIndicator from "../common/OfflineIndicator";
import "../../styles/Layout.css"; // Обновленный путь к стилям

const Layout = () => {
  const { user, loading, logout, isAdmin } = useAuth();
  const { categories, loading: isLoadingCategories } = useCategories();
  const location = useLocation();
  const navigate = useNavigate();

  const [alert, setAlert] = useState({ show: false, message: '', type: '' });
  
  // Обработчик для показа уведомления через Alert
  useEffect(() => {
    const handleAlert = (event) => {
      const { message, type } = event.detail;
      console.log('Отображаем Bootstrap Alert:', message, type);
      setAlert({ show: true, message, type });
      
      // Автоматически скрываем через 3 секунды
      setTimeout(() => {
        setAlert({ show: false, message: '', type: '' });
      }, 3000);
    };
    
    window.addEventListener('show:toast', handleAlert);
    
    return () => {
      window.removeEventListener('show:toast', handleAlert);
    };
  }, []);

  useEffect(() => {
    if (!loading) {
      // Если пользователь не авторизован и пытается получить доступ к /user
      if (!user && location.pathname === "/user") {
        navigate("/login");
      }
      
      // Если пользователь авторизован и пытается получить доступ к страницам auth
      if (user && ["/register", "/login"].includes(location.pathname)) {
        navigate("/user");
      }
    }
  }, [loading, user, location.pathname, navigate]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <CartProvider>
      <div className="d-flex flex-column min-vh-100">
        {/* Индикатор отсутствия подключения */}
        <OfflineIndicator />
        
        {/* Bootstrap Alert для уведомлений - улучшенный стиль */}
        {alert.show && (
          <div 
            className={`alert alert-${alert.type} alert-dismissible fade show`} 
            role="alert"
            style={{ 
              position: 'fixed', 
              top: '15px', 
              right: '15px', 
              zIndex: 9999,
              maxWidth: '350px',
              boxShadow: '0 4px 8px rgba(0,0,0,0.1)',
              borderLeft: alert.type === 'danger' ? '4px solid #dc3545' : 
                        alert.type === 'success' ? '4px solid #28a745' : 
                        alert.type === 'warning' ? '4px solid #ffc107' : 
                        '4px solid #17a2b8',
              padding: '12px 15px'
            }}
          >
            {alert.type === 'danger' && <i className="bi bi-exclamation-circle-fill me-2 text-danger"></i>}
            {alert.type === 'success' && <i className="bi bi-check-circle-fill me-2 text-success"></i>}
            {alert.type === 'warning' && <i className="bi bi-exclamation-triangle-fill me-2 text-warning"></i>}
            {alert.type === 'info' && <i className="bi bi-info-circle-fill me-2 text-info"></i>}
            
            <span className="fw-semibold">{alert.message}</span>
            <button 
              type="button" 
              className="btn-close" 
              onClick={() => setAlert({ show: false, message: '', type: '' })}
              aria-label="Close"
            ></button>
          </div>
        )}
        
        <header>
          <nav className="navbar navbar-expand-lg navbar-dark bg-primary shadow-sm">
            <div className="container">
              <Link className="navbar-brand fw-bold" to="/">
                <i className="bi bi-shield-lock me-2"></i>
                Secure Auth
              </Link>
              
              <button 
                className="navbar-toggler" 
                type="button" 
                data-bs-toggle="collapse" 
                data-bs-target="#navbarNav" 
                aria-controls="navbarNav" 
                aria-expanded="false" 
                aria-label="Toggle navigation"
              >
                <span className="navbar-toggler-icon"></span>
              </button>
              
              <div className="collapse navbar-collapse" id="navbarNav">
                <ul className="navbar-nav me-auto">
                  {/* Выпадающее меню категорий */}
                  <li className="nav-item dropdown">
                    <button 
                      className="nav-link dropdown-toggle" 
                      id="categoriesDropdown" 
                      data-bs-toggle="dropdown" 
                      aria-expanded="false"
                    >
                      <i className="bi bi-grid me-1"></i>
                      Категории
                    </button>
                    <ul className="dropdown-menu" aria-labelledby="categoriesDropdown">
                      <li>
                        <Link className="dropdown-item" to="/products">
                          Все товары
                        </Link>
                      </li>
                      <li><hr className="dropdown-divider" /></li>
                      {isLoadingCategories ? (
                        <li>
                          <span className="dropdown-item">Загрузка...</span>
                        </li>
                      ) : categories.length > 0 ? (
                        categories.map(category => (
                          <li key={category.id}>
                            <Link 
                              className="dropdown-item" 
                              to={`/products?category_id=${category.id}`}
                            >
                              {category.name}
                            </Link>
                          </li>
                        ))
                      ) : (
                        <li>
                          <span className="dropdown-item">Нет доступных категорий</span>
                        </li>
                      )}
                    </ul>
                  </li>
                </ul>
                
                {/* Компонент поиска для десктоп */}
                <div className="navbar-search-container d-none d-md-block mx-3">
                  <ProductSearch />
                </div>
                
                <ul className="navbar-nav ms-auto">
                  {/* Компонент корзины */}
                  <li className="nav-item me-2">
                    <CartIcon />
                  </li>
                  
                  {/* Ссылка на отзывы */}
                  <li className="nav-item">
                    <Link 
                      to="/reviews" 
                      className={`nav-link ${location.pathname === "/reviews" ? "active fw-bold" : ""}`}
                    >
                      <i className="bi bi-star me-1"></i>
                      Отзывы
                    </Link>
                  </li>
                  
                  {/* Добавляем мобильную версию поиска */}
                  <li className="nav-item d-md-none mb-2">
                    <div className="navbar-search-container">
                      <ProductSearch />
                    </div>
                  </li>
                  
                  {/* Добавляем мобильную версию корзины */}
                  <li className="nav-item d-md-none mb-2">
                    <Link 
                      to="/cart" 
                      className="btn btn-outline-light btn-sm"
                    >
                      <i className="bi bi-cart3 me-1"></i>
                      Корзина
                    </Link>
                  </li>
                  
                  {user ? (
                    <>
                      <li className="nav-item">
                        <Link 
                          to="/user" 
                          className={`nav-link ${location.pathname === "/user" ? "active fw-bold" : ""}`}
                        >
                          <i className="bi bi-person-circle me-1"></i>
                          Профиль
                        </Link>
                      </li>
                      
                      {/* Добавляем ссылку на админ-панель для администраторов */}
                      {isAdmin && (
                        <li className="nav-item">
                          <Link 
                            to="/admin" 
                            className={`nav-link ${location.pathname.startsWith("/admin") ? "active fw-bold" : ""}`}
                          >
                            <i className="bi bi-gear-fill me-1"></i>
                            Управление
                          </Link>
                        </li>
                      )}
                      
                      <li className="nav-item">
                        <button 
                          onClick={handleLogout} 
                          className="nav-link btn btn-danger text-white ms-2 px-3"
                        >
                          <i className="bi bi-box-arrow-right me-1"></i>
                          Выйти
                        </button>
                      </li>
                    </>
                  ) : (
                    <>
                      <li className="nav-item">
                        <Link 
                          to="/register" 
                          className={`nav-link ${location.pathname === "/register" ? "active fw-bold" : ""}`}
                        >
                          <i className="bi bi-person-plus me-1"></i>
                          Регистрация
                        </Link>
                      </li>
                      <li className="nav-item">
                        <Link 
                          to="/login" 
                          className={`nav-link ${location.pathname === "/login" ? "active fw-bold" : ""}`}
                        >
                          <i className="bi bi-box-arrow-in-right me-1"></i>
                          Вход
                        </Link>
                      </li>
                    </>
                  )}
                </ul>
              </div>
            </div>
          </nav>
          
          {/* Элемент только для главной страницы */}
          {location.pathname === "/" && (
            <div className="welcome-banner bg-primary text-white py-4">
              <div className="container text-center">
                <h2 className="fs-1 fw-bold">Добро пожаловать в наш магазин!</h2>
                <p className="fs-5 mt-2">Специальные предложения для новых пользователей</p>
              </div>
            </div>
          )}
        </header>
        
        <main className="flex-grow-1 py-4 bg-light">
          <div className="container">
            {/* Баннер только на главной */}
            {location.pathname === "/" && (
              <div className="alert alert-warning p-3 shadow-sm mb-4">
                <p className="text-center fs-5 fw-bold mb-0">
                  <i className="bi bi-fire me-2"></i>
                  Горячее предложение! Скидка 20% на первый заказ
                </p>
              </div>
            )}
            
            <Outlet />
          </div>
        </main>

        <footer className="py-4 bg-dark text-white text-center">
          <div className="container">
            <p className="mb-0">© 2025 Secure Auth. Все права защищены.</p>
          </div>
        </footer>
        
        {/* Кнопка прокрутки вверх */}
        <ScrollToTopButton />
      </div>
    </CartProvider>
  );
};

export default Layout;
