import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { 
  Container, Row, Col, Card, Table, Badge, Button, 
  Spinner, Alert, ListGroup, Image
} from 'react-bootstrap';
import axios from 'axios';
import { formatDateTime } from '../../utils/dateUtils';
import { API_URLS, STORAGE_KEYS } from '../../utils/constants';
import AdminBackButton from '../../components/common/AdminBackButton';

const AdminCartDetail = () => {
  const { cartId } = useParams();
  const navigate = useNavigate();
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCartDetails = async () => {
      setLoading(true);
      setError(null);
      try {
        // Удаляем получение токена из localStorage
        // Теперь используем только куки для аутентификации
        
        console.log(`Запрос данных корзины ID: ${cartId} с куки-авторизацией`);
        
        const response = await axios.get(`${API_URLS.CART_SERVICE}/admin/carts/${cartId}`, {
          withCredentials: true  // Включаем передачу куки
        });
        
        console.log('Получен ответ от сервера:', response.data);
        setCart(response.data);
      } catch (err) {
        console.error('Error fetching cart details:', err);
        let errorMessage = 'Не удалось загрузить информацию о корзине. Попробуйте позже.';
        
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
      } finally {
        setLoading(false);
      }
    };

    fetchCartDetails();
  }, [cartId]);

  const handleBackClick = () => {
    navigate('/admin/carts');
  };

  if (loading) {
    return (
      <Container className="py-5 text-center">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </Spinner>
      </Container>
    );
  }

  if (error) {
    return (
      <Container className="py-5">
        <Alert variant="danger">{error}</Alert>
        <div className="text-center mt-3">
          <AdminBackButton
            to="/admin/carts"
            label="Вернуться к списку корзин"
          />
        </div>
      </Container>
    );
  }

  if (!cart) {
    return (
      <Container className="py-5">
        <Alert variant="warning">Корзина не найдена или была удалена</Alert>
        <div className="text-center mt-3">
          <AdminBackButton
            to="/admin/carts"
            label="Вернуться к списку корзин"
          />
        </div>
      </Container>
    );
  }

  const cartStatus = () => {
    if (cart.is_shared) {
      return <Badge bg="info" className="me-2">Общая</Badge>;
    }
    if (cart.items && cart.items.length > 0) {
      return <Badge bg="success">Активная</Badge>;
    }
    return <Badge bg="warning" text="dark">Пустая</Badge>;
  };

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Информация о корзине #{cart.id}</h2>
        <AdminBackButton
          to="/admin/carts"
          label="Назад к списку корзин"
          variant="outline-primary"
        />
      </div>

      <Row>
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Основная информация</h5>
            </Card.Header>
            <Card.Body>
              <ListGroup variant="flush">
                <ListGroup.Item>
                  <strong>ID корзины:</strong> {cart.id}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Владелец:</strong>{' '}
                  {cart.user_id ? (
                    <Link to={`/admin/users/${cart.user_id}`}>
                      {cart.user_email || `Пользователь #${cart.user_id}`}
                    </Link>
                  ) : (
                    <span>Анонимный пользователь</span>
                  )}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Статус:</strong>{' '}
                  {cartStatus()}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Создана:</strong> {formatDateTime(cart.created_at)}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Обновлена:</strong> {formatDateTime(cart.updated_at)}
                </ListGroup.Item>
              </ListGroup>
            </Card.Body>
          </Card>

          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Метаданные</h5>
            </Card.Header>
            <Card.Body>
              <ListGroup variant="flush">
                <ListGroup.Item>
                  <strong>Количество товаров:</strong> {cart.items?.length || 0}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Общее количество единиц:</strong> {cart.items?.reduce((sum, item) => sum + item.quantity, 0) || 0}
                </ListGroup.Item>
                <ListGroup.Item>
                  <strong>Общая стоимость:</strong> {cart.items?.reduce((sum, item) => sum + (item.product_price * item.quantity), 0) || 0} ₽
                </ListGroup.Item>
                {cart.share_code && (
                  <ListGroup.Item>
                    <strong>Код доступа:</strong> {cart.share_code}
                  </ListGroup.Item>
                )}
              </ListGroup>
            </Card.Body>
          </Card>
        </Col>

        <Col md={8}>
          <Card>
            <Card.Header>
              <h5 className="mb-0">Товары в корзине</h5>
            </Card.Header>
            <Card.Body>
              {cart.items && cart.items.length > 0 ? (
                <Table striped bordered hover responsive>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Товар</th>
                      <th>Цена</th>
                      <th>Количество</th>
                      <th>Сумма</th>
                      <th>Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cart.items.map(item => (
                      <tr key={item.id}>
                        <td>{item.product_id}</td>
                        <td>
                          <div className="d-flex align-items-center">
                            {item.product_image && (
                              <Image 
                                src={item.product_image} 
                                alt={item.product_name} 
                                width={40} 
                                height={40} 
                                className="me-2 object-fit-cover"
                              />
                            )}
                            <div>
                              <div>{item.product_name}</div>
                              <small className="text-muted">
                                ID: {item.product_id}
                              </small>
                            </div>
                          </div>
                        </td>
                        <td>{item.product_price} ₽</td>
                        <td>{item.quantity}</td>
                        <td>{item.product_price * item.quantity} ₽</td>
                        <td>
                          <Link to={`/admin/products/${item.product_id}`}>
                            <Button variant="outline-primary" size="sm">
                              К товару
                            </Button>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan="4" className="text-end"><strong>Итого:</strong></td>
                      <td colSpan="2"><strong>{cart.items.reduce((sum, item) => sum + (item.product_price * item.quantity), 0)} ₽</strong></td>
                    </tr>
                  </tfoot>
                </Table>
              ) : (
                <Alert variant="info">В корзине нет товаров</Alert>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default AdminCartDetail; 