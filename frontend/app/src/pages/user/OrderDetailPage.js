import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useOrders } from '../../context/OrderContext';
import { 
  Container, 
  Row, 
  Col, 
  Card, 
  Badge, 
  Button, 
  Spinner, 
  Alert,
  Table,
  Modal,
  Form
} from 'react-bootstrap';
import { formatPrice } from '../../utils/helpers';
import { formatDateTime } from '../../utils/dateUtils';
import OrderStatusBadge from '../../components/OrderStatusBadge';
import './OrderDetailPage.css';

const OrderDetailPage = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { fetchOrder, cancelOrder, loading, error } = useOrders();
  const [order, setOrder] = useState(null);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelLoading, setCancelLoading] = useState(false);
  const [cancelError, setCancelError] = useState(null);
  
  // Загрузка заказа при монтировании компонента
  useEffect(() => {
    const loadOrder = async () => {
      const result = await fetchOrder(orderId);
      if (result) {
        setOrder(result);
      }
    };
    
    loadOrder();
  }, [orderId, fetchOrder]);
  
  // Обработчик отмены заказа
  const handleCancelOrder = async () => {
    setCancelLoading(true);
    setCancelError(null);
    
    try {
      const result = await cancelOrder(orderId, cancelReason);
      if (result) {
        setOrder(result);
        setShowCancelModal(false);
      }
    } catch (err) {
      setCancelError('Не удалось отменить заказ. Пожалуйста, попробуйте позже.');
    } finally {
      setCancelLoading(false);
    }
  };
  
  // Отображение загрузки
  if (loading && !order) {
    return (
      <Container className="order-detail-container text-center py-5">
        <Spinner animation="border" className="my-5" />
        <p>Загрузка информации о заказе...</p>
      </Container>
    );
  }
  
  // Отображение ошибки
  if (error && !order) {
    return (
      <Container className="order-detail-container py-5">
        <Alert variant="danger">
          {typeof error === 'object' ? JSON.stringify(error) : error}
          <div className="mt-3">
            <Button variant="outline-primary" onClick={() => navigate('/orders')}>
              Вернуться к списку заказов
            </Button>
          </div>
        </Alert>
      </Container>
    );
  }
  
  // Если заказ не найден
  if (!order) {
    return (
      <Container className="order-detail-container py-5">
        <Alert variant="warning">
          Заказ не найден
          <div className="mt-3">
            <Button variant="outline-primary" onClick={() => navigate('/orders')}>
              Вернуться к списку заказов
            </Button>
          </div>
        </Alert>
      </Container>
    );
  }
  
  return (
    <Container className="order-detail-container py-4">
      <div className="mb-4">
        <Button 
          variant="outline-secondary" 
          onClick={() => navigate('/orders')}
          className="back-button"
        >
          &larr; Назад к заказам
        </Button>
      </div>
      
      <Row>
        <Col lg={8}>
          <Card className="order-main-card mb-4">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h2 className="order-title mb-0">Заказ №{order.id}</h2>
              <OrderStatusBadge status={order.status} />
            </Card.Header>
            <Card.Body>
              <Row className="mb-4">
                <Col md={6}>
                  <div className="order-info-item">
                    <div className="order-info-label">Дата заказа:</div>
                    <div className="order-info-value">{formatDateTime(order.created_at)}</div>
                  </div>
                </Col>
                <Col md={6}>
                  <div className="order-info-item">
                    <div className="order-info-label">Статус оплаты:</div>
                    <div className="order-info-value">
                      {order.is_paid ? (
                        <Badge bg="success">Оплачен</Badge>
                      ) : (
                        <Badge bg="warning">Не оплачен</Badge>
                      )}
                    </div>
                  </div>
                </Col>
              </Row>
              
              {order.comment && (
                <div className="order-notes mb-4">
                  <h5>Комментарий к заказу:</h5>
                  <p>{order.comment}</p>
                </div>
              )}
              
              <h4 className="mt-4 mb-3">Товары в заказе</h4>
              <Table responsive>
                <thead>
                  <tr>
                    <th>Товар</th>
                    <th className="text-center">Цена</th>
                    <th className="text-center">Кол-во</th>
                    <th className="text-end">Сумма</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map(item => (
                    <tr key={item.id}>
                      <td>
                        <div className="order-product-name">{item.product_name}</div>
                        <div className="order-product-id">ID: {item.product_id}</div>
                      </td>
                      <td className="text-center">{formatPrice(item.product_price)}</td>
                      <td className="text-center">{item.quantity}</td>
                      <td className="text-end">{formatPrice(item.total_price)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan="3" className="text-end fw-bold">Итого:</td>
                    <td className="text-end fw-bold order-total-price">
                      {formatPrice(order.total_price)}
                    </td>
                  </tr>
                </tfoot>
              </Table>
              
              {/* Кнопка отмены заказа */}
              {order.status && order.status.allow_cancel && !order.status.is_final && (
                <div className="mt-4 text-end">
                  <Button 
                    variant="danger" 
                    onClick={() => setShowCancelModal(true)}
                  >
                    Отменить заказ
                  </Button>
                </div>
              )}
            </Card.Body>
          </Card>
          
          {/* История статусов заказа */}
          {order.status_history && order.status_history.length > 0 && (
            <Card className="order-history-card mb-4">
              <Card.Header>
                <h4 className="mb-0">История заказа</h4>
              </Card.Header>
              <Card.Body>
                <div className="order-status-timeline">
                  {order.status_history.map((history, index) => (
                    <div key={history.id} className="timeline-item">
                      <div className="timeline-badge" style={{ backgroundColor: history.status.color }}></div>
                      <div className="timeline-content">
                        <div className="timeline-date">{formatDateTime(history.changed_at)}</div>
                        <div className="timeline-title">
                          Статус изменен на <OrderStatusBadge status={history.status} />
                        </div>
                        {history.notes && (
                          <div className="timeline-notes">{history.notes}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card.Body>
            </Card>
          )}
        </Col>
        
        <Col lg={4}>
          {/* Информация о доставке */}
          <Card className="order-shipping-card mb-4">
            <Card.Header>
              <h4 className="mb-0">Информация о получателе</h4>
            </Card.Header>
            <Card.Body>
              <div className="shipping-address">
                <h5>Адрес доставки</h5>
                <p>
                  <strong>{order.full_name}</strong><br />
                  {order.street}<br />
                  {order.city}, {order.region}
                </p>
              </div>
              
              <div className="mt-3">
                <h5>Контактная информация</h5>
                {order.phone && (
                  <div className="contact-item">
                    <span className="contact-label">Телефон:</span>
                    <span className="contact-value">{order.phone}</span>
                  </div>
                )}
                {order.email && (
                  <div className="contact-item">
                    <span className="contact-label">Email:</span>
                    <span className="contact-value">{order.email}</span>
                  </div>
                )}
              </div>
            </Card.Body>
          </Card>
          
          {/* Действия с заказом */}
          <Card className="order-actions-card">
            <Card.Header>
              <h4 className="mb-0">Действия</h4>
            </Card.Header>
            <Card.Body>
              <div className="d-grid gap-2">
                <Link to="/orders" className="btn btn-outline-primary">
                  Вернуться к заказам
                </Link>
                
                {/* Кнопка для повторного заказа - можно добавить функционал */}
                <Button variant="outline-secondary" disabled>
                  Повторить заказ
                </Button>
                
                {/* Поддержка - можно добавить функционал */}
                <Button variant="outline-secondary" disabled>
                  Связаться с поддержкой
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {/* Модальное окно для отмены заказа */}
      <Modal show={showCancelModal} onHide={() => setShowCancelModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Отмена заказа #{order.id}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {cancelError && <Alert variant="danger">{cancelError}</Alert>}
          
          <p>Вы уверены, что хотите отменить заказ?</p>
          <p>Пожалуйста, укажите причину отмены:</p>
          
          <Form.Group className="mb-3">
            <Form.Control
              as="textarea"
              rows={3}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Укажите причину отмены заказа"
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowCancelModal(false)}>
            Отмена
          </Button>
          <Button 
            variant="danger" 
            onClick={handleCancelOrder}
            disabled={cancelLoading}
          >
            {cancelLoading ? (
              <>
                <Spinner
                  as="span"
                  animation="border"
                  size="sm"
                  role="status"
                  aria-hidden="true"
                />
                <span className="ms-2">Отмена заказа...</span>
              </>
            ) : (
              'Подтвердить отмену'
            )}
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default OrderDetailPage; 