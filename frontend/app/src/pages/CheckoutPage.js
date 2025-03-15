import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useOrders } from '../context/OrderContext';
import { useAuth } from '../context/AuthContext';
import { Alert, Button, Form, Card, Row, Col, Spinner } from 'react-bootstrap';
import { formatPrice } from '../utils/helpers';
import { API_URLS } from '../utils/constants';
import './CheckoutPage.css';

const CheckoutPage = () => {
  const navigate = useNavigate();
  const { cart, clearCart } = useCart();
  const { createOrder, loading, error, setError } = useOrders();
  const { user } = useAuth();
  
  // Определяем статус авторизации
  const isAuthenticated = Boolean(user || localStorage.getItem('access_token'));
  
  // Состояния формы
  const [formData, setFormData] = useState({
    fullName: user?.full_name || '',
    email: user?.email || '',
    phone: '',
    city: '',
    region: '',
    street: '',
    comment: ''
  });
  
  const [validated, setValidated] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);
  const [orderNumber, setOrderNumber] = useState(null);
  
  // Проверяем наличие товаров в корзине
  useEffect(() => {
    if (!cart || !cart.items || cart.items.length === 0) {
      navigate('/cart');
    }
    
    // Предупреждаем неавторизованных пользователей
    if (!isAuthenticated) {
      setError("На данный момент для оформления заказа необходима авторизация. Пожалуйста, войдите в систему.");
    } else {
      setError(null);
    }
  }, [cart, navigate, isAuthenticated, setError]);
  
  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    
    console.log("Форма отправляется, валидность:", form.checkValidity());
    
    // Проверка статуса авторизации
    if (!isAuthenticated) {
      setError("На данный момент для оформления заказа необходима авторизация. Пожалуйста, войдите в систему.");
      return;
    }
    
    // Дополнительная проверка обязательных полей
    const requiredFields = ["fullName", "phone", "region", "city", "street"];
    const missingFields = requiredFields.filter(field => !formData[field]);
    
    if (missingFields.length > 0) {
      setValidated(true);
      const fieldNames = {
        fullName: "ФИО получателя",
        phone: "Телефон",
        region: "Регион",
        city: "Город",
        street: "Адрес доставки"
      };
      console.error("Отсутствуют обязательные поля:", missingFields.map(f => fieldNames[f]).join(", "));
      return;
    }
    
    // Проверка валидности формы
    if (form.checkValidity() === false) {
      e.stopPropagation();
      setValidated(true);
      console.log("Форма не валидна, проверьте все обязательные поля");
      
      // Вывод всех полей и их состояний валидности для отладки
      console.log("Состояние полей формы:");
      for (const key in formData) {
        console.log(`${key}: '${formData[key]}', required: ${form.elements[key]?.required || false}`);
      }
      
      return;
    }
    
    setValidated(true);
    
    // Подготовка данных для заказа в новом формате
    const orderData = {
      items: cart.items.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity
      })),
      fullName: formData.fullName,
      email: formData.email,
      phone: formData.phone,
      region: formData.region,
      city: formData.city,
      street: formData.street,
      comment: formData.comment || ''
    };
    
    console.log("Отправляемые данные заказа:", orderData);
    
    try {
      // Отправка заказа
      console.log("Начинаем создание заказа...");
      const result = await createOrder(orderData);
      console.log("Результат создания заказа:", result);
      
      if (result) {
        console.log("Заказ успешно создан с ID:", result.id);
        setOrderSuccess(true);
        setOrderNumber(result.id);
        clearCart(); // Очищаем корзину после успешного заказа
        
        // Через 5 секунд перенаправляем на страницу заказов
        setTimeout(() => {
          navigate('/orders');
        }, 5000);
      }
    } catch (err) {
      console.error("Ошибка создания заказа:", err);
      // Лог ошибки уже выполняется в контексте заказов
    }
  };
  
  // Если заказ успешно создан, показываем сообщение об успехе
  if (orderSuccess) {
    return (
      <div className="checkout-success-container">
        <Card className="checkout-success-card">
          <Card.Body className="text-center">
            <div className="success-icon">✓</div>
            <h2>Заказ успешно оформлен!</h2>
            <p>Ваш номер заказа: <strong>{orderNumber}</strong></p>
            <p>Мы отправили подтверждение на вашу электронную почту.</p>
            <p>Вы будете перенаправлены на страницу заказов через 5 секунд...</p>
            <Button 
              variant="primary" 
              onClick={() => navigate('/orders')}
              className="mt-3"
            >
              Перейти к заказам
            </Button>
          </Card.Body>
        </Card>
      </div>
    );
  }
  
  // Основной рендер страницы оформления заказа
  return (
    <div className="checkout-container">
      <h1 className="checkout-title">Оформление заказа</h1>
      
      {error && (
        <Alert variant="danger">
          {error}
          {!isAuthenticated && (
            <div className="mt-3">
              <Button 
                variant="primary" 
                onClick={() => navigate('/login')}
              >
                Войти в систему
              </Button>
            </div>
          )}
        </Alert>
      )}
      
      <Row>
        {/* Форма оформления заказа */}
        <Col md={8}>
          <Card className="checkout-card">
            <Card.Body>
              <Form noValidate validated={validated} onSubmit={handleSubmit}>
                <h3>Информация о доставке</h3>
                
                <Form.Group className="mb-3">
                  <Form.Label>ФИО получателя</Form.Label>
                  <Form.Control
                    type="text"
                    name="fullName"
                    value={formData.fullName}
                    onChange={handleChange}
                    required
                    placeholder="Иванов Иван Иванович"
                  />
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, введите ФИО получателя
                  </Form.Control.Feedback>
                </Form.Group>
                
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Email</Form.Label>
                      <Form.Control
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        required
                        placeholder="example@mail.ru"
                      />
                      <Form.Control.Feedback type="invalid">
                        Пожалуйста, введите корректный email
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Телефон</Form.Label>
                      <Form.Control
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        required
                        placeholder="9XXXXXXXXX"
                      />
                      <Form.Control.Feedback type="invalid">
                        Пожалуйста, введите номер телефона
                      </Form.Control.Feedback>
                    </Form.Group>
                  </Col>
                </Row>
                
                <Form.Group className="mb-3">
                  <Form.Label>Регион</Form.Label>
                  <Form.Control
                    type="text"
                    name="region"
                    value={formData.region}
                    onChange={handleChange}
                    required
                    placeholder="Свердловская область"
                  />
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, укажите регион доставки
                  </Form.Control.Feedback>
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Город</Form.Label>
                  <Form.Control
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={handleChange}
                    required
                    placeholder="Екатеринбург"
                  />
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, укажите город доставки
                  </Form.Control.Feedback>
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Адрес доставки</Form.Label>
                  <Form.Control
                    type="text"
                    name="street"
                    value={formData.street}
                    onChange={handleChange}
                    required
                    placeholder="ул. Ленина, д. 1, кв. 1"
                  />
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, укажите полный адрес доставки
                  </Form.Control.Feedback>
                  <Form.Text className="text-muted">
                    Укажите полный адрес, включая улицу, дом, корпус, квартиру
                  </Form.Text>
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Комментарий к заказу</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    name="comment"
                    value={formData.comment}
                    onChange={handleChange}
                  />
                </Form.Group>
                
                <Button 
                  variant="primary" 
                  type="submit" 
                  className="w-100 mt-3" 
                  disabled={loading || !isAuthenticated}
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
                      <span className="ms-2">Оформление заказа...</span>
                    </>
                  ) : (
                    'Оформить заказ'
                  )}
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>
        
        {/* Сводка заказа */}
        <Col md={4}>
          <Card className="checkout-summary-card">
            <Card.Header>
              <h3 className="checkout-summary-title">Ваш заказ</h3>
            </Card.Header>
            <Card.Body>
              <div className="checkout-items">
                {cart?.items?.map(item => (
                  <div key={item.id} className="checkout-item">
                    <div className="checkout-item-name">
                      {item.product.name} x {item.quantity}
                    </div>
                    <div className="checkout-item-price">
                      {formatPrice(item.total_price)}
                    </div>
                  </div>
                ))}
              </div>
              
              <hr />
              
              <div className="checkout-total">
                <span className="checkout-total-label">Итого:</span>
                <span className="checkout-total-price">
                  {formatPrice(cart?.total_price || 0)}
                </span>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CheckoutPage; 