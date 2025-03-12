// src/components/layout/Layout.jsx

import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import React, { useEffect } from 'react';
import "../../styles/Layout.css"; // Обновленный путь к стилям

const Layout = () => {
  const { user, loading, logout, isAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

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
    <div className="d-flex flex-column min-vh-100">
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
              <ul className="navbar-nav ms-auto">
                {/* Удаляем ссылку на продукты, так как они будут на главной */}
                
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
                    {isAdmin && isAdmin() && (
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
    </div>
  );
};

export default Layout;
