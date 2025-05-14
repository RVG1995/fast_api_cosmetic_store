import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { useOrders } from '../context/OrderContext';
import { useAuth } from '../context/AuthContext';
import { Alert, Button, Form, Card, Row, Col, Spinner } from 'react-bootstrap';
import { formatPrice } from '../utils/helpers';
import PromoCodeForm from '../components/PromoCodeForm';
import BoxberryPickupModal from '../components/cart/BoxberryPickupModal';
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
    delivery_address: '',
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
  // Подсказки адресов
  const [addressOptions, setAddressOptions] = useState([]);
  
  // Состояния для BoxBerry
  const [showBoxberryModal, setShowBoxberryModal] = useState(false);
  const [selectedPickupPoint, setSelectedPickupPoint] = useState(null);
  const [isBoxberryDelivery, setIsBoxberryDelivery] = useState(false);
  const [boxberryCityCode, setBoxberryCityCode] = useState(null);
  
  // Обновим состояние, убрав значение по умолчанию для типа доставки
  const [deliveryType, setDeliveryType] = useState('');
  
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
        `${API_URLS.DELIVERY_SERVICE}/delivery/dadata/fio`,
        { query }
      );
      console.log('Dadata FIO resp:', data.suggestions);
      const values = data.suggestions.map(s => s.value);
      setNameSuggestions(values);
    } catch (e) {
      console.error('DaData FIO error', e);
    }
  };

  // Подсказки адресов
  const fetchAddressSuggestions = async (query) => {
    console.log('Dadata address fetch:', query);
    if (!query) {
      setAddressOptions([]);
      return;
    }
    try {
      const { data } = await axios.post(
        `${API_URLS.DELIVERY_SERVICE}/delivery/dadata/address`,
        { query }
      );
      console.log('Dadata address resp:', data.suggestions);
      setAddressOptions(data.suggestions);
    } catch(e) { 
      console.error('DaData address error', e); 
    }
  };

  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    // Если включается BoxBerry, сбрасываем адрес доставки
    if (name === 'isBoxberryDelivery') {
      setIsBoxberryDelivery(checked);
      if (checked) {
        // Если у нас уже был выбран пункт, восстанавливаем его
        if (selectedPickupPoint) {
          setFormData(prev => ({
            ...prev, 
            delivery_address: selectedPickupPoint.Address
          }));
        } else {
          // Иначе очищаем поле адреса
          setFormData(prev => ({...prev, delivery_address: ''}));
        }
      }
      return;
    }
    
    if (name === 'fullName') { 
      fetchNameSuggestions(value); 
      setFormData(prev => ({...prev, fullName: value})); 
      return; 
    }
    
    if (name === 'delivery_address') {
      // Если активирована доставка BoxBerry, не разрешаем менять поле адреса
      if (isBoxberryDelivery) return;
      
      fetchAddressSuggestions(value);
      setFormData(prev => ({...prev, delivery_address: value}));
      return;
    }
    
    if (type === 'checkbox') { 
      setFormData(prev => ({...prev, [name]: checked})); 
      return; 
    }
    
    setFormData(prev => ({...prev, [name]: value}));
  };

  // Обработчик выбора пункта выдачи BoxBerry
  const handlePickupPointSelected = (point) => {
    console.log('Выбран пункт выдачи:', point);
    setSelectedPickupPoint(point);
    // Устанавливаем флаг isBoxberryDelivery в true при выборе пункта
    setIsBoxberryDelivery(true);
    setFormData(prev => ({
      ...prev,
      delivery_address: point.Address
    }));
    
    // Сохраняем код города, если он есть в модальном окне
    if (point.CityCode) {
      setBoxberryCityCode(point.CityCode);
    }
  };

  // Обработчик открытия модального окна BoxBerry
  const handleOpenBoxberryModal = () => {
    setShowBoxberryModal(true);
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
    
    // Валидация формы
    const form = e.currentTarget;
    setValidated(true);
    
    if (!form.checkValidity()) {
      e.stopPropagation();
      return;
    }
    
    // Проверяем, что выбран тип доставки
    if (!deliveryType) {
      alert('Пожалуйста, выберите способ доставки');
      return;
    }
    
    // Проверяем, что для пунктов выдачи указан адрес
    if (deliveryType.includes('pickup_point') && !selectedPickupPoint) {
      alert('Пожалуйста, выберите пункт выдачи');
      return;
    }
    
    // Дополнительная проверка обязательных полей
    const requiredFields = ["fullName", "phone", "delivery_address", "personalDataAgreement"];
    const missingFields = requiredFields.filter(field => !formData[field]);
    
    if (missingFields.length > 0) {
      setValidated(true);
      const fieldNames = {
        fullName: "ФИО получателя",
        phone: "Телефон",
        delivery_address: "Адрес доставки",
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
    
    try {
      // Подготовка данных для заказа в новом формате
      const orderData = {
        items: cart.items.map(item => ({
          product_id: item.product.id,
          quantity: item.quantity
        })),
        
        // Данные покупателя
        full_name: formData.fullName,
        email: formData.email,
        phone: formData.phone,
        delivery_address: formData.delivery_address,
        comment: formData.comment,
        
        // Информация о типе доставки
        delivery_type: deliveryType,
        boxberry_point_address: isBoxberryDelivery && selectedPickupPoint ? selectedPickupPoint.Address : null,
        
        // Промокод (если применен)
        promo_code: promoCode ? promoCode.code : null,
        
        // Соглашения
        personal_data_agreement: formData.personalDataAgreement,
        receive_notifications: formData.receiveNotifications
      };
      
      console.log("Отправляемые данные заказа:", orderData);
      
      // Отправка заказа
      console.log("Начинаем создание заказа...");
      
      // Отправка заказа на бэкенд
      const response = await axios.post(
        `${API_URLS.ORDER_SERVICE}/orders`,
        orderData,
        { withCredentials: true }
      );
      
      console.log("Заказ успешно создан:", response.data);
      
      if (response.data) {
        console.log("Заказ успешно создан с ID:", response.data.id);
        // Создаем номер заказа в формате "ID-ГОД" из даты создания заказа
        let orderYear;
        if (response.data.created_at) {
          // Используем год из даты создания заказа
          orderYear = new Date(response.data.created_at).getFullYear();
        } else {
          // Если дата создания недоступна, используем текущий год
          orderYear = new Date().getFullYear();
        }
        const formattedOrderNumber = `${response.data.id}-${orderYear}`;
        
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
                
                {/* В форме заказа добавим радиокнопки для выбора доставки */}
                <div className="delivery-options-container">
                  <div className="delivery-options-title">Способ доставки<span className="text-danger">*</span></div>
                  
                  <div className={`delivery-option ${deliveryType === 'boxberry_courier' ? 'selected' : ''}`}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="deliveryType"
                      id="boxberry_courier"
                      value="boxberry_courier"
                      checked={deliveryType === 'boxberry_courier'}
                      onChange={(e) => {
                        setDeliveryType(e.target.value);
                        setIsBoxberryDelivery(false);
                      }}
                      required
                    />
                    <label className="form-check-label" htmlFor="boxberry_courier">
                      Курьер BoxBerry
                    </label>
                  </div>
                  
                  <div className={`delivery-option ${deliveryType === 'boxberry_pickup_point' ? 'selected' : ''}`}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="deliveryType"
                      id="boxberry_pickup_point"
                      value="boxberry_pickup_point"
                      checked={deliveryType === 'boxberry_pickup_point'}
                      onChange={(e) => {
                        setDeliveryType(e.target.value);
                        setIsBoxberryDelivery(true);
                      }}
                      required
                    />
                    <label className="form-check-label" htmlFor="boxberry_pickup_point">
                      Пункт выдачи BoxBerry
                    </label>
                  </div>
                  
                  <div className={`delivery-option ${deliveryType === 'cdek_courier' ? 'selected' : ''}`}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="deliveryType"
                      id="cdek_courier"
                      value="cdek_courier"
                      checked={deliveryType === 'cdek_courier'}
                      onChange={(e) => {
                        setDeliveryType(e.target.value);
                        setIsBoxberryDelivery(false);
                      }}
                      required
                    />
                    <label className="form-check-label" htmlFor="cdek_courier">
                      Курьер СДЭК
                    </label>
                  </div>
                  
                  <div className={`delivery-option ${deliveryType === 'cdek_pickup_point' ? 'selected' : ''}`}>
                    <input
                      className="form-check-input"
                      type="radio"
                      name="deliveryType"
                      id="cdek_pickup_point"
                      value="cdek_pickup_point"
                      checked={deliveryType === 'cdek_pickup_point'}
                      onChange={(e) => {
                        setDeliveryType(e.target.value);
                        setIsBoxberryDelivery(false);
                      }}
                      required
                    />
                    <label className="form-check-label" htmlFor="cdek_pickup_point">
                      Пункт выдачи СДЭК
                    </label>
                  </div>
                  
                  {deliveryType === '' && validated && (
                    <div className="delivery-error">
                      Пожалуйста, выберите способ доставки
                    </div>
                  )}
                </div>
                
                {/* Опция выбора доставки в пункт выдачи BoxBerry */}
                {isBoxberryDelivery && (
                  <div className="mb-3">
                    <Button 
                      variant="outline-primary" 
                      onClick={handleOpenBoxberryModal}
                      className="d-block w-100"
                    >
                      {selectedPickupPoint ? "Изменить пункт выдачи" : "Выбрать пункт выдачи BoxBerry"}
                    </Button>
                    {selectedPickupPoint && (
                      <div className="mt-2 p-2 border rounded bg-light">
                        <p className="mb-1"><strong>{selectedPickupPoint.Name}</strong></p>
                        <p className="mb-1 small">{selectedPickupPoint.Address}</p>
                        <p className="mb-0 small text-muted">График работы: {selectedPickupPoint.WorkShedule}</p>
                      </div>
                    )}
                  </div>
                )}
                
                <Form.Group className="position-relative" controlId="delivery_address">
                  <Form.Label>Адрес доставки</Form.Label>
                  <Form.Control
                    type="text"
                    name="delivery_address"
                    autoComplete="off"
                    value={formData.delivery_address}
                    onChange={handleChange}
                    required
                    placeholder="Введите полный адрес"
                    disabled={isBoxberryDelivery}
                  />
                  {!isBoxberryDelivery && addressOptions.length > 0 && (
                    <div className="suggestions-list position-absolute bg-white border w-100" style={{ zIndex: 1000 }}>
                      {addressOptions.map((opt, i) => (
                        <div
                          key={i}
                          className="suggestion-item hover-bg-light"
                          onClick={() => {
                            setFormData(prev => ({ ...prev, delivery_address: opt.value }));
                            setAddressOptions([]);
                          }}
                        >
                          {opt.value}
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
                  disabled={loading || (isBoxberryDelivery && !selectedPickupPoint)}
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
      
      {/* Модальное окно выбора пункта выдачи BoxBerry */}
      <BoxberryPickupModal
        show={showBoxberryModal}
        onHide={() => setShowBoxberryModal(false)}
        onPickupPointSelected={handlePickupPointSelected}
        selectedAddress={formData.delivery_address}
      />
    </div>
  );
};

export default CheckoutPage; 