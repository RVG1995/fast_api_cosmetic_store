import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Table, Badge, Button, Form, Alert, Spinner, Modal } from 'react-bootstrap';
import { useOrders } from '../../context/OrderContext';
import { formatDateTime } from '../../utils/dateUtils';
import { formatPrice } from '../../utils/helpers';

const AdminOrderDetail = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { 
    getAdminOrderById, 
    getOrderStatuses, 
    updateOrderStatus, 
    loading, 
    error 
  } = useOrders();
  
  const [order, setOrder] = useState(null);
  const [statuses, setStatuses] = useState([]);
  const [selectedStatus, setSelectedStatus] = useState('');
  const [statusNote, setStatusNote] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  
  // Загрузка деталей заказа и статусов
  useEffect(() => {
    const loadData = async () => {
      try {
        // Загрузка заказа
        const orderData = await getAdminOrderById(orderId);
        setOrder(orderData);
        
        // Загрузка всех возможных статусов
        const statusesData = await getOrderStatuses();
        setStatuses(statusesData);
      } catch (err) {
        console.error('Ошибка при загрузке данных заказа:', err);
      }
    };
    
    loadData();
  }, [getAdminOrderById, getOrderStatuses, orderId]);
  
  // Получение цвета для статуса заказа
  const getStatusBadgeVariant = (statusCode) => {
    const statusMap = {
      'NEW': 'info',
      'PROCESSING': 'primary',
      'SHIPPED': 'warning',
      'DELIVERED': 'success',
      'CANCELLED': 'danger',
      'RETURNED': 'secondary'
    };
    
    return statusMap[statusCode] || 'light';
  };
  
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
    setShowModal(true);
  };
  
  // Закрытие модального окна
  const handleCloseModal = () => {
    setShowModal(false);
  };
  
  // Обработчик подтверждения изменения статуса
  const handleConfirmStatusUpdate = async () => {
    try {
      await updateOrderStatus(orderId, {
        status_code: selectedStatus,
        note: statusNote || undefined
      });
      
      // Обновление данных заказа после изменения статуса
      const updatedOrder = await getAdminOrderById(orderId);
      setOrder(updatedOrder);
      
      setUpdateSuccess(true);
      setTimeout(() => setUpdateSuccess(false), 3000);
      setShowModal(false);
    } catch (err) {
      console.error('Ошибка при обновлении статуса заказа:', err);
    }
  };
  
  // Если заказ не загружен, показываем индикатор загрузки
  if (loading && !order) {
    return (
      <div className="container py-5 text-center">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </Spinner>
      </div>
    );
  }
  
  // Если произошла ошибка, показываем сообщение
  if (error && !order) {
    return (
      <div className="container py-5">
        <Alert variant="danger">
          {typeof error === 'object' ? JSON.stringify(error) : (error || 'Произошла ошибка при загрузке данных заказа')}
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
        <h2>Детали заказа #{order.id}</h2>
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
                  <p><strong>ID заказа:</strong> {order.id}</p>
                  <p><strong>Дата создания:</strong> {formatDateTime(order.created_at)}</p>
                  <p><strong>Статус:</strong> <Badge bg={getStatusBadgeVariant(order.status.code)}>{order.status.name}</Badge></p>
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
                      <td>{formatPrice(item.unit_price)}</td>
                      <td>{item.quantity}</td>
                      <td>{formatPrice(item.unit_price * item.quantity)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan="4" className="text-end"><strong>Итого:</strong></td>
                    <td><strong>{formatPrice(order.total_amount)}</strong></td>
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
                          <Badge bg={getStatusBadgeVariant(statusChange.status.code)}>
                            {statusChange.status.name}
                          </Badge>
                        </div>
                        <small className="text-muted">
                          {formatDateTime(statusChange.timestamp)}
                        </small>
                      </div>
                      {statusChange.note && (
                        <div className="status-note mt-1 bg-light p-2 rounded">
                          {statusChange.note}
                        </div>
                      )}
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
              <p><strong>{order.full_name}</strong></p>
              <p>{order.street}</p>
              <p>
                {order.city}
                {order.region && `, ${order.region}`}
              </p>
              <p>Телефон: {order.phone}</p>
              <p>Email: {order.email}</p>
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
                        key={status.code} 
                        value={status.code}
                        disabled={status.code === order.status.code}
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
      
      {/* Модальное окно подтверждения */}
      <Modal show={showModal} onHide={handleCloseModal}>
        <Modal.Header closeButton>
          <Modal.Title>Подтверждение изменения статуса</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Вы уверены, что хотите изменить статус заказа на <strong>
            {statuses.find(s => s.code === selectedStatus)?.name || selectedStatus}
          </strong>?</p>
          {selectedStatus === 'CANCELLED' && (
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
    </div>
  );
};

export default AdminOrderDetail; 