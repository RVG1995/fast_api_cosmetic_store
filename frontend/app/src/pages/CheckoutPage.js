import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useOrders } from '../context/OrderContext';
import { useAuth } from '../context/AuthContext';
import { Alert, Button, Form, Card, Row, Col, Spinner } from 'react-bootstrap';
import { formatPrice } from '../utils/helpers';
import PromoCodeForm from '../components/PromoCodeForm';
import './CheckoutPage.css';

const CheckoutPage = () => {
  const navigate = useNavigate();
  const { cart, clearCart } = useCart();
  const { createOrder, loading, error, setError, promoCode, clearPromoCode } = useOrders();
  const { user } = useAuth();
  
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
  const [redirectTimer, setRedirectTimer] = useState(null);
  const [appliedPromoCode, setAppliedPromoCode] = useState(null);
  const [cartTotal, setCartTotal] = useState(0);
  const [discountAmount, setDiscountAmount] = useState(0);
  
  // Проверяем наличие товаров в корзине и вычисляем общую стоимость
  useEffect(() => {
    if (!cart || !cart.items || cart.items.length === 0) {
      navigate('/cart');
    } else {
      // Вычисляем общую стоимость корзины
      const total = cart.items.reduce((sum, item) => {
        return sum + (item.product?.price || 0) * item.quantity;
      }, 0);
      setCartTotal(total);
    }
  }, [cart, navigate]);
  
  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Обработчик применения промокода
  const handlePromoCodeApplied = (promoData) => {
    setAppliedPromoCode(promoData);
    if (promoData) {
      const calculatedDiscount = promoData.discount;
      setDiscountAmount(calculatedDiscount);
      console.log('Промокод применен:', promoData, 'Скидка:', calculatedDiscount);
    } else {
      setDiscountAmount(0);
      console.log('Промокод удален');
    }
  };
  
  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    
    console.log("Форма отправляется, валидность:", form.checkValidity());
    
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
    
    // Проверка формата телефона
    const phoneRegex = /^(\+7|8)\d{10}$/;
    if (!phoneRegex.test(formData.phone)) {
      setError("Неверный формат телефона. Используйте формат +79999999999 или 89999999999");
      setValidated(true);
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
      comment: formData.comment || '',
      promo_code: promoCode ? promoCode.code : undefined
    };
    
    console.log("Отправляемые данные заказа:", orderData);
    
    try {
      // Отправка заказа
      console.log("Начинаем создание заказа...");
      const result = await createOrder(orderData);
      console.log("Результат создания заказа:", result);
      
      if (result) {
        console.log("Заказ успешно создан с ID:", result.id);
        // Создаем номер заказа в формате "ID-ГОД" из даты создания заказа
        let orderYear;
        if (result.created_at) {
          // Используем год из даты создания заказа
          orderYear = new Date(result.created_at).getFullYear();
        } else {
          // Если дата создания недоступна, используем текущий год
          orderYear = new Date().getFullYear();
        }
        const formattedOrderNumber = `${result.id}-${orderYear}`;
        setOrderSuccess(true);
        setOrderNumber(formattedOrderNumber);
        
        // Очищаем промокод после успешного создания заказа
        clearPromoCode();
        
        // Откладываем очистку корзины и редирект на 15 секунд
        const redirectTimer = setTimeout(() => {
          clearCart(); // Очищаем корзину непосредственно перед редиректом
          navigate('/orders');
        }, 15000);
        
        // Сохраняем ID таймера для возможности его отмены при ручном переходе
        setRedirectTimer(redirectTimer);
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
            <p>Вы будете перенаправлены на страницу заказов через 15 секунд...</p>
            <Button 
              variant="primary" 
              onClick={() => {
                // Отменяем таймер автоматического редиректа
                if (redirectTimer) {
                  clearTimeout(redirectTimer);
                }
                clearCart(); // Очищаем корзину перед редиректом
                clearPromoCode(); // Очищаем промокод при переходе на страницу заказов
                navigate('/orders');
              }}
              className="mt-3"
            >
              Перейти к заказам
            </Button>
          </Card.Body>
        </Card>
      </div>
    );
  }

  // Вычисляем итоговую стоимость с учетом скидки
  const finalTotal = Math.max(0, cartTotal - discountAmount);
  
  // Основной рендер страницы оформления заказа
  return (
    <div className="checkout-container">
      <h1 className="checkout-title">Оформление заказа</h1>
      
      {error && (
        <Alert variant="danger">
          {error}
        </Alert>
      )}
      
      <Row className="align-items-start">
        {/* Форма оформления заказа */}
        <Col md={8}>
          <Card className="checkout-card">
            <Card.Header>
              <h3 className="checkout-summary-title">Информация о доставке</h3>
            </Card.Header>
            <Card.Body>
              <Form noValidate validated={validated} onSubmit={handleSubmit}>
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
                        placeholder="+7XXXXXXXXXX или 8XXXXXXXXXX"
                        pattern="^(\+7|8)\d{10}$"
                      />
                      <Form.Control.Feedback type="invalid">
                        Пожалуйста, введите корректный номер телефона (начинается с +7 или 8)
                      </Form.Control.Feedback>
                      <Form.Text className="text-muted">
                        Формат: +79999999999 или 89999999999
                      </Form.Text>
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
                    placeholder="Москва и Московская область"
                  />
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, укажите регион
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
                    placeholder="Москва"
                  />
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, укажите город
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
                    placeholder="Улица, дом, квартира"
                  />
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, укажите адрес доставки
                  </Form.Control.Feedback>
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Комментарий к заказу</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    name="comment"
                    value={formData.comment}
                    onChange={handleChange}
                    placeholder="Комментарий к заказу (например, удобное время доставки)"
                  />
                </Form.Group>
                
                <Button 
                  variant="primary" 
                  type="submit" 
                  className="w-100"
                  disabled={loading}
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
                    "Оформить заказ"
                  )}
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>
        
        {/* Информация о заказе */}
        <Col md={4}>
          <Card className="checkout-summary-card">
            <Card.Header>
              <h3 className="checkout-summary-title">Ваш заказ</h3>
            </Card.Header>
            <Card.Body>
              {cart && cart.items && cart.items.length > 0 ? (
                <div className="checkout-summary">
                  <div className="checkout-items">
                    {cart.items.map(item => (
                      <div key={item.id} className="checkout-item">
                        <div className="item-name">{item.product.name}</div>
                        <div className="item-quantity">{item.quantity} x {formatPrice(item.product.price)} ₽</div>
                        <div className="item-total">{formatPrice(item.quantity * item.product.price)} ₽</div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Форма промокода */}
                  <PromoCodeForm 
                    email={formData.email} 
                    phone={formData.phone} 
                    cartTotal={cartTotal}
                    onPromoCodeApplied={handlePromoCodeApplied}
                  />
                  
                  <div className="checkout-total">
                    {discountAmount > 0 && (
                      <div className="discount">
                        <div>Скидка:</div>
                        <div>-{formatPrice(discountAmount)} ₽</div>
                      </div>
                    )}
                    
                    <div className="total">
                      <div>Итого:</div>
                      <div>
                        {discountAmount > 0 && (
                          <span className="old-price">{formatPrice(cartTotal)} ₽</span>
                        )}
                        <strong className={discountAmount > 0 ? "new-price" : ""}>
                          {formatPrice(finalTotal)} ₽
                        </strong>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="empty-cart-message">
                  Корзина пуста
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CheckoutPage; 