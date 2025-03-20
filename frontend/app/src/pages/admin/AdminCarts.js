import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Table, Container, Button, Form, InputGroup, Row, Col, Badge, Spinner, Alert } from 'react-bootstrap';
import axios from 'axios';
import { formatDateTime } from '../../utils/dateUtils';
import { API_URLS, STORAGE_KEYS } from '../../utils/constants';

const AdminCarts = () => {
  const [carts, setCarts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterOption, setFilterOption] = useState('all');
  const [sortOption, setSortOption] = useState('newest');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 10;

  const fetchCarts = async () => {
    setLoading(true);
    setError(null);
    try {
      // Удаляем получение токена из localStorage
      // Теперь используем только куки для аутентификации
      
      const params = {
        page: currentPage,
        page_size: pageSize,
        filter: filterOption !== 'all' ? filterOption : undefined,
        sort: sortOption
      };
      
      console.log('Отправка запроса к API корзин с куки-авторизацией');
      
      const response = await axios.get(`${API_URLS.CART_SERVICE}/admin/carts`, {
        params,
        withCredentials: true  // Включаем передачу куки
      });
      
      console.log('Получен ответ от сервера:', response.data);
      setCarts(response.data.items || []);
      setTotalPages(Math.ceil((response.data.total || 0) / pageSize));
      setLoading(false);
    } catch (err) {
      console.error('Error fetching carts:', err);
      let errorMessage = 'Не удалось загрузить данные корзин. Попробуйте позже.';
      
      if (err.response) {
        if (err.response.status === 401) {
          errorMessage = 'Ошибка авторизации. Пожалуйста, войдите в систему снова.';
        } else if (err.response.status === 403) {
          errorMessage = 'У вас нет прав для просмотра этой страницы.';
        } else if (err.response.data && err.response.data.detail) {
          errorMessage = `Ошибка: ${err.response.data.detail}`;
        }
      }
      
      setError(errorMessage);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCarts();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, filterOption, sortOption]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchCarts();
  };

  const handleFilterChange = (e) => {
    setFilterOption(e.target.value);
    setCurrentPage(1);
  };

  const handleSortChange = (e) => {
    setSortOption(e.target.value);
    setCurrentPage(1);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const filteredCarts = searchTerm
    ? carts.filter(cart => 
        cart.id.toString().toLowerCase().includes(searchTerm.toLowerCase()) ||
        (cart.user_id && cart.user_id.toString().toLowerCase().includes(searchTerm.toLowerCase())) ||
        (cart.user_email && cart.user_email.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    : carts;

  return (
    <Container className="py-4">
      <h2>Управление корзинами пользователей</h2>
      
      <Row className="mb-4">
        <Col md={6}>
          <Form onSubmit={handleSearch}>
            <InputGroup>
              <Form.Control
                type="text"
                placeholder="Поиск по ID корзины или пользователя"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              <Button variant="primary" type="submit">Поиск</Button>
            </InputGroup>
          </Form>
        </Col>
        <Col md={3}>
          <Form.Select 
            value={filterOption} 
            onChange={handleFilterChange}
            aria-label="Фильтр корзин"
          >
            <option value="all">Все корзины</option>
            <option value="with_items">С товарами</option>
            <option value="empty">Пустые корзины</option>
            <option value="with_user">Авторизованные пользователи</option>
            <option value="anonymous">Анонимные корзины</option>
          </Form.Select>
        </Col>
        <Col md={3}>
          <Form.Select 
            value={sortOption} 
            onChange={handleSortChange}
            aria-label="Сортировка корзин"
          >
            <option value="newest">Сначала новые</option>
            <option value="oldest">Сначала старые</option>
            <option value="items_count_desc">По количеству товаров (убыв.)</option>
            <option value="items_count_asc">По количеству товаров (возр.)</option>
            <option value="total_price_desc">По стоимости (убыв.)</option>
            <option value="total_price_asc">По стоимости (возр.)</option>
          </Form.Select>
        </Col>
      </Row>

      {loading ? (
        <div className="text-center my-5">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </Spinner>
        </div>
      ) : error ? (
        <Alert variant="danger">{error}</Alert>
      ) : filteredCarts.length === 0 ? (
        <Alert variant="info">Корзины не найдены</Alert>
      ) : (
        <>
          <Table striped bordered hover responsive>
            <thead>
              <tr>
                <th>ID</th>
                <th>Пользователь</th>
                <th>Статус</th>
                <th>Создана</th>
                <th>Обновлена</th>
                <th>Кол-во товаров</th>
                <th>Сумма</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {filteredCarts.map(cart => (
                <tr key={cart.id}>
                  <td>{cart.id}</td>
                  <td>
                    {cart.user_id ? (
                      <Link to={`/admin/users/${cart.user_id}`}>
                        {cart.user_email || cart.user_id}
                      </Link>
                    ) : (
                      <Badge bg="secondary">Анонимный</Badge>
                    )}
                  </td>
                  <td>
                    {cart.is_shared && <Badge bg="info" className="me-1">Общая</Badge>}
                    {cart.total_items > 0 ? (
                      <Badge bg="success">Активная</Badge>
                    ) : (
                      <Badge bg="warning" text="dark">Пустая</Badge>
                    )}
                  </td>
                  <td>{formatDateTime(cart.created_at)}</td>
                  <td>{formatDateTime(cart.updated_at)}</td>
                  <td>{cart.total_items || 0}</td>
                  <td>{cart.total_price ? `${cart.total_price} ₽` : '0 ₽'}</td>
                  <td>
                    <Link to={`/admin/carts/${cart.id}`}>
                      <Button variant="primary" size="sm">
                        Просмотр
                      </Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>

          {totalPages > 1 && (
            <div className="d-flex justify-content-center mt-4">
              <ul className="pagination">
                <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                  <button 
                    className="page-link" 
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    Предыдущая
                  </button>
                </li>
                {[...Array(totalPages).keys()].map(number => (
                  <li 
                    key={number + 1} 
                    className={`page-item ${currentPage === number + 1 ? 'active' : ''}`}
                  >
                    <button
                      className="page-link"
                      onClick={() => handlePageChange(number + 1)}
                    >
                      {number + 1}
                    </button>
                  </li>
                ))}
                <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                  <button 
                    className="page-link" 
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Следующая
                  </button>
                </li>
              </ul>
            </div>
          )}
        </>
      )}
    </Container>
  );
};

export default AdminCarts; 