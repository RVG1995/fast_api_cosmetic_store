import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useOrders } from '../../context/OrderContext';
import { useAuth } from '../../context/AuthContext';
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
import axios from 'axios';
import { STORAGE_KEYS, API_URLS } from '../../utils/constants';

const OrderDetailPage = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { getOrderById, cancelOrder, loading, error } = useOrders();
  const { token, user } = useAuth();
  const [order, setOrder] = useState(null);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelLoading, setCancelLoading] = useState(false);
  const [cancelError, setCancelError] = useState(null);
  const [loadError, setLoadError] = useState(null);
  
  // Загрузка заказа при монтировании компонента
  const loadOrder = async () => {
    console.log('=== ДИАГНОСТИКА ЗАГРУЗКИ ЗАКАЗА ===');
    console.log('ID заказа:', orderId);
    console.log('Токен в localStorage:', localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN) ? 'Присутствует' : 'Отсутствует');
    console.log('Токен в контексте:', token ? 'Присутствует' : 'Отсутствует');
    console.log('Пользователь:', user);
    
    try {
      // НЕ делаем перенаправление здесь, так как это уже обрабатывается в PrivateRoute
      
      // Принудительно используем метод запроса с токеном из localStorage
      console.log('===== НАЧАЛО ЗАПРОСА ЗАКАЗА =====');
      const actualToken = token || localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      
      if (!actualToken) {
        console.error('Отсутствует токен для запроса заказа');
        setLoadError('Для просмотра заказа необходима авторизация');
        return;
      }
      
      // Напрямую вызываем axios вместо getOrderById для диагностики
      const config = {
        headers: {
          'Authorization': `Bearer ${actualToken}`,
          'Content-Type': 'application/json'
        }
      };
      
      const url = `${API_URLS.ORDER_SERVICE}/orders/${orderId}`;
      console.log('URL запроса:', url);
      console.log('Конфигурация:', JSON.stringify(config));
      
      // Выполняем запрос
      const response = await axios.get(url, config);
      console.log('Ответ от сервера:', response.status);
      console.log('Данные заказа:', response.data);
      
      // Устанавливаем данные заказа
      setOrder(response.data);
    } catch (err) {
      console.error('===== ОШИБКА ЗАПРОСА ЗАКАЗА =====');
      console.error('Имя ошибки:', err.name);
      console.error('Сообщение ошибки:', err.message);
      
      if (err.response) {
        console.error('Статус ошибки:', err.response.status);
        console.error('Данные ошибки:', err.response.data);
        
        if (err.response.status === 401) {
          setLoadError('Для просмотра заказа необходима авторизация');
        } else if (err.response.status === 403) {
          setLoadError('У вас нет прав для просмотра этого заказа');
        } else if (err.response.status === 404) {
          setLoadError('Заказ не найден');
        } else {
          setLoadError(`Ошибка сервера: ${err.response.data.detail || 'Неизвестная ошибка'}`);
        }
      } else if (err.request) {
        // Запрос был сделан, но ответ не получен
        console.error('Запрос был отправлен, но ответ не получен:', err.request);
        setLoadError('Не удалось получить ответ от сервера. Проверьте подключение к интернету');
      } else {
        // Что-то произошло при настройке запроса
        setLoadError(`Ошибка при загрузке заказа: ${err.message}`);
      }
    }
  };
  
  // Запускаем загрузку заказа при монтировании компонента
  useEffect(() => {
    console.log('OrderDetailPage: useEffect вызван');
    loadOrder();
  }, [orderId]);
  
  // Диагностика условий отображения кнопки отмены
  useEffect(() => {
    if (order && order.status) {
      console.log('===== ДИАГНОСТИКА КНОПКИ ОТМЕНЫ =====');
      console.log('Статус заказа:', order.status);
      console.log('order.status.allow_cancel:', order.status.allow_cancel);
      console.log('!order.status.is_final:', !order.status.is_final);
      console.log('Условие отображения кнопки:', order.status.allow_cancel && !order.status.is_final);
      
      if (!order.status.allow_cancel) {
        console.log('Кнопка отмены скрыта: статус не позволяет отмену');
      } else if (order.status.is_final) {
        console.log('Кнопка отмены скрыта: статус является финальным');
      } else {
        console.log('Кнопка отмены должна отображаться');
      }
    }
  }, [order]);
  
  // Обработчик отмены заказа
  const handleCancelOrder = useCallback(async () => {
    console.log('=== НАЧАЛО ФУНКЦИИ handleCancelOrder ===');
    console.log('ID заказа:', orderId);
    console.log('Причина отмены:', cancelReason);
    console.log('Отображаем индикатор загрузки');
    
    setCancelLoading(true);
    setCancelError(null);
    
    try {
      console.log('Вызываем функцию cancelOrder из контекста заказов');
      const result = await cancelOrder(orderId, cancelReason);
      console.log('Результат отмены заказа:', result ? 'Успешно' : 'Ошибка');
      
      if (result) {
        console.log('Обновляем данные заказа в состоянии компонента');
        setOrder(result);
        setShowCancelModal(false);
        console.log('Закрываем модальное окно');
        
        // После успешной отмены запрашиваем актуальные данные заказа
        const updatedOrder = await getOrderById(orderId);
        if (updatedOrder) {
          setOrder(updatedOrder);
          console.log('Данные заказа обновлены после отмены');
        }
      } else {
        console.error('Функция cancelOrder вернула null');
        setCancelError('Не удалось отменить заказ. Сервер вернул неверные данные.');
      }
    } catch (err) {
      console.error('=== ОШИБКА В handleCancelOrder ===');
      console.error('Сообщение ошибки:', err.message);
      if (err.response) {
        console.error('Ответ сервера:', err.response.status, err.response.data);
      }
      setCancelError('Не удалось отменить заказ. Пожалуйста, попробуйте позже.');
    } finally {
      console.log('Скрываем индикатор загрузки');
      setCancelLoading(false);
      console.log('=== ЗАВЕРШЕНИЕ ФУНКЦИИ handleCancelOrder ===');
    }
  }, [orderId, cancelOrder, getOrderById, cancelReason, setCancelLoading, setCancelError, setShowCancelModal, setOrder]);
  
  // Вычисляем, можно ли отменить заказ
  const canCancelOrder = useMemo(() => {
    if (!order || !order.status) return false;
    return order.status.allow_cancel && !order.status.is_final;
  }, [order]);
  
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
              <h2 className="order-title mb-0">Заказ №{order.id}-{new Date(order.created_at).getFullYear()}</h2>
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
              {canCancelOrder && (
                <div className="mt-4 text-end">
                  <Button 
                    variant="danger" 
                    onClick={() => setShowCancelModal(true)}
                  >
                    <i className="bi bi-x-circle me-2"></i>
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
                  <strong>{order.full_name}</strong>
                </p>
                <p>
                  <strong>Улица:</strong> {order.street || "Не указана"}
                </p>
                <p>
                  <strong>Город:</strong> {order.city || "Не указан"}
                </p>
                <p>
                  <strong>Регион:</strong> {order.region || "Не указан"}
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