import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Table, Badge, Button, Form, Alert, Spinner, Modal } from 'react-bootstrap';
import { useOrders } from '../../context/OrderContext';
import { useAuth } from '../../context/AuthContext';
import { formatDateTime } from '../../utils/dateUtils';
import { formatPrice } from '../../utils/helpers';
import OrderStatusBadge from '../../components/OrderStatusBadge';
import axios from 'axios';
import { API_URLS } from '../../utils/constants';

const AdminOrderDetail = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { 
    getAdminOrderById, 
    getOrderStatuses, 
    updateOrderStatus,
    updateOrderPaymentStatus,
    loading: contextLoading, 
    error: contextError 
  } = useOrders();
  const { user } = useAuth();
  
  const [order, setOrder] = useState(null);
  const [statuses, setStatuses] = useState([]);
  const [selectedStatus, setSelectedStatus] = useState('');
  const [statusNote, setStatusNote] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [paymentUpdateSuccess, setPaymentUpdateSuccess] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Загрузка деталей заказа и статусов
  useEffect(() => {
    const loadData = async () => {
      try {
        console.log('=== ДИАГНОСТИКА ЗАГРУЗКИ ЗАКАЗА АДМИНИСТРАТОРОМ ===');
        console.log('ID заказа:', orderId);
        console.log('Пользователь:', user);
        
        // Проверяем авторизацию пользователя
        if (!user) {
          console.error('Пользователь не авторизован');
          setLoadError('Для доступа к информации о заказе необходима авторизация');
          return;
        }
        
        // Проверка прав администратора
        const isAdmin = user?.is_admin || user?.is_super_admin;
        
        if (!isAdmin) {
          console.error('Пользователь не является администратором');
          setLoadError('Доступ запрещен. Для просмотра этой страницы необходимы права администратора');
          return;
        }
        
        // Напрямую вызываем axios вместо getAdminOrderById для диагностики
        console.log('===== НАЧАЛО ЗАПРОСА ЗАКАЗА АДМИНИСТРАТОРОМ =====');
        
        const config = {
          withCredentials: true,
          headers: {
            'Content-Type': 'application/json'
          }
        };
        
        const orderUrl = `${API_URLS.ORDER_SERVICE}/admin/orders/${orderId}`;
        console.log('URL запроса заказа:', orderUrl);
        console.log('Конфигурация:', JSON.stringify(config));
        
        // Выполняем запрос заказа
        const orderResponse = await axios.get(orderUrl, config);
        console.log('Ответ от сервера (заказ):', orderResponse.status);
        console.log('Данные заказа:', orderResponse.data);
        
        // Устанавливаем данные заказа
        setOrder(orderResponse.data);
        
        // Загружаем статусы заказов
        const statusesUrl = `${API_URLS.ORDER_SERVICE}/order-statuses`;
        console.log('URL запроса статусов:', statusesUrl);
        
        const statusesResponse = await axios.get(statusesUrl, { withCredentials: true });
        console.log('Ответ от сервера (статусы):', statusesResponse.status);
        console.log('Данные статусов:', statusesResponse.data);
        
        // Устанавливаем статусы
        setStatuses(statusesResponse.data || []);
        
        // Если у заказа есть статус, устанавливаем его как выбранный
        if (orderResponse.data && orderResponse.data.status && orderResponse.data.status.id) {
          setSelectedStatus(orderResponse.data.status.id.toString());
        }
      } catch (err) {
        console.error('===== ОШИБКА ЗАПРОСА ЗАКАЗА АДМИНИСТРАТОРОМ =====');
        console.error('Имя ошибки:', err.name);
        console.error('Сообщение ошибки:', err.message);
        
        if (err.response) {
          console.error('Статус ошибки:', err.response.status);
          console.error('Данные ошибки:', err.response.data);
          
          if (err.response.status === 401) {
            setLoadError('Для доступа к заказу необходима авторизация');
          } else if (err.response.status === 403) {
            setLoadError('У вас нет прав для просмотра этого заказа');
          } else if (err.response.status === 404) {
            setLoadError('Заказ не найден');
          } else {
            setLoadError(`Ошибка сервера: ${err.response?.data?.detail || 'Неизвестная ошибка'}`);
          }
        } else if (err.request) {
          console.error('Запрос был отправлен, но ответ не получен:', err.request);
          setLoadError('Не удалось получить ответ от сервера. Проверьте подключение к интернету');
        } else {
          setLoadError(`Ошибка при загрузке заказа: ${err.message}`);
        }
        setLoading(false);
      }
    };

    loadData();
  }, [orderId, user]);
  
  // Если произошла локальная ошибка загрузки
  if (loadError) {
    return (
      <div className="container py-5">
        <Alert variant="danger">
          {loadError}
        </Alert>
        <Button 
          variant="primary" 
          onClick={() => navigate('/admin/orders')}
          className="mt-3"
        >
          Вернуться к списку заказов
        </Button>
      </div>
    );
  }
  
  // Обработчик изменения статуса заказа
  const handleStatusChange = (e) => {
    setSelectedStatus(e.target.value);
  };
  
  // Обработчик изменения примечания к статусу
  const handleNoteChange = (e) => {
    setStatusNote(e.target.value);
  };
  
  // Открытие модального окна для подтверждения изменения статуса
  const handleOpenModal = () => {
    if (!selectedStatus) return;
    
    // Проверяем, не пытается ли пользователь выбрать текущий статус
    if (order && order.status && selectedStatus === order.status.id.toString()) {
      setError('Заказ уже имеет данный статус');
      setTimeout(() => setError(null), 3000);
      return;
    }
    
    setShowModal(true);
  };
  
  // Закрытие модального окна
  const handleCloseModal = () => {
    setShowModal(false);
  };
  
  // Обработчик подтверждения изменения статуса
  const handleConfirmStatusUpdate = async () => {
    try {
      setLoading(true);
      
      // Формируем данные для обновления в соответствии со схемой API
      const updateData = {
        status_id: parseInt(selectedStatus)
      };
      
      // Если есть примечание, добавляем его как комментарий
      if (statusNote) {
        updateData.comment = statusNote;
      }
      
      // Выполняем запрос на обновление статуса заказа
      const result = await updateOrderStatus(orderId, updateData);
      
      if (result) {
        // Обновление данных заказа после изменения статуса
        const updatedOrder = await getAdminOrderById(orderId);
        
        setOrder(updatedOrder);
        setUpdateSuccess(true);
        setTimeout(() => setUpdateSuccess(false), 3000);
      } else {
        setError('Не удалось обновить статус заказа');
      }
      
      setShowModal(false);
    } catch (err) {
      console.error('Ошибка при обновлении статуса заказа:', err);
      
      if (err.response) {
        console.error('Статус ошибки:', err.response.status);
        console.error('Данные ошибки:', err.response.data);
      }
      
      setError(err.response?.data?.detail || 'Не удалось обновить статус заказа');
    } finally {
      setLoading(false);
    }
  };
  
  // Обработчик открытия модального окна для изменения статуса оплаты
  const handleOpenPaymentModal = () => {
    setShowPaymentModal(true);
  };
  
  // Обработчик закрытия модального окна для изменения статуса оплаты
  const handleClosePaymentModal = () => {
    setShowPaymentModal(false);
  };
  
  // Обработчик подтверждения изменения статуса оплаты
  const handleConfirmPaymentUpdate = async (isPaid) => {
    try {
      setLoading(true);
      
      // Выполняем запрос на обновление статуса оплаты заказа
      const result = await updateOrderPaymentStatus(orderId, isPaid);
      
      if (result) {
        // Обновление данных заказа после изменения статуса оплаты
        const updatedOrder = await getAdminOrderById(orderId);
        
        setOrder(updatedOrder);
        setPaymentUpdateSuccess(true);
        setTimeout(() => setPaymentUpdateSuccess(false), 3000);
      } else {
        setError('Не удалось обновить статус оплаты заказа');
      }
      
      setShowPaymentModal(false);
    } catch (err) {
      console.error('Ошибка при обновлении статуса оплаты заказа:', err);
      
      if (err.response) {
        console.error('Статус ошибки:', err.response.status);
        console.error('Данные ошибки:', err.response.data);
      }
      
      setError(err.response?.data?.detail || 'Не удалось обновить статус оплаты заказа');
    } finally {
      setLoading(false);
    }
  };
  
  // Если заказ не загружен, показываем индикатор загрузки
  if ((loading || contextLoading) && !order) {
    return (
      <div className="container py-5 text-center">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </Spinner>
      </div>
    );
  }
  
  // Если произошла ошибка, показываем сообщение
  if ((error || contextError) && !order) {
    const errorMessage = error || contextError;
    return (
      <div className="container py-5">
        <Alert variant="danger">
          {typeof errorMessage === 'object' ? JSON.stringify(errorMessage) : (errorMessage || 'Произошла ошибка при загрузке данных заказа')}
        </Alert>
        <Button 
          variant="primary" 
          onClick={() => navigate('/admin/orders')}
          className="mt-3"
        >
          Вернуться к списку заказов
        </Button>
      </div>
    );
  }
  
  // Если заказ не найден
  if (!order) {
    return (
      <div className="container py-5">
        <Alert variant="warning">
          Заказ с ID {orderId} не найден
        </Alert>
        <Button 
          variant="primary" 
          onClick={() => navigate('/admin/orders')}
          className="mt-3"
        >
          Вернуться к списку заказов
        </Button>
      </div>
    );
  }
  
  return (
    <div className="container py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Детали заказа #{order.id}-{new Date(order.created_at).getFullYear()}</h2>
        <Button 
          variant="outline-secondary" 
          onClick={() => navigate('/admin/orders')}
        >
          Вернуться к списку
        </Button>
      </div>
      
      {updateSuccess && (
        <Alert variant="success" className="mb-4">
          Статус заказа успешно обновлен!
        </Alert>
      )}
      
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}
      
      <Row>
        {/* Основная информация о заказе */}
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Информация о заказе</h5>
            </Card.Header>
            <Card.Body>
              <Row>
                <Col md={6}>
                  <p><strong>ID заказа:</strong> {order.order_number}</p>
                  <p><strong>Дата создания:</strong> {formatDateTime(order.created_at)}</p>
                  <p><strong>Статус:</strong> <OrderStatusBadge status={order.status} /></p>
                </Col>
                <Col md={6}>
                  <p><strong>ID пользователя:</strong> {order.user_id}</p>
                  <p><strong>Email:</strong> {order.email}</p>
                  <p><strong>Телефон:</strong> {order.phone || 'Не указан'}</p>
                  <p><strong>Сумма заказа:</strong> {formatPrice(order.total_price)}</p>
                </Col>
              </Row>
              
              {order.comment && (
                <div className="mt-3">
                  <h6>Комментарий к заказу:</h6>
                  <p className="bg-light p-2 rounded">{order.comment}</p>
                </div>
              )}
            </Card.Body>
          </Card>
          
          {/* Товары в заказе */}
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Товары в заказе</h5>
            </Card.Header>
            <Card.Body>
              <Table responsive hover>
                <thead>
                  <tr>
                    <th>ID товара</th>
                    <th>Наименование</th>
                    <th>Цена за ед.</th>
                    <th>Кол-во</th>
                    <th>Сумма</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map(item => (
                    <tr key={item.id}>
                      <td>{item.product_id}</td>
                      <td>{item.product_name}</td>
                      <td>{formatPrice(item.unit_price || item.product_price || 0)}</td>
                      <td>{item.quantity}</td>
                      <td>{formatPrice((item.unit_price || item.product_price || 0) * item.quantity)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan="4" className="text-end"><strong>Итого:</strong></td>
                    <td><strong>{formatPrice(order.total_price || order.total_amount || 0)}</strong></td>
                  </tr>
                </tfoot>
              </Table>
            </Card.Body>
          </Card>
          
          {/* История статусов заказа */}
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">История статусов</h5>
            </Card.Header>
            <Card.Body>
              <div className="status-timeline">
                {order.status_history && order.status_history.length > 0 ? (
                  order.status_history.map((statusChange, index) => (
                    <div key={index} className="status-item mb-3">
                      <div className="d-flex justify-content-between">
                        <div>
                          <OrderStatusBadge status={statusChange.status} />
                        </div>
                        <small className="text-muted">
                          {formatDateTime(statusChange.changed_at || statusChange.timestamp)}
                        </small>
                      </div>
                      {statusChange.notes || statusChange.note ? (
                        <div className="status-note mt-1 bg-light p-2 rounded">
                          {statusChange.notes || statusChange.note}
                        </div>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <p>История статусов отсутствует</p>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        {/* Боковая панель с адресом доставки и управлением статусом */}
        <Col md={4}>
          {/* Адрес доставки */}
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Информация о получателе</h5>
            </Card.Header>
            <Card.Body>
              <p><strong>Получатель:</strong> {order.full_name}</p>
              <p><strong>Улица:</strong> {order.street || "Не указана"}</p>
              <p><strong>Город:</strong> {order.city || "Не указан"}</p>
              <p><strong>Регион:</strong> {order.region || "Не указан"}</p>
              <p><strong>Телефон:</strong> {order.phone || "Не указан"}</p>
              <p><strong>Email:</strong> {order.email}</p>
            </Card.Body>
          </Card>
          
          {/* Управление статусом оплаты */}
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Статус оплаты</h5>
            </Card.Header>
            <Card.Body>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <div>
                  <Badge bg={order.is_paid ? "success" : "danger"}>
                    {order.is_paid ? "Оплачен" : "Не оплачен"}
                  </Badge>
                </div>
                
                <Button 
                  variant={order.is_paid ? "outline-danger" : "outline-success"} 
                  size="sm"
                  onClick={handleOpenPaymentModal}
                  disabled={loading}
                >
                  {order.is_paid ? "Отметить как неоплаченный" : "Отметить как оплаченный"}
                </Button>
              </div>
              
              {paymentUpdateSuccess && (
                <Alert variant="success" className="mb-0">
                  Статус оплаты успешно обновлен
                </Alert>
              )}
            </Card.Body>
          </Card>
          
          {/* Управление статусом заказа */}
          <Card>
            <Card.Header>
              <h5 className="mb-0">Изменить статус</h5>
            </Card.Header>
            <Card.Body>
              <Form>
                <Form.Group className="mb-3">
                  <Form.Label>Новый статус</Form.Label>
                  <Form.Select
                    value={selectedStatus}
                    onChange={handleStatusChange}
                  >
                    <option value="">Выберите статус</option>
                    {statuses.map(status => (
                      <option 
                        key={status.id} 
                        value={status.id.toString()}
                        disabled={status.id.toString() === order.status.id.toString()}
                      >
                        {status.name}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Примечание (необязательно)</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={statusNote}
                    onChange={handleNoteChange}
                    placeholder="Добавьте примечание к изменению статуса"
                  />
                </Form.Group>
                
                <Button 
                  variant="primary" 
                  className="w-100"
                  disabled={!selectedStatus || loading}
                  onClick={handleOpenModal}
                >
                  {loading ? (
                    <>
                      <Spinner
                        as="span"
                        animation="border"
                        size="sm"
                        role="status"
                        aria-hidden="true"
                      />
                      <span className="ms-2">Обновление...</span>
                    </>
                  ) : (
                    'Обновить статус'
                  )}
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {/* Модальное окно подтверждения изменения статуса */}
      <Modal show={showModal} onHide={handleCloseModal}>
        <Modal.Header closeButton>
          <Modal.Title>Подтверждение изменения статуса</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Вы уверены, что хотите изменить статус заказа на <strong>
            {statuses.find(s => s.id.toString() === selectedStatus)?.name || selectedStatus}
          </strong>?</p>
          {statuses.find(s => s.id.toString() === selectedStatus)?.name === 'Отменен' && (
            <Alert variant="warning">
              Внимание! Отмена заказа необратима. После отмены заказ не может быть восстановлен.
            </Alert>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseModal}>
            Отмена
          </Button>
          <Button variant="primary" onClick={handleConfirmStatusUpdate}>
            Подтвердить
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Модальное окно подтверждения изменения статуса оплаты */}
      <Modal show={showPaymentModal} onHide={handleClosePaymentModal}>
        <Modal.Header closeButton>
          <Modal.Title>Подтверждение изменения статуса оплаты</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Вы уверены, что хотите изменить статус оплаты заказа на <strong>
            {order?.is_paid ? "Не оплачен" : "Оплачен"}
          </strong>?</p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleClosePaymentModal}>
            Отмена
          </Button>
          <Button 
            variant={order?.is_paid ? "danger" : "success"} 
            onClick={() => handleConfirmPaymentUpdate(!order?.is_paid)}
          >
            {order?.is_paid ? "Отметить как неоплаченный" : "Отметить как оплаченный"}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default AdminOrderDetail; 