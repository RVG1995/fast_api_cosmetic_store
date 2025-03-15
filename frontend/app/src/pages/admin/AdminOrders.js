import React, { useState, useEffect } from 'react';
import { Table, Button, Badge, Card, Form, Row, Col, Pagination } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { useOrders } from '../../context/OrderContext';
import { formatDateTime } from '../../utils/dateUtils';
import { formatPrice } from '../../utils/helpers';
import OrderStatusBadge from '../../components/OrderStatusBadge';
import './AdminOrders.css';

const AdminOrders = () => {
  const { getAllOrders, getOrderStatuses, loading, error } = useOrders();
  const [orders, setOrders] = useState([]);
  const [statuses, setStatuses] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    status_id: '',
    order_id: '',
    date_from: '',
    date_to: '',
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
        // Подготавливаем параметры запроса
        const params = {
          page: currentPage,
          size: 10
        };
        
        // Добавляем параметры фильтрации только если они заданы
        if (filters.status_id) params.status_id = Number(filters.status_id);
        if (filters.order_id) params.id = Number(filters.order_id);
        if (filters.date_from) params.date_from = filters.date_from;
        if (filters.date_to) params.date_to = filters.date_to;
        
        console.log('Отправляем запрос с параметрами:', params);
        
        const response = await getAllOrders(params);
        console.log('Полученный ответ от API:', response);
        
        if (response && response.items) {
          setOrders(response.items);
          
          // Проверяем, что значения total и limit являются числами и корректны
          const total = typeof response.total === 'number' ? response.total : 0;
          const size = typeof response.size === 'number' && response.size > 0 ? response.size : 10;
          // Используем pages из ответа API, если оно доступно, иначе вычисляем
          let calculatedPages;
          if (typeof response.pages === 'number' && response.pages > 0) {
            calculatedPages = response.pages;
            console.log('Используем значение pages из API:', calculatedPages);
          } else {
            calculatedPages = Math.max(1, Math.ceil(total / size));
            console.log('Вычисляем pages локально:', calculatedPages, 'из total:', total, 'и size:', size);
          }
          
          // Убедимся, что totalPages не меньше 1
          const finalPages = Math.max(1, calculatedPages);
          console.log('Итоговое количество страниц:', finalPages);
          
          setTotalPages(finalPages);
          
          // Если текущая страница больше общего количества страниц,
          // автоматически перейдем на последнюю доступную страницу
          if (currentPage > finalPages) {
            console.log(`Текущая страница (${currentPage}) больше общего количества (${finalPages}), переходим на страницу ${finalPages}`);
            setCurrentPage(finalPages);
          }
        } else {
          console.log('Ответ не содержит элементов или некорректен');
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
      status_id: '',
      order_id: '',
      date_from: '',
      date_to: '',
    });
    setCurrentPage(1);
  };

  // Формирование элементов пагинации
  const renderPagination = () => {
    console.log('Рендеринг пагинации, totalPages:', totalPages, 'currentPage:', currentPage);
    
    // Если страниц нет или только одна, не показываем пагинацию
    if (totalPages <= 1) {
      return null;
    }
    
    // Проверка валидности currentPage перед рендерингом
    let activePage = currentPage;
    if (isNaN(activePage) || activePage < 1) {
      console.error('Некорректная активная страница:', activePage, 'установлена на 1');
      activePage = 1;
    } else if (activePage > totalPages) {
      console.error('Активная страница больше максимума:', activePage, 'установлена на', totalPages);
      activePage = totalPages;
    }
    
    // Если страниц мало, просто показываем все
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, i) => {
        const pageNum = i + 1;
        return (
          <Pagination.Item
            key={pageNum}
            active={pageNum === activePage}
            onClick={() => {
              console.log(`Клик на страницу ${pageNum}`);
              safeSetCurrentPage(pageNum);
            }}
          >
            {pageNum}
          </Pagination.Item>
        );
      });
    }
    
    // Для большого количества страниц показываем текущую, несколько соседних и краевые
    const items = [];
    
    // Первая страница
    items.push(
      <Pagination.Item
        key={1}
        active={1 === activePage}
        onClick={() => {
          console.log('Клик на страницу 1');
          safeSetCurrentPage(1);
        }}
      >
        1
      </Pagination.Item>
    );
    
    // Если текущая страница далеко от начала - добавляем троеточие
    if (activePage > 3) {
      items.push(<Pagination.Ellipsis key="ellipsis1" />);
    }
    
    // Страницы вокруг текущей
    for (let i = Math.max(2, activePage - 1); i <= Math.min(totalPages - 1, activePage + 1); i++) {
      items.push(
        <Pagination.Item
          key={i}
          active={i === activePage}
          onClick={() => {
            console.log(`Клик на страницу ${i}`);
            safeSetCurrentPage(i);
          }}
        >
          {i}
        </Pagination.Item>
      );
    }
    
    // Если текущая страница далеко от конца - добавляем троеточие
    if (activePage < totalPages - 2) {
      items.push(<Pagination.Ellipsis key="ellipsis2" />);
    }
    
    // Последняя страница
    if (totalPages > 1) {
      items.push(
        <Pagination.Item
          key={totalPages}
          active={totalPages === activePage}
          onClick={() => {
            console.log(`Клик на страницу ${totalPages}`);
            safeSetCurrentPage(totalPages);
          }}
        >
          {totalPages}
        </Pagination.Item>
      );
    }
    
    return items;
  };

  // Безопасная установка страницы с проверкой на валидное число
  const safeSetCurrentPage = (page) => {
    // Преобразуем вход в целое число
    const parsedPage = parseInt(page, 10);
    console.log('Попытка установить страницу:', parsedPage, 'максимум страниц:', totalPages);
    
    // Проверка валидности
    if (isNaN(parsedPage)) {
      console.error('Некорректное значение страницы (не число):', page);
      return; // Выходим без изменения страницы
    }
    
    // Проверка диапазона
    if (parsedPage < 1) {
      console.error('Некорректное значение страницы (меньше 1):', parsedPage);
      setCurrentPage(1); // Устанавливаем минимальное значение
      return;
    }
    
    if (parsedPage > totalPages) {
      console.error('Некорректное значение страницы (больше максимума):', parsedPage, 'максимум:', totalPages);
      setCurrentPage(totalPages); // Устанавливаем максимальное значение
      return;
    }
    
    // Если все проверки пройдены, устанавливаем новую страницу
    setCurrentPage(parsedPage);
  };

  return (
    <div className="container py-4 admin-orders-container">
      <h2 className="mb-4">Управление заказами</h2>
      
      {error && (
        <div className="alert alert-danger">
          {typeof error === 'object' ? JSON.stringify(error) : error}
        </div>
      )}
      
      {/* Фильтры */}
      <Card className="mb-4 filters-card">
        <Card.Body>
          <h5 className="mb-3">Фильтры</h5>
          <Form>
            <Row>
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Статус заказа</Form.Label>
                  <Form.Select
                    name="status_id"
                    value={filters.status_id}
                    onChange={handleFilterChange}
                  >
                    <option value="">Все статусы</option>
                    {Array.isArray(statuses) && statuses.length > 0 ? (
                      statuses.map(status => (
                        <option key={status.id} value={status.id}>
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
                  <Form.Label>ID заказа</Form.Label>
                  <Form.Control
                    type="number"
                    name="order_id"
                    value={filters.order_id}
                    onChange={handleFilterChange}
                    placeholder="Введите ID заказа"
                  />
                </Form.Group>
              </Col>
              
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Дата от</Form.Label>
                  <Form.Control
                    type="date"
                    name="date_from"
                    value={filters.date_from}
                    onChange={handleFilterChange}
                  />
                </Form.Group>
              </Col>
              
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Дата до</Form.Label>
                  <Form.Control
                    type="date"
                    name="date_to"
                    value={filters.date_to}
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
              <Table responsive hover className="admin-orders-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Дата создания</th>
                    <th>Зарегистрирован</th>
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
                        <td className="text-center">
                          {order.user_id ? (
                            <i className="bi bi-check-circle-fill text-success" title="Зарегистрированный пользователь"></i>
                          ) : (
                            <i className="bi bi-x-circle-fill text-danger" title="Гость"></i>
                          )}
                        </td>
                        <td>
                          {order.full_name || 'Нет данных'}
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
                    <Pagination.First
                      onClick={() => {
                        console.log('Клик на First, переход на страницу 1');
                        safeSetCurrentPage(1);
                      }}
                      disabled={currentPage === 1}
                    />
                    <Pagination.Prev
                      onClick={() => {
                        const prevPage = currentPage - 1;
                        console.log(`Клик на Prev, переход с ${currentPage} на ${prevPage}`);
                        safeSetCurrentPage(prevPage);
                      }}
                      disabled={currentPage === 1}
                    />
                    
                    {renderPagination()}
                    
                    <Pagination.Next
                      onClick={() => {
                        const nextPage = currentPage + 1;
                        console.log(`Клик на Next, переход с ${currentPage} на ${nextPage}`);
                        safeSetCurrentPage(nextPage);
                      }}
                      disabled={currentPage === totalPages}
                    />
                    <Pagination.Last
                      onClick={() => {
                        console.log(`Клик на Last, переход на страницу ${totalPages}`);
                        safeSetCurrentPage(totalPages);
                      }}
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