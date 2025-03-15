import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useOrders } from '../../context/OrderContext';
import { 
  Container, 
  Row, 
  Col, 
  Card,
  Pagination, 
  Spinner, 
  Alert,
  Table,
  Button
} from 'react-bootstrap';
import { formatPrice } from '../../utils/helpers';
import { formatDate } from '../../utils/dateUtils';
import './OrdersPage.css';
import OrderStatusBadge from '../../components/OrderStatusBadge';

const OrdersPage = () => {
  const { fetchUserOrders, getOrderStatuses, loading, error } = useOrders();
  const [orders, setOrders] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    pages: 1,
    total: 0,
    limit: 10
  });
  const [statusFilter, setStatusFilter] = useState(null);

  // Загрузка заказов пользователя
  const loadOrders = useCallback(async () => {
    const result = await fetchUserOrders(
      pagination.page, 
      pagination.limit, 
      statusFilter
    );
    
    if (result) {
      setOrders(result.items || []);
      setPagination({
        page: result.page || 1,
        pages: result.pages || 1,
        total: result.total || 0,
        limit: result.limit || 10
      });
    }
  }, [fetchUserOrders, pagination.page, pagination.limit, statusFilter]);

  // Загрузка статусов заказов для фильтрации
  const loadStatuses = useCallback(async () => {
    const statusesData = await getOrderStatuses();
    if (statusesData) {
      setStatuses(statusesData);
    }
  }, [getOrderStatuses]);

  // Загрузка заказов при монтировании компонента и изменении фильтров
  useEffect(() => {
    loadStatuses();
    loadOrders();
  }, [loadStatuses, loadOrders]);

  // Обработчик смены страницы
  const handlePageChange = (page) => {
    setPagination(prev => ({ ...prev, page }));
  };

  // Обработчик выбора статуса для фильтрации
  const handleStatusFilterChange = (statusId) => {
    setStatusFilter(statusId);
    setPagination(prev => ({ ...prev, page: 1 })); // Сбрасываем на первую страницу
  };

  // Отображение загрузки
  if (loading && orders.length === 0) {
    return (
      <Container className="orders-container text-center py-5">
        <Spinner animation="border" className="my-5" />
        <p>Загрузка заказов...</p>
      </Container>
    );
  }

  return (
    <Container className="orders-container py-4">
      <h1 className="orders-title mb-4">Мои заказы</h1>
      
      {error && (
        <Alert variant="danger">
          {typeof error === 'object' ? JSON.stringify(error) : error}
        </Alert>
      )}
      
      {/* Фильтр по статусам */}
      <div className="orders-filter mb-4">
        <Row>
          <Col>
            <div className="d-flex flex-wrap align-items-center">
              <span className="me-2">Фильтр по статусу:</span>
              <Button 
                variant={statusFilter === null ? "primary" : "outline-primary"}
                className="me-2 mb-2"
                onClick={() => handleStatusFilterChange(null)}
              >
                Все
              </Button>
              
              {statuses.map(status => (
                <Button
                  key={status.id}
                  variant={statusFilter === status.id ? "primary" : "outline-primary"}
                  className="me-2 mb-2"
                  onClick={() => handleStatusFilterChange(status.id)}
                  style={{ borderColor: status.color }}
                >
                  {status.name}
                </Button>
              ))}
            </div>
          </Col>
        </Row>
      </div>
      
      {/* Список заказов */}
      {orders.length === 0 ? (
        <Card className="text-center p-5">
          <Card.Body>
            <h3>У вас пока нет заказов</h3>
            <p>Перейдите в каталог, чтобы сделать покупки</p>
            <Link to="/products" className="btn btn-primary mt-3">
              Перейти в каталог
            </Link>
          </Card.Body>
        </Card>
      ) : (
        <div className="orders-list">
          <Table responsive className="orders-table">
            <thead>
              <tr>
                <th>№ заказа</th>
                <th>Дата</th>
                <th>Статус</th>
                <th>Сумма</th>
                <th className="text-center">Действия</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} className="order-item">
                  <td className="order-number">{order.id}</td>
                  <td className="order-date">{formatDate(order.created_at)}</td>
                  <td className="order-status">
                    <OrderStatusBadge status={order.status} />
                  </td>
                  <td className="order-price">{formatPrice(order.total_price)}</td>
                  <td className="order-actions text-center">
                    <Link 
                      to={`/orders/${order.id}`} 
                      className="btn btn-sm btn-outline-primary"
                    >
                      Подробнее
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
          
          {/* Пагинация */}
          {pagination.pages > 1 && (
            <div className="d-flex justify-content-center mt-4">
              <Pagination>
                <Pagination.First 
                  onClick={() => handlePageChange(1)}
                  disabled={pagination.page === 1}
                />
                <Pagination.Prev 
                  onClick={() => handlePageChange(pagination.page - 1)}
                  disabled={pagination.page === 1}
                />
                
                {/* Отображаем максимум 5 страниц вокруг текущей */}
                {[...Array(pagination.pages)].map((_, i) => {
                  const pageNumber = i + 1;
                  
                  // Отображаем только 5 страниц вокруг текущей
                  if (
                    pageNumber === 1 || 
                    pageNumber === pagination.pages ||
                    (pageNumber >= pagination.page - 2 && pageNumber <= pagination.page + 2)
                  ) {
                    return (
                      <Pagination.Item
                        key={pageNumber}
                        active={pagination.page === pageNumber}
                        onClick={() => handlePageChange(pageNumber)}
                      >
                        {pageNumber}
                      </Pagination.Item>
                    );
                  }
                  
                  // Отображаем разделитель, если есть пропуски
                  if (
                    (pageNumber === 2 && pagination.page > 4) ||
                    (pageNumber === pagination.pages - 1 && pagination.page < pagination.pages - 3)
                  ) {
                    return <Pagination.Ellipsis key={`ellipsis-${pageNumber}`} />;
                  }
                  
                  return null;
                })}
                
                <Pagination.Next 
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={pagination.page === pagination.pages}
                />
                <Pagination.Last 
                  onClick={() => handlePageChange(pagination.pages)}
                  disabled={pagination.page === pagination.pages}
                />
              </Pagination>
            </div>
          )}
        </div>
      )}
    </Container>
  );
};

export default OrdersPage; 