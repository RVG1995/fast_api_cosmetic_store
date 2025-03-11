// src/pages/user/UserInfoPage.jsx
import React from "react";
import { useAuth } from "../../context/AuthContext";
import { Link } from "react-router-dom";
// Добавим собственные стили
import "../../styles/UserInfoPage.css";

function UserInfoPage() {
  const { user } = useAuth();

  return (
    <div className="py-5 bg-light">
      <div className="container">
        <div className="row">
          {/* Левая колонка - Карточка с личной информацией */}
          <div className="col-lg-8 mb-4">
            <div className="card shadow h-100">
              {/* Шапка карточки */}
              <div className="card-header info-header">
                <h2 className="fs-4 fw-bold mb-0">Личная информация</h2>
              </div>
              
              {/* Тело карточки */}
              <div className="card-body bg-white p-4">
                <div className="row">
                  <div className="col-md-6 mb-4">
                    <div className="bg-light p-4 rounded shadow-sm h-100 border">
                      <p className="fw-bold text-primary mb-1">Имя</p>
                      <p className="fs-5 mb-0">{user.first_name}</p>
                    </div>
                  </div>
                  <div className="col-md-6 mb-4">
                    <div className="bg-light p-4 rounded shadow-sm h-100 border">
                      <p className="fw-bold text-primary mb-1">Фамилия</p>
                      <p className="fs-5 mb-0">{user.last_name}</p>
                    </div>
                  </div>
                  <div className="col-12 mb-4">
                    <div className="bg-light p-4 rounded shadow-sm border">
                      <p className="fw-bold text-primary mb-1">Email</p>
                      <p className="fs-5 mb-0">{user.email}</p>
                    </div>
                  </div>
                </div>

                <div className="row mt-4">
                  <div className="col-md-6 mb-3">
                    <button className="btn btn-primary w-100 py-2 rounded shadow-sm">
                      Изменить пароль
                    </button>
                  </div>
                  <div className="col-md-6 mb-3">
                    <button className="btn btn-light w-100 py-2 rounded shadow-sm">
                      Настройки уведомлений
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Правая колонка - Карточка со статистикой */}
          <div className="col-lg-4">
            <div className="card shadow h-100">
              {/* Шапка карточки */}
              <div className="card-header stats-header text-center">
                <h2 className="fs-4 fw-bold mb-0">Статистика</h2>
              </div>
              
              {/* Тело карточки */}
              <div className="card-body bg-white p-4">
                <div className="row g-4 mb-4">
                  <div className="col-md-4 col-sm-4">
                    <div className="bg-light p-3 rounded shadow-sm h-100 text-center border">
                      <p className="fs-2 fw-bold text-primary mb-0">0</p>
                      <p className="text-secondary">Заказов</p>
                    </div>
                  </div>
                  <div className="col-md-4 col-sm-4">
                    <div className="bg-light p-3 rounded shadow-sm h-100 text-center border">
                      <p className="fs-2 fw-bold text-success mb-0">0₽</p>
                      <p className="text-secondary">Покупок</p>
                    </div>
                  </div>
                  <div className="col-md-4 col-sm-4">
                    <div className="bg-light p-3 rounded shadow-sm h-100 text-center border">
                      <p className="fs-2 fw-bold text-custom-purple mb-0">0</p>
                      <p className="text-secondary">Отзывов</p>
                    </div>
                  </div>
                </div>
                
                {/* Список последних заказов */}
                <div className="mt-4">
                  <h3 className="fs-5 mb-3">Последние заказы</h3>
                  
                  <div className="orders-list">
                    {/* Пустой список заказов */}
                    <div className="text-center py-4 bg-light rounded border mb-3">
                      <i className="bi bi-bag text-muted fs-1"></i>
                      <p className="text-muted mt-2">У вас пока нет заказов</p>
                    </div>
                    
                    {/* Отображение будет, когда появятся заказы
                    <div className="order-item p-3 bg-light rounded border mb-2">
                      <div className="d-flex justify-content-between align-items-center">
                        <div>
                          <p className="mb-0 fw-bold">Заказ #12345</p>
                          <small className="text-muted">2023-05-15</small>
                        </div>
                        <span className="badge bg-success">Доставлен</span>
                      </div>
                      <div className="mt-2">
                        <small className="text-primary">3 товара на сумму 5,600₽</small>
                      </div>
                    </div>
                    */}
                    
                    <Link to="/orders" className="btn btn-primary w-100 mt-3">
                      <i className="bi bi-list-ul me-2"></i>
                      Все заказы
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UserInfoPage;
