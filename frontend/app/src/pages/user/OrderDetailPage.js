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
  Form,
  OverlayTrigger,
  Tooltip
} from 'react-bootstrap';
import { formatPrice } from '../../utils/helpers';
import { formatDateTime } from '../../utils/dateUtils';
import OrderStatusBadge from '../../components/OrderStatusBadge';
import './OrderDetailPage.css';
import axios from 'axios';
import { API_URLS } from '../../utils/constants';
import { useConfirm } from '../../components/common/ConfirmContext';

const OrderDetailPage = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { getOrderById, cancelOrder, loading, error } = useOrders();
  const { user } = useAuth();
  const [order, setOrder] = useState(null);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelLoading, setCancelLoading] = useState(false);
  const [cancelError, setCancelError] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [reorderLoading, setReorderLoading] = useState(false);
  const [reorderError, setReorderError] = useState(null);
  const [canReorder, setCanReorder] = useState(false);
  const [cannotReorderReason, setCannotReorderReason] = useState('');
  const [checkingReorderAvailability, setCheckingReorderAvailability] = useState(false);
  const confirm = useConfirm();
  
  // Загрузка заказа при монтировании компонента
  const loadOrder = useCallback(async () => {
    console.log('=== ДИАГНОСТИКА ЗАГРУЗКИ ЗАКАЗА ===');
    console.log('ID заказа:', orderId);
    console.log('Пользователь:', user);
    
    try {
      // Проверяем авторизацию пользователя
      if (!user) {
        console.error('Пользователь не авторизован');
        setLoadError('Для просмотра заказа необходима авторизация');
        return;
      }
      
      // Используем конфигурацию с куками
      const config = {
        withCredentials: true,
        headers: {
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
      
      // После загрузки заказа проверяем возможность его повторения
      await checkReorderAvailability(response.data);
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
  }, [orderId, user]);
  
  // Функция для проверки возможности повторения заказа
  const checkReorderAvailability = async (orderData) => {
    if (!orderData || !orderData.items || orderData.items.length === 0) {
      setCanReorder(false);
      setCannotReorderReason('Заказ не содержит товаров');
      return;
    }
    
    setCheckingReorderAvailability(true);
    
    try {
      // Собираем ID товаров из заказа
      const productIds = orderData.items.map(item => item.product_id);
      
      const config = {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      };
      
      // Выполняем запрос для проверки доступности товаров
      const url = `${API_URLS.PRODUCT_SERVICE}/products/check-availability`;
      console.log('Проверка доступности товаров:', url);
      console.log('ID товаров:', productIds);
      
      try {
        const response = await axios.post(url, { product_ids: productIds }, config);
        console.log('Ответ сервера о доступности товаров:', response.data);
        
        // Проверяем, все ли товары доступны
        const unavailableProducts = [];
        
        for (const [productId, availability] of Object.entries(response.data)) {
          if (!availability) {
            // Находим имя товара по product_id
            const productName = orderData.items.find(item => item.product_id === Number(productId))?.product_name || `ID: ${productId}`;
            unavailableProducts.push(productName);
          }
        }
        
        if (unavailableProducts.length > 0) {
          setCanReorder(false);
          setCannotReorderReason(`Следующие товары недоступны: ${unavailableProducts.join(', ')}`);
        } else {
          setCanReorder(true);
          setCannotReorderReason('');
        }
      } catch (apiError) {
        console.error('Ошибка API при проверке доступности товаров:', apiError);
        
        // Для отладки выводим подробную информацию об ошибке
        if (apiError.response) {
          console.error('Данные ответа:', apiError.response.data);
          console.error('Статус ответа:', apiError.response.status);
          console.error('Заголовки ответа:', apiError.response.headers);
        } else if (apiError.request) {
          console.error('Запрос был отправлен, но ответ не получен:', apiError.request);
        } else {
          console.error('Ошибка при настройке запроса:', apiError.message);
        }
        
        // Временная мера - предполагаем, что товары доступны если не можем проверить
        setCanReorder(true);
        setCannotReorderReason('');
        
        // Закомментированный код для показа ошибки, при необходимости раскомментировать
        /*
        setCanReorder(false);
        if (apiError.response && apiError.response.data && apiError.response.data.detail) {
          setCannotReorderReason(apiError.response.data.detail);
        } else {
          setCannotReorderReason('Не удалось проверить наличие товаров. Попробуйте позже.');
        }
        */
      }
    } catch (err) {
      console.error('Общая ошибка при проверке доступности товаров:', err);
      
      // Временная мера - предполагаем, что товары доступны если не можем проверить
      setCanReorder(true);
      setCannotReorderReason('');
    } finally {
      setCheckingReorderAvailability(false);
    }
  };
  
  // Запускаем загрузку заказа при монтировании и при изменении loadOrder
  useEffect(() => {
    console.log('OrderDetailPage: useEffect вызван');
    loadOrder();
  }, [loadOrder]);
  
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
  
  // Обработчик повторения заказа
  const handleReorder = async () => {
    if (!user) {
      setReorderError('Для повторения заказа необходимо авторизоваться');
      return;
    }
    
    if (!canReorder) {
      setReorderError(cannotReorderReason || 'Невозможно повторить заказ');
      return;
    }
    
    // Запрашиваем согласие на обработку персональных данных
    const agreed = await confirm({
      title: 'Согласие на обработку персональных данных',
      body: 'Для повторения заказа необходимо дать согласие на обработку персональных данных. Продолжить?'
    });
    if (!agreed) {
      setReorderError('Для повторения заказа необходимо согласиться на обработку персональных данных');
      return;
    }
    
    setReorderLoading(true);
    setReorderError(null);
    
    try {
      const config = {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json'
        }
      };
      
      const url = `${API_URLS.ORDER_SERVICE}/orders/${orderId}/reorder`;
      console.log('URL запроса повторения заказа:', url);
      
      const response = await axios.post(url, { personal_data_agreement: agreed }, config);
      console.log('Ответ от сервера:', response.data);
      
      if (response.data.success) {
        alert(response.data.message || 'Заказ успешно повторен');
        // Перенаправляем пользователя на страницу нового заказа
        navigate(`/orders/${response.data.order_id}`);
      } else {
        setReorderError(response.data.message || 'Не удалось повторить заказ');
      }
    } catch (err) {
      console.error('Ошибка при повторении заказа:', err);
      setReorderError(err.response?.data?.detail || 'Произошла ошибка при повторении заказа');
    } finally {
      setReorderLoading(false);
    }
  };
  
  // Формат типа доставки
  const formatDeliveryType = (type) => {
    if (!type) return 'Не указан';
    
    switch(type) {
      case 'boxberry_pickup_point':
        return 'Пункт выдачи BoxBerry';
      case 'boxberry_courier':
        return 'Курьер BoxBerry';
      case 'cdek_pickup_point':
        return 'Пункт выдачи СДЭК';
      case 'cdek_courier':
        return 'Курьер СДЭК';
      default:
        return type;
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
  
  // Отображение ошибок загрузки и контекста
  if ((error || loadError) && !order) {
    const message = loadError || (typeof error === 'object' ? JSON.stringify(error) : error);
    return (
      <Container className="order-detail-container py-5">
        <Alert variant="danger">
          {message}
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
              
              {/* Информация о промокоде и скидке */}
              {(order.promo_code || order.discount_amount > 0) && (
                <Row className="mb-4">
                  {order.promo_code && (
                    <Col md={6}>
                      <div className="order-info-item">
                        <div className="order-info-label">Промокод:</div>
                        <div className="order-info-value">
                          <Badge bg="success">{order.promo_code.code}</Badge>
                         
                        </div>
                      </div>
                    </Col>
                  )}
                  {order.discount_amount > 0 && (
                    <Col md={6}>
                      <div className="order-info-item">
                        <div className="order-info-label">Скидка:</div>
                        <div className="order-info-value"> {order.promo_code.discount_percent && 
                            <span className="ms-1">{order.promo_code.discount_percent}%</span>}
                          {!order.promo_code.discount_percent && order.promo_code.discount_amount && 
                            <span className="ms-1">{formatPrice(order.promo_code.discount_amount)}</span>}</div>
                      </div>
                    </Col>
                  )}
                </Row>
              )}
              
              {/* Информация о доставке */}
              <div className="mb-4">
                <h5 className="section-title">Информация о доставке</h5>
                <Row>
                  <Col md={6}>
                    <div className="order-info-item">
                      <div className="order-info-label">Адрес доставки:</div>
                      <div className="order-info-value">{order.delivery_address || "Не указан"}</div>
                    </div>
                  </Col>
                  <Col md={6}>
                    <div className="order-info-item">
                      <div className="order-info-label">Тип доставки:</div>
                      <div className="order-info-value">{formatDeliveryType(order.delivery_info?.delivery_type || order.delivery_type)}</div>
                    </div>
                  </Col>
                </Row>
                {/* Пункт выдачи Boxberry */}
                {(order.delivery_info?.boxberry_point_address || order.boxberry_point_address) && (
                  <div className="order-info-item mt-2">
                    <div className="order-info-label">Адрес пункта выдачи:</div>
                    <div className="order-info-value">{order.delivery_info?.boxberry_point_address || order.boxberry_point_address}</div>
                  </div>
                )}
                {/* Трек-номер */}
                {(order.delivery_info?.tracking_number || order.tracking_number) && 
                 (order.delivery_info?.delivery_type || order.delivery_type)?.includes('boxberry') && (
                  <div className="order-info-item mt-2">
                    <div className="order-info-label">Трек-номер:</div>
                    <div className="order-info-value">{order.delivery_info?.tracking_number || order.tracking_number}</div>
                  </div>
                )}
                <div className="order-info-item mt-2">
                  <div className="order-info-label">Статус доставки:</div>
                  <div className="order-info-value">
                    {order.delivery_info?.status_in_delivery_service
                      ? order.delivery_info.status_in_delivery_service
                      : <span className="text-muted">Заказ ещё не передан в доставку</span>
                    }
                  </div>
                </div>
                <div className="order-info-item mt-2">
                  <div className="order-info-label">Способ оплаты:</div>
                  <div className="order-info-value">
                    {order.is_payment_on_delivery ? 'Оплата при получении' : 'Оплата на сайте'}
                  </div>
                </div>
              </div>
              
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
                    <td colSpan="3" className="text-end fst-italic"><strong>Стоимость товаров:</strong></td>
                    <td className="text-end fst-italic">
                      <span>
                        {formatPrice(
                          order.items.reduce((total, item) => total + (item.unit_price || item.product_price || 0) * item.quantity, 0)
                        )}
                      </span>
                    </td>
                  </tr>
                {order.discount_amount > 0 && (
                    <tr>
                      <td colSpan="3" className="text-end fst-italic"><strong>Скидка по промокоду {order.promo_code?.code && (
                          <span>
                            ({order.promo_code.code}
                            {order.promo_code.discount_percent && <span> - {order.promo_code.discount_percent}%</span>})
                          </span>
                        )}:</strong>
                      </td>
                      <td className="text-end fst-italic">-{formatPrice(order.discount_amount)}</td>
                    </tr>
                  )}
                    <tr>
                      <td colSpan="3" className="text-end fst-italic"><strong>Стоимость доставки:</strong></td>
                      <td className="text-end">{formatPrice(order.delivery_info?.delivery_cost || order.delivery_cost || 0)}</td>
                    </tr>
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
              <h5 className="section-title">ФИО получателя</h5>
              <p className="mb-4">
                <strong>{order.full_name}</strong>
              </p>
              
              <h5 className="section-title">Контактная информация</h5>
              <div className="contact-info">
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
                
                {reorderError && (
                  <Alert variant="danger" className="mt-2 mb-2">
                    {reorderError}
                  </Alert>
                )}
                
                {/* Кнопка для повторного заказа */}
                {checkingReorderAvailability ? (
                  <Button 
                    variant="secondary" 
                    disabled
                  >
                    <Spinner size="sm" animation="border" className="me-2" />
                    Проверка доступности...
                  </Button>
                ) : canReorder ? (
                  <Button 
                    variant="outline-primary" 
                    onClick={handleReorder}
                    disabled={reorderLoading}
                  >
                    {reorderLoading ? (
                      <>
                        <Spinner size="sm" animation="border" className="me-2" />
                        Создание заказа...
                      </>
                    ) : (
                      <>Повторить заказ</>
                    )}
                  </Button>
                ) : (
                  <OverlayTrigger
                    placement="top"
                    overlay={<Tooltip id="tooltip-reorder">{cannotReorderReason}</Tooltip>}
                  >
                    <div className="d-grid">
                      <Button 
                        variant="secondary" 
                        disabled
                      >
                        Повторить заказ
                      </Button>
                    </div>
                  </OverlayTrigger>
                )}
                
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