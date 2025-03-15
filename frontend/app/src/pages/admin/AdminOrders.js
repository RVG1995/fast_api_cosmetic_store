import React, { useState, useEffect } from 'react';
import { Table, Button, Badge, Card, Form, Row, Col, Pagination } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { useOrders } from '../../context/OrderContext';
import { formatDateTime } from '../../utils/dateUtils';
import { formatPrice } from '../../utils/helpers';
import OrderStatusBadge from '../../components/OrderStatusBadge';

const AdminOrders = () => {
  const { getAllOrders, getOrderStatuses, loading, error } = useOrders();
  const [orders, setOrders] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    status: '',
    userId: '',
    dateFrom: '',
    dateTo: '',
  });

  // Загрузка статусов заказов при монтировании компонента
  useEffect(() => {
    const loadStatuses = async () => {
      try {
        const data = await getOrderStatuses();
        setStatuses(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Ошибка при загрузке статусов заказов:', err);
        setStatuses([]);
      }
    };
    
    loadStatuses();
  }, [getOrderStatuses]);

  // Загрузка списка заказов с учетом фильтров и пагинации
  useEffect(() => {
    const loadOrders = async () => {
      try {
        const response = await getAllOrders({
          page: currentPage,
          limit: 10,
          status: filters.status || undefined,
          user_id: filters.userId || undefined,
          date_from: filters.dateFrom || undefined,
          date_to: filters.dateTo || undefined,
        });
        
        if (response && response.items) {
          setOrders(response.items);
          setTotalPages(Math.ceil(response.total / response.limit));
        } else {
          setOrders([]);
          setTotalPages(1);
        }
      } catch (err) {
        console.error('Ошибка при загрузке заказов:', err);
        setOrders([]);
        setTotalPages(1);
      }
    };
    
    loadOrders();
  }, [getAllOrders, currentPage, filters]);

  // Обработчик изменения фильтров
  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
    setCurrentPage(1); // Сброс на первую страницу при изменении фильтров
  };

  // Обработчик сброса фильтров
  const handleResetFilters = () => {
    setFilters({
      status: '',
      userId: '',
      dateFrom: '',
      dateTo: '',
    });
    setCurrentPage(1);
  };

  // Формирование элементов пагинации
  const renderPagination = () => {
    // Если страниц мало, просто показываем все
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, i) => (
        <Pagination.Item
          key={i + 1}
          active={i + 1 === currentPage}
          onClick={() => setCurrentPage(i + 1)}
        >
          {i + 1}
        </Pagination.Item>
      ));
    }
    
    // Для большого количества страниц показываем текущую, несколько соседних и краевые
    const items = [];
    
    // Первая страница
    items.push(
      <Pagination.Item
        key={1}
        active={1 === currentPage}
        onClick={() => setCurrentPage(1)}
      >
        1
      </Pagination.Item>
    );
    
    // Если текущая страница далеко от начала - добавляем троеточие
    if (currentPage > 3) {
      items.push(<Pagination.Ellipsis key="ellipsis1" />);
    }
    
    // Страницы вокруг текущей
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
      items.push(
        <Pagination.Item
          key={i}
          active={i === currentPage}
          onClick={() => setCurrentPage(i)}
        >
          {i}
        </Pagination.Item>
      );
    }
    
    // Если текущая страница далеко от конца - добавляем троеточие
    if (currentPage < totalPages - 2) {
      items.push(<Pagination.Ellipsis key="ellipsis2" />);
    }
    
    // Последняя страница
    if (totalPages > 1) {
      items.push(
        <Pagination.Item
          key={totalPages}
          active={totalPages === currentPage}
          onClick={() => setCurrentPage(totalPages)}
        >
          {totalPages}
        </Pagination.Item>
      );
    }
    
    return items;
  };

  return (
    <div className="container py-4">
      <h2 className="mb-4">Управление заказами</h2>
      
      {error && (
        <div className="alert alert-danger">
          {typeof error === 'object' ? JSON.stringify(error) : error}
        </div>
      )}
      
      {/* Фильтры */}
      <Card className="mb-4">
        <Card.Body>
          <h5 className="mb-3">Фильтры</h5>
          <Form>
            <Row>
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Статус заказа</Form.Label>
                  <Form.Select
                    name="status"
                    value={filters.status}
                    onChange={handleFilterChange}
                  >
                    <option value="">Все статусы</option>
                    {Array.isArray(statuses) && statuses.length > 0 ? (
                      statuses.map(status => (
                        <option key={status.code} value={status.code}>
                          {status.name}
                        </option>
                      ))
                    ) : (
                      <option value="" disabled>Загрузка статусов...</option>
                    )}
                  </Form.Select>
                </Form.Group>
              </Col>
              
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>ID пользователя</Form.Label>
                  <Form.Control
                    type="text"
                    name="userId"
                    value={filters.userId}
                    onChange={handleFilterChange}
                    placeholder="Введите ID пользователя"
                  />
                </Form.Group>
              </Col>
              
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Дата от</Form.Label>
                  <Form.Control
                    type="date"
                    name="dateFrom"
                    value={filters.dateFrom}
                    onChange={handleFilterChange}
                  />
                </Form.Group>
              </Col>
              
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Дата до</Form.Label>
                  <Form.Control
                    type="date"
                    name="dateTo"
                    value={filters.dateTo}
                    onChange={handleFilterChange}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <div className="d-flex justify-content-end">
              <Button 
                variant="secondary" 
                onClick={handleResetFilters}
                className="me-2"
              >
                Сбросить фильтры
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
      
      {/* Таблица заказов */}
      <Card>
        <Card.Body>
          {loading ? (
            <div className="text-center my-4">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Загрузка...</span>
              </div>
            </div>
          ) : (
            <>
              <Table responsive hover>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Дата создания</th>
                    <th>Пользователь</th>
                    <th>Сумма</th>
                    <th>Статус</th>
                    <th>Способ оплаты</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {Array.isArray(orders) && orders.length > 0 ? (
                    orders.map(order => (
                      <tr key={order.id}>
                        <td>{order.id}-{new Date(order.created_at).getFullYear()}</td>
                        <td>{order.created_at ? formatDateTime(order.created_at) : '-'}</td>
                        <td>
                          {order.user_id || '-'}
                          <div className="small text-muted">{order.email || '-'}</div>
                        </td>
                        <td>{order.total_price !== undefined ? formatPrice(order.total_price) : '-'}</td>
                        <td>
                          {order.status ? (
                            <OrderStatusBadge status={order.status} />
                          ) : '-'}
                        </td>
                        <td>Онлайн</td>
                        <td>
                          <Link to={`/admin/orders/${order.id}`}>
                            <Button variant="outline-primary" size="sm">
                              Просмотр
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="7" className="text-center">
                        Заказы не найдены
                      </td>
                    </tr>
                  )}
                </tbody>
              </Table>
              
              {/* Пагинация */}
              {totalPages > 1 && (
                <div className="d-flex justify-content-center mt-4">
                  <Pagination>
                    <Pagination.Prev
                      onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                      disabled={currentPage === 1}
                    />
                    
                    {renderPagination()}
                    
                    <Pagination.Next
                      onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                      disabled={currentPage === totalPages}
                    />
                  </Pagination>
                </div>
              )}
            </>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default AdminOrders;