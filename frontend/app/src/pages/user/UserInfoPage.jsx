// src/pages/user/UserInfoPage.jsx
import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { useOrders } from "../../context/OrderContext";
import { Link } from "react-router-dom";
// Добавим собственные стили
import "../../styles/UserInfoPage.css";

function UserInfoPage() {
  const { user, getUserProfile } = useAuth();
  const { getUserOrderStatistics, loading: orderLoading } = useOrders();
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statistics, setStatistics] = useState({
    total_orders: 0,
    total_revenue: 0,
    average_order_value: 0,
    orders_by_status: {}
  });
  const [error, setError] = useState(null);

  // Загрузка профиля пользователя
  useEffect(() => {
    console.log('UserInfoPage useEffect: user =', user);
    if (!user || !user.id) return;
    const fetchUserProfile = async () => {
      setLoading(true);
      try {
        console.log('Вызов getUserProfile');
        const profileData = await getUserProfile();
        console.log('Ответ getUserProfile:', profileData);
        if (profileData) {
          setUserProfile(profileData);
        }
      } catch (err) {
        console.error("Ошибка при загрузке профиля пользователя:", err);
        setError("Не удалось загрузить данные профиля");
      } finally {
        setLoading(false);
      }
    };
    fetchUserProfile();
  }, [user, getUserProfile]);

  // Загрузка статистики при монтировании компонента
  useEffect(() => {
    const fetchStatistics = async () => {
      try {
        const data = await getUserOrderStatistics();
        if (data) {
          setStatistics(data);
        }
      } catch (err) {
        console.error("Ошибка при загрузке статистики:", err);
        setError("Не удалось загрузить статистику заказов");
      }
    };

    fetchStatistics();
  }, [getUserOrderStatistics]);

  // Отображаем загрузку, пока данные профиля не получены
  if (loading && !userProfile) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </div>
        <p className="mt-2">Загрузка данных профиля...</p>
      </div>
    );
  }

  // Используем данные из профиля, если они доступны, иначе из основного объекта user
  const displayUser = userProfile || user;

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
                      <p className="fs-5 mb-0">{displayUser.first_name}</p>
                    </div>
                  </div>
                  <div className="col-md-6 mb-4">
                    <div className="bg-light p-4 rounded shadow-sm h-100 border">
                      <p className="fw-bold text-primary mb-1">Фамилия</p>
                      <p className="fs-5 mb-0">{displayUser.last_name}</p>
                    </div>
                  </div>
                  <div className="col-12 mb-4">
                    <div className="bg-light p-4 rounded shadow-sm border">
                      <p className="fw-bold text-primary mb-1">Email</p>
                      <p className="fs-5 mb-0">{displayUser.email}</p>
                    </div>
                  </div>
                </div>

                <div className="row mt-4">
                  <div className="col-md-6 mb-3">
                    <Link to="/user/change-password" className="btn btn-primary w-100 py-2 rounded shadow-sm">
                      Изменить пароль
                    </Link>
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
                {orderLoading ? (
                  <div className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Загрузка...</span>
                    </div>
                    <p className="mt-2">Загрузка статистики...</p>
                  </div>
                ) : error ? (
                  <div className="alert alert-danger">{error}</div>
                ) : (
                  <>
                    <div className="row g-4 mb-4">
                      <div className="col-md-4 col-sm-4">
                        <div className="bg-light p-3 rounded shadow-sm h-100 text-center border">
                          <p className="fs-2 fw-bold text-primary mb-0">{statistics.total_orders}</p>
                          <p className="text-secondary">Заказов</p>
                        </div>
                      </div>
                      <div className="col-md-4 col-sm-4">
                        <div className="bg-light p-3 rounded shadow-sm h-100 text-center border">
                          <div className="d-flex flex-column align-items-center">
                            <p className="fs-2 fw-bold text-success mb-0" style={{fontSize: "1.7rem"}}>
                              {statistics.total_revenue}
                            </p>
                            <p className="fs-4 fw-bold text-success mb-0">₽</p>
                          </div>
                          <p className="text-secondary">Покупок</p>
                        </div>
                      </div>
                      <div className="col-md-4 col-sm-4">
                        <div className="bg-light p-3 rounded shadow-sm h-100 text-center border">
                          <div className="d-flex flex-column align-items-center">
                            <p className="fs-2 fw-bold text-custom-purple mb-0">
                              {Math.round(statistics.average_order_value)}
                            </p>
                            <p className="fs-4 fw-bold text-custom-purple mb-0">₽</p>
                          </div>
                          <p className="text-secondary">Средний чек</p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Список последних заказов */}
                    <div className="mt-4">
                      <h3 className="fs-5 mb-3">Последние заказы</h3>
                      
                      <div className="orders-list">
                        {statistics.total_orders === 0 ? (
                          <div className="text-center py-4 bg-light rounded border mb-3">
                            <i className="bi bi-bag text-muted fs-1"></i>
                            <p className="text-muted mt-2">У вас пока нет заказов</p>
                          </div>
                        ) : (
                          <div className="order-status-summary mb-3">
                            {Object.entries(statistics.orders_by_status).map(([status, count]) => (
                              <div key={status} className="d-flex justify-content-between align-items-center mb-2">
                                <span>{status}</span>
                                <span className="badge bg-primary">{count}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        
                        <Link to="/orders" className="btn btn-primary w-100 mt-3">
                          <i className="bi bi-list-ul me-2"></i>
                          Все заказы
                        </Link>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UserInfoPage;
