// src/pages/user/UserInfoPage.jsx
import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { useOrders } from "../../context/OrderContext";
import { Link } from "react-router-dom";
import { Modal, Button, Form } from "react-bootstrap";
import { authAPI } from "../../utils/api";
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
  
  // Состояния для модального окна редактирования профиля
  const [showEditModal, setShowEditModal] = useState(false);
  const [profileForm, setProfileForm] = useState({
    first_name: '',
    last_name: '',
    email: ''
  });
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [profileError, setProfileError] = useState(null);
  
  // Состояния для управления сессиями
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionError, setSessionError] = useState(null);

  // Состояние для анимации удаления сессий
  const [removingSessions, setRemovingSessions] = useState([]);

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
          // Инициализируем форму редактирования профиля
          setProfileForm({
            first_name: profileData.first_name || '',
            last_name: profileData.last_name || '',
            email: profileData.email || ''
          });
        } else {
          // Если профиль не получен, инициализируем форму из данных пользователя или пустыми строками
          setProfileForm({
            first_name: user?.first_name || '',
            last_name: user?.last_name || '',
            email: user?.email || ''
          });
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
  
  // Загрузка сессий при монтировании компонента
  useEffect(() => {
    const fetchSessions = async () => {
      if (!user || !user.id) return;
      
      setSessionsLoading(true);
      setSessionError(null);
      
      try {
        const response = await authAPI.getUserSessions();
        if (response && response.data) {
          setSessions(response.data.sessions || []);
        }
      } catch (err) {
        console.error("Ошибка при загрузке сессий:", err);
        setSessionError("Не удалось загрузить сессии");
      } finally {
        setSessionsLoading(false);
      }
    };
    
    fetchSessions();
  }, [user]);
  
  // Обработчики для модального окна редактирования профиля
  const handleEditModalOpen = () => {
    // Сбрасываем состояние успешного обновления при каждом открытии модального окна
    setUpdateSuccess(false);
    setProfileError(null);
    setShowEditModal(true);
  };
  
  const handleEditModalClose = () => {
    setShowEditModal(false);
    setFormErrors({});
    setProfileError(null);
    
    // Если профиль был успешно обновлен, обновляем страницу через 1 секунду
    // после закрытия модального окна
    if (updateSuccess) {
      setTimeout(() => {
        window.location.reload();
      }, 300);
    }
  };
  
  const handleProfileFormChange = (e) => {
    const { name, value } = e.target;
    
    setProfileForm(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Сбрасываем ошибки при изменении поля
    if (formErrors[name]) {
      setFormErrors(prev => ({ ...prev, [name]: null }));
    }
  };
  
  const validateProfileForm = () => {
    const errors = {};
    
    // Проверяем имя только если оно не пустое
    if (profileForm.first_name.trim() !== '' && profileForm.first_name.trim().length < 2) {
      errors.first_name = 'Имя должно содержать минимум 2 символа';
    }
    
    // Проверяем фамилию только если она не пустая
    if (profileForm.last_name.trim() !== '' && profileForm.last_name.trim().length < 2) {
      errors.last_name = 'Фамилия должна содержать минимум 2 символа';
    }
    
    // Проверяем email только если он не пустой
    if (profileForm.email.trim() !== '') {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profileForm.email)) {
        errors.email = 'Некорректный email';
      }
    }
    
    return errors;
  };
  
  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    
    // Валидация формы
    const errors = validateProfileForm();
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Определяем, какие поля изменились
      const changedFields = {};
      
      // Получаем текущие значения для сравнения (fallback на пустые строки если userProfile отсутствует)
      const currentFirstName = userProfile?.first_name || '';
      const currentLastName = userProfile?.last_name || '';
      const currentEmail = userProfile?.email || '';
      
      // Проверяем имя - если оно не пустое и отличается от текущего
      if (profileForm.first_name.trim() !== '' && profileForm.first_name !== currentFirstName) {
        changedFields.first_name = profileForm.first_name;
      }
      
      // Проверяем фамилию - если она не пустая и отличается от текущей
      if (profileForm.last_name.trim() !== '' && profileForm.last_name !== currentLastName) {
        changedFields.last_name = profileForm.last_name;
      }
      
      // Проверяем email - если он не пустой и отличается от текущего
      if (profileForm.email.trim() !== '' && profileForm.email !== currentEmail) {
        changedFields.email = profileForm.email;
      }
      
      // Обновляем профиль только если есть изменения
      if (Object.keys(changedFields).length > 0) {
        await authAPI.updateProfile(changedFields);
        
        // Обновляем локальное состояние
        setUserProfile(prev => {
          // Если предыдущего значения нет, создаем новый объект
          if (!prev) return { ...changedFields };
          // Иначе обновляем существующий
          return { ...prev, ...changedFields };
        });
        
        // Устанавливаем флаг успешного обновления
        setUpdateSuccess(true);
      } else {
        // Если нет изменений, показываем информационное сообщение
        setProfileError("Нет изменений для сохранения");
      }
      
    } catch (err) {
      console.error('Ошибка при обновлении профиля:', err);
      
      if (err.response?.data?.detail) {
        // Обрабатываем ошибку с сервера
        if (err.response.data.detail.includes('Email уже зарегистрирован')) {
          setFormErrors({ email: 'Email уже зарегистрирован другим пользователем' });
        } else {
          setProfileError(err.response.data.detail);
        }
      } else {
        setProfileError('Ошибка при обновлении профиля');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Обработчик для отзыва одной сессии
  const handleRevokeSession = async (sessionId) => {
    // Добавляем анимацию удаления
    setRemovingSessions(prev => [...prev, sessionId]);

    // Ждем завершения анимации (500мс)
    setTimeout(async () => {
      try {
        await authAPI.revokeSession(sessionId);
        
        // Обновляем список сессий после отзыва
        setSessions(prev => prev.filter(session => session.id !== sessionId));
        
      } catch (err) {
        console.error("Ошибка при отзыве сессии:", err);
        setSessionError("Не удалось отозвать сессию");
      } finally {
        // Удаляем сессию из списка анимируемых
        setRemovingSessions(prev => prev.filter(id => id !== sessionId));
      }
    }, 500);
  };
  
  // Обработчик для отзыва всех сессий
  const handleRevokeAllSessions = async () => {
    try {
      // Получаем JTI текущей сессии
      const currentJti = getCurrentSessionJti();
      
      // Анимируем удаление всех сессий, кроме текущей
      const sessionsToRemove = sessions
        .filter(session => session.jti !== currentJti)
        .map(session => session.id);
      
      setRemovingSessions(sessionsToRemove);
      
      // Ждем завершения анимации
      setTimeout(async () => {
        await authAPI.revokeAllSessions();
        
        // Обновляем список сессий, оставляя только текущую
        setSessions(prev => prev.filter(session => session.jti === currentJti));
        
        // Очищаем список анимируемых сессий
        setRemovingSessions([]);
      }, 500);
      
    } catch (err) {
      console.error("Ошибка при отзыве всех сессий:", err);
      setSessionError("Не удалось отозвать все сессии");
      setRemovingSessions([]);
    }
  };
  
  // Вспомогательная функция для получения JTI текущей сессии
  const getCurrentSessionJti = () => {
    if (sessions.length === 0) return null;
    
    // Получаем информацию о текущем браузере
    const currentUserAgent = navigator.userAgent;
    
    // Сначала пытаемся найти сессию с таким же user-agent
    // и самую свежую по времени
    const matchingSessions = sessions
      .filter(session => {
        // Проверяем, содержит ли user_agent текущий user-agent
        // Иногда они могут немного отличаться из-за различий в обработке на сервере и клиенте
        return session.user_agent && 
               (session.user_agent.includes(currentUserAgent) || 
                currentUserAgent.includes(session.user_agent));
      })
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    // Если нашли подходящие сессии, возвращаем JTI самой свежей
    if (matchingSessions.length > 0) {
      return matchingSessions[0].jti;
    }
    
    // Если не нашли по user-agent, просто берем самую свежую сессию
    const sortedSessions = [...sessions].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
    
    return sortedSessions[0].jti;
  };

  // Отображаем загрузку, пока данные профиля не получены
  if (loading) {
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
  const displayUser = userProfile || user || { first_name: '', last_name: '', email: '' };

  return (
    <div className="container py-5 user-info-page">
      <div className="row g-4">
        {/* Левая колонка - Карточка с личной информацией */}
        <div className="col-lg-8">
          <div className="card shadow" style={{ height: '450px' }}>
            {/* Шапка карточки */}
            <div className="card-header info-header">
              <h2 className="fs-4 fw-bold mb-0">Личная информация</h2>
            </div>
            
            {/* Тело карточки */}
            <div className="card-body bg-white p-4 d-flex flex-column">
              <div className="row flex-grow-1">
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

              <div className="row mt-auto">
                <div className="col-md-6 mb-3">
                  <Link to="/user/change-password" className="btn btn-primary w-100 py-2 rounded shadow-sm">
                    Изменить пароль
                  </Link>
                </div>
                <div className="col-md-6 mb-3">
                  <button
                    onClick={handleEditModalOpen}
                    className="btn btn-success w-100 py-2 rounded shadow-sm"
                  >
                    Редактировать профиль
                  </button>
                </div>
                <div className="col-md-12 mb-3">
                  <Link to="/user/notifications" className="btn btn-light w-100 py-2 rounded shadow-sm">
                    Настройки уведомлений
                  </Link>
                </div>
              </div>
              <div className="mb-3">
                <Link to="/user/favorites" className="btn btn-outline-danger">
                  <i className="bi bi-heart me-1"></i> Мои избранные товары
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* Правая колонка - Карточка со статистикой */}
        <div className="col-lg-4">
          <div className="card shadow" style={{ height: '450px' }}>
            {/* Шапка карточки */}
            <div className="card-header stats-header text-center">
              <h2 className="fs-4 fw-bold mb-0">Статистика</h2>
            </div>
            
            {/* Тело карточки */}
            <div className="card-body bg-white p-4 d-flex flex-column">
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
                <div className="d-flex flex-column flex-grow-1">
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
                  <div className="mt-4 flex-grow-1">
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
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Секция активных сессий */}
      <div className="row mt-4">
        <div className="col-12">
          <div className="card shadow">
            <div className="card-header sessions-header">
              <div className="d-flex justify-content-between align-items-center">
                <h2 className="fs-4 fw-bold mb-0">Активные сессии</h2>
                {sessions.length > 1 && (
                  <button 
                    className="btn btn-outline-danger btn-sm" 
                    onClick={handleRevokeAllSessions}
                    disabled={sessionsLoading}
                  >
                    Отозвать все кроме текущей
                  </button>
                )}
              </div>
            </div>
            <div className="card-body">
              {sessionsLoading ? (
                <div className="text-center py-4">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Загрузка...</span>
                  </div>
                  <p className="mt-2">Загрузка сессий...</p>
                </div>
              ) : sessionError ? (
                <div className="alert alert-danger">{sessionError}</div>
              ) : sessions.length === 0 ? (
                <div className="text-center py-4">
                  <i className="bi bi-shield-lock text-muted fs-1"></i>
                  <p className="text-muted mt-2">Нет активных сессий</p>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover table-striped align-middle mb-0">
                    <thead className="table-light">
                      <tr>
                        <th style={{width: "60%"}}>Устройство</th>
                        <th>Дата входа</th>
                        <th style={{width: "15%"}}>Действия</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.map(session => {
                        // Определяем текущую сессию
                        const isCurrentSession = session.jti === getCurrentSessionJti();
                        
                        // Форматируем дату создания сессии
                        const createdDate = new Date(session.created_at);
                        const formattedDate = createdDate.toLocaleDateString() + ' ' + createdDate.toLocaleTimeString();
                        
                        // Проверяем, удаляется ли сессия (для анимации)
                        const isRemoving = removingSessions.includes(session.id);
                        
                        return (
                          <tr 
                            key={session.id} 
                            className={`${isCurrentSession ? 'table-primary' : ''} ${isRemoving ? 'session-row-removing' : ''}`}
                          >
                            <td>
                              <div className="d-flex align-items-center">
                                <i className="bi bi-laptop fs-4 me-3 text-primary"></i>
                                <div>
                                  <div className="text-truncate" style={{maxWidth: "400px"}}>{session.user_agent || 'Неизвестное устройство'}</div>
                                  {isCurrentSession && (
                                    <span className="badge bg-success mt-1">Текущая сессия</span>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td>{formattedDate}</td>
                            <td className="text-center">
                              {!isCurrentSession && (
                                <button 
                                  className="btn btn-danger btn-sm" 
                                  onClick={() => handleRevokeSession(session.id)}
                                  disabled={isRemoving}
                                >
                                  {isRemoving ? 'Отзыв...' : 'Отозвать'}
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      {/* Модальное окно для редактирования профиля */}
      <Modal show={showEditModal} onHide={handleEditModalClose}>
        <Modal.Header closeButton>
          <Modal.Title>Редактирование профиля</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {updateSuccess ? (
            <div className="alert alert-success">
              Профиль успешно обновлен! Страница будет перезагружена.
            </div>
          ) : (
            <Form onSubmit={handleProfileUpdate}>
              {profileError && (
                <div className="alert alert-danger mb-4">
                  {profileError}
                </div>
              )}
            
              <Form.Group className="mb-3">
                <Form.Label>Имя</Form.Label>
                <Form.Control
                  type="text"
                  name="first_name"
                  value={profileForm.first_name}
                  onChange={handleProfileFormChange}
                  isInvalid={!!formErrors.first_name}
                />
                <Form.Control.Feedback type="invalid">
                  {formErrors.first_name}
                </Form.Control.Feedback>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>Фамилия</Form.Label>
                <Form.Control
                  type="text"
                  name="last_name"
                  value={profileForm.last_name}
                  onChange={handleProfileFormChange}
                  isInvalid={!!formErrors.last_name}
                />
                <Form.Control.Feedback type="invalid">
                  {formErrors.last_name}
                </Form.Control.Feedback>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>Email</Form.Label>
                <Form.Control
                  type="email"
                  name="email"
                  value={profileForm.email}
                  onChange={handleProfileFormChange}
                  isInvalid={!!formErrors.email}
                />
                <Form.Control.Feedback type="invalid">
                  {formErrors.email}
                </Form.Control.Feedback>
                <Form.Text className="text-muted">
                  При смене email, новый email не должен быть зарегистрирован в системе.
                </Form.Text>
              </Form.Group>
            </Form>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleEditModalClose}>
            {updateSuccess ? 'Закрыть' : 'Отмена'}
          </Button>
          {!updateSuccess && (
            <Button 
              variant="primary" 
              onClick={handleProfileUpdate}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Обновление...' : 'Сохранить изменения'}
            </Button>
          )}
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default UserInfoPage;
