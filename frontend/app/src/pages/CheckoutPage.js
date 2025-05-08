import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useOrders } from '../context/OrderContext';
import { useAuth } from '../context/AuthContext';
import { Alert, Button, Form, Card, Row, Col, Spinner } from 'react-bootstrap';
import { formatPrice } from '../utils/helpers';
import PromoCodeForm from '../components/PromoCodeForm';
import './CheckoutPage.css';
import axios from 'axios';
import { API_URLS } from '../utils/constants';

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
    comment: '',
    personalDataAgreement: false,
    receiveNotifications: true // По умолчанию согласие на получение уведомлений для неавторизованных пользователей
  });
  
  const [validated, setValidated] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);
  const [orderNumber, setOrderNumber] = useState(null);
  const [redirectTimer, setRedirectTimer] = useState(null);
  const [cartTotal, setCartTotal] = useState(0);
  const [discountAmount, setDiscountAmount] = useState(0);
  const [nameSuggestions, setNameSuggestions] = useState([]);
  // сохраним объекты подсказок для FIAS
  const [regionOptions, setRegionOptions] = useState([]);
  const [regionFiasId, setRegionFiasId] = useState('');
  const [cityOptions, setCityOptions] = useState([]);
  const [cityFiasId, setCityFiasId] = useState('');
  // сохраним подсказки улиц с FIAS
  const [streetOptions, setStreetOptions] = useState([]);
  
  // Проверяем наличие товаров в корзине и вычисляем общую стоимость
  useEffect(() => {
    // Если заказ успешно создан, не выполняем редирект даже при пустой корзине
    if (orderSuccess) {
      return;
    }
    
    if (!cart || !cart.items || cart.items.length === 0) {
      navigate('/cart');
    } else {
      // Вычисляем общую стоимость корзины
      const total = cart.items.reduce((sum, item) => {
        return sum + (item.product?.price || 0) * item.quantity;
      }, 0);
      setCartTotal(total);
    }
  }, [cart, navigate, orderSuccess]);
  
  // Функция запроса подсказок FIO через axios с логами
  const fetchNameSuggestions = async (query) => {
    console.log('Dadata FIO fetch:', query);
    if (!query) return setNameSuggestions([]);
    try {
      const { data } = await axios.post(
        `${API_URLS.ORDER_SERVICE}/dadata/fio`,
        { query }
      );
      console.log('Dadata FIO resp:', data.suggestions);
      const values = data.suggestions.map(s => s.value);
      setNameSuggestions(values);
    } catch (e) {
      console.error('DaData FIO error', e);
    }
  };
  // Подсказки регионов
  const fetchRegionSuggestions = async (query) => {
    if (!query) {
      setRegionOptions([]);
      return;
    }
    try {
      const { data } = await axios.post(
        `${API_URLS.ORDER_SERVICE}/dadata/address`,
        { query, from_bound:{ value:'region' }, to_bound:{ value:'region' } }
      );
      setRegionOptions(data.suggestions);
    } catch(e) { console.error('DaData region error', e); }
  };
  // Подсказки городов через axios с логами и bound 'city'
  const fetchCitySuggestions = async (query) => {
    console.log('Dadata city fetch:', query, 'regionFiasId:', regionFiasId);
    if (!query) {
      setCityOptions([]);
      return;
    }
    const body = { query, from_bound:{ value:'city' }, to_bound:{ value:'city' } };
    if (regionFiasId) body.locations = [{ region_fias_id: regionFiasId }];
    try {
      const { data } = await axios.post(
        `${API_URLS.ORDER_SERVICE}/dadata/address`,
        body
      );
      console.log('Dadata city resp:', data.suggestions);
      setCityOptions(data.suggestions);
    } catch(e) {
      console.error('DaData city error', e);
    }
  };
  // Подсказки улиц через axios с логами и фильтром по city_fias_id
  const fetchStreetSuggestions = async (query) => {
    console.log('Dadata street fetch:', query, 'regionFiasId:', regionFiasId, 'cityFiasId:', cityFiasId);
    if (!query) {
      setStreetOptions([]);
      return;
    }
    const body = { query, from_bound:{ value:'street' }, to_bound:{ value:'street' } };
    if (cityFiasId) body.locations = [{ city_fias_id: cityFiasId }];
    try {
      const { data } = await axios.post(
        `${API_URLS.ORDER_SERVICE}/dadata/address`,
        body
      );
      console.log('Dadata street resp:', data.suggestions);
      setStreetOptions(data.suggestions);
    } catch(e) { console.error('DaData street error', e); }
  };

  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (name==='fullName')      { fetchNameSuggestions(value); setFormData(prev=>({...prev,fullName:value})); return; }
    if (name==='region') {
      fetchRegionSuggestions(value);
      setFormData(prev=>({...prev, region:value, city:'', street:''}));
      const found = regionOptions.find(s => s.value === value);
      setRegionFiasId(found?.data?.fias_id || '');
      return;
    }
    if (name==='city') {
      fetchCitySuggestions(value);
      setFormData(prev=>({...prev, city:value, street:''}));
      const found = cityOptions.find(s => s.value === value);
      // suggestion.data.fias_id now содержит city_fias_id при bound 'city'
      setCityFiasId(found?.data?.fias_id || found?.data?.city_fias_id || '');
      return;
    }
    if (name==='street') {
      fetchStreetSuggestions(value);
      setFormData(prev => ({ ...prev, street: value }));
      return;
    }
    if (type === 'checkbox')    { setFormData(prev=>({...prev,[name]:checked})); return; }
    setFormData(prev=>({...prev,[name]:value}));
  };

  // Обработчик применения промокода
  const handlePromoCodeApplied = (promoData) => {
    if (promoData) {
      // Рассчитываем скидку
      let calculatedDiscount = 0;
      if (promoData.discount_percent) {
        calculatedDiscount = Math.floor(cartTotal * promoData.discount_percent / 100);
      } else if (promoData.discount_amount) {
        calculatedDiscount = Math.min(promoData.discount_amount, cartTotal);
      }
      
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
    const requiredFields = ["fullName", "phone", "region", "city", "street", "personalDataAgreement"];
    const missingFields = requiredFields.filter(field => !formData[field]);
    
    if (missingFields.length > 0) {
      setValidated(true);
      const fieldNames = {
        fullName: "ФИО получателя",
        phone: "Телефон",
        region: "Регион",
        city: "Город",
        street: "Адрес доставки",
        personalDataAgreement: "Согласие на обработку персональных данных"
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
      personalDataAgreement: formData.personalDataAgreement,
      promo_code: promoCode ? promoCode.code : undefined,
      receive_notifications: !user ? formData.receiveNotifications : undefined // Передаем только для неавторизованных пользователей
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
        
        // Сразу очищаем корзину после успешного создания заказа
        console.log("Очищаем корзину после создания заказа");
        await clearCart();
        
        // Очищаем промокод после успешного создания заказа
        clearPromoCode();
        
        setOrderSuccess(true);
        setOrderNumber(formattedOrderNumber);
        
        // Откладываем редирект на 15 секунд (корзина уже очищена)
        const redirectTimer = setTimeout(() => {
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
                // Проверяем, пуста ли корзина, и если нет - очищаем
                if (cart && cart.items && cart.items.length > 0) {
                  console.log("Корзина до сих пор не пуста, очищаем перед редиректом");
                  clearCart();
                }
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
                <Form.Group controlId="fullName" className="position-relative">
                  <Form.Label>ФИО получателя</Form.Label>
                  <Form.Control
                    type="text"
                    name="fullName"
                    autoComplete="off"
                    value={formData.fullName}
                    onChange={handleChange}
                    required
                  />
                  {nameSuggestions.length > 0 && (
                    <div className="suggestions-list position-absolute bg-white border w-100" style={{ zIndex: 1000 }}>
                      {nameSuggestions.map((s, i) => (
                        <div
                          key={i}
                          className="suggestion-item px-2 py-1 hover-bg-light"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, fullName: s }));
                            setNameSuggestions([]);
                          }}
                        >
                          {s}
                        </div>
                      ))}
                    </div>
                  )}
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
                
                <Form.Group className="mb-3 position-relative" controlId="region">
                  <Form.Label>Регион</Form.Label>
                  <Form.Control
                    type="text"
                    name="region"
                    autoComplete="off"
                    value={formData.region}
                    onChange={handleChange}
                    required
                    placeholder="Москва и Московская область"
                  />
                  {regionOptions.length > 0 && (
                    <div className="suggestions-list position-absolute bg-white border w-100" style={{ zIndex: 1000 }}>
                      {regionOptions.map((opt, i) => (
                        <div
                          key={i}
                          className="suggestion-item hover-bg-light"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, region: opt.value, city: '', street: '' }));
                            setRegionFiasId(opt.data.fias_id || '');
                            setRegionOptions([]);
                          }}
                        >
                          {opt.value}
                        </div>
                      ))}
                    </div>
                  )}
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, укажите регион
                  </Form.Control.Feedback>
                </Form.Group>
                
                <Form.Group className="mb-3 position-relative" controlId="city">
                  <Form.Label>Город</Form.Label>
                  <Form.Control
                    type="text"
                    name="city"
                    autoComplete="off"
                    value={formData.city}
                    onChange={handleChange}
                    required
                    placeholder="Москва"
                  />
                  {cityOptions.length > 0 && (
                    <div className="suggestions-list position-absolute bg-white border w-100" style={{ zIndex: 1000 }}>
                      {cityOptions.map((opt, i) => (
                        <div
                          key={i}
                          className="suggestion-item hover-bg-light"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, city: opt.value, street: '' }));
                            setCityFiasId(opt.data.fias_id || opt.data.city_fias_id || '');
                            setCityOptions([]);
                          }}
                        >
                          {opt.value}
                        </div>
                      ))}
                    </div>
                  )}
                  <Form.Control.Feedback type="invalid">
                    Пожалуйста, укажите город
                  </Form.Control.Feedback>
                </Form.Group>
                
                <Form.Group className="position-relative" controlId="street">
                  <Form.Label>Адрес доставки</Form.Label>
                  <Form.Control
                    type="text"
                    name="street"
                    autoComplete="off"
                    value={formData.street}
                    onChange={handleChange}
                    required
                  />
                  {streetOptions.length > 0 && (
                    <div className="suggestions-list position-absolute bg-white border w-100" style={{ zIndex: 1000 }}>
                      {streetOptions.map((opt, i) => (
                        <div
                          key={i}
                          className="suggestion-item hover-bg-light"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, street: opt.data.street_with_type }));
                            setStreetOptions([]);
                          }}
                        >
                          {opt.data.street_with_type}
                        </div>
                      ))}
                    </div>
                  )}
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
                
                <Form.Group className="mb-3">
                  <Form.Check
                    required
                    type="checkbox"
                    id="personalDataAgreement"
                    name="personalDataAgreement"
                    checked={formData.personalDataAgreement}
                    onChange={handleChange}
                    label="Я согласен на обработку персональных данных"
                    feedback="Необходимо согласие на обработку персональных данных"
                    feedbackType="invalid"
                  />
                </Form.Group>
                
                {/* Опция подписки на уведомления для незарегистрированных пользователей */}
                {!user && (
                  <Form.Group className="mb-3">
                    <Form.Check
                      type="checkbox"
                      id="receiveNotifications"
                      name="receiveNotifications"
                      checked={formData.receiveNotifications}
                      onChange={handleChange}
                      label="Я хочу получать уведомления о статусе заказа по email"
                    />
                  </Form.Group>
                )}
                
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
                    {cart.items.map((item, idx) => (
                      <div key={item.id !== undefined ? item.id : `anon_${item.product_id}_${idx}`} className="checkout-item">
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