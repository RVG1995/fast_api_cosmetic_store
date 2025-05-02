import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Form, Button, Container, Row, Col, Card, Alert, Spinner } from 'react-bootstrap';
import { adminAPI } from '../../utils/api';
import { useOrders } from '../../context/OrderContext';
import { debounce } from 'lodash';
import { formatPrice } from '../../utils/helpers';
import { API_URLS } from '../../utils/constants';
import axios from 'axios';

const AdminOrderForm = ({ onClose, onSuccess }) => {
  // Состояние формы
  const [formData, setFormData] = useState({
    user_id: null,
    full_name: '',
    email: '',
    phone: '',
    region: '',
    city: '',
    street: '',
    comment: '',
    promo_code: '',
    status_id: 1, // По умолчанию первый статус (обычно "Новый")
    is_paid: false,
    items: []
  });

  // Состояние для списка пользователей
  const [users, setUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  
  // Состояние для продуктов
  const [products, setProducts] = useState([]);
  const [searchProduct, setSearchProduct] = useState('');
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [quantity, setQuantity] = useState(1);
  
  // Состояние формы
  const [statuses, setStatuses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Состояние для промокода
  const [promoCodeLoading, setPromoCodeLoading] = useState(false);
  const [promoCodeError, setPromoCodeError] = useState(null);
  const [appliedPromoCode, setAppliedPromoCode] = useState(null);
  const [orderTotal, setOrderTotal] = useState(0);
  const [discountAmount, setDiscountAmount] = useState(0);
  
  // Получаем методы из контекста заказов
  const { getOrderStatuses, createAdminOrder, checkPromoCode, calculateDiscount } = useOrders();

  // Загрузка статусов заказа
  useEffect(() => {
    const loadStatuses = async () => {
      try {
        const data = await getOrderStatuses();
        setStatuses(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Ошибка при загрузке статусов заказов:', err);
        setError('Не удалось загрузить статусы заказов');
      }
    };
    
    loadStatuses();
  }, [getOrderStatuses]);

  // Загрузка списка пользователей
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoadingUsers(true);
        const response = await adminAPI.getAllUsers();
        setUsers(response.data || []);
      } catch (err) {
        console.error('Ошибка при загрузке пользователей:', err);
        setError('Не удалось загрузить список пользователей');
      } finally {
        setLoadingUsers(false);
      }
    };
    
    fetchUsers();
  }, []);

  // Обработчик поиска пользователя с debounce
  const handleUserSearch = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    
    if (value.length > 1) {
      debouncedSearch(value);
    } else {
      setSearchResults([]);
    }
  };

  // Создаем функцию поиска с debounce
  const debouncedSearch = useCallback(
    debounce((term) => {
      const results = users.filter(user => {
        const fullName = `${user.first_name} ${user.last_name}`.toLowerCase();
        return fullName.includes(term.toLowerCase()) || 
               user.email.toLowerCase().includes(term.toLowerCase());
      });
      setSearchResults(results);
    }, 300),
    [users]
  );

  // Обработчик выбора пользователя
  const handleSelectUser = (user) => {
    setFormData({
      ...formData,
      user_id: user.id,
      full_name: `${user.first_name} ${user.last_name}`,
      email: user.email
    });
    setSearchTerm(`${user.first_name} ${user.last_name}`);
    setSearchResults([]);
  };

  // Обработчик очистки выбранного пользователя
  const handleClearUser = () => {
    setFormData({
      ...formData,
      user_id: null,
      full_name: '',
      email: ''
    });
    setSearchTerm('');
  };

  // Обработчик изменения полей формы
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  // Функция для поиска продуктов
  const searchProducts = async (term) => {
    if (!term || term.length < 2) return;
    
    try {
      setLoadingProducts(true);
      const response = await axios.get(`${API_URLS.PRODUCT_SERVICE}/products/search`, {
        params: { name: term },
        withCredentials: true
      });
      setProducts(response.data || []);
    } catch (err) {
      console.error('Ошибка при поиске продуктов:', err);
    } finally {
      setLoadingProducts(false);
    }
  };

  // Функция с debounce для поиска продуктов
  const debouncedProductSearch = useCallback(
    debounce((term) => searchProducts(term), 300),
    []
  );

  // Обработчик изменения поля поиска продукта
  const handleProductSearch = (e) => {
    const value = e.target.value;
    setSearchProduct(value);
    debouncedProductSearch(value);
  };

  // Обработчик выбора продукта
  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
    setSearchProduct('');
    setProducts([]);
  };

  // Обработчик добавления продукта к заказу
  const handleAddProduct = () => {
    if (!selectedProduct) return;
    
    // Проверяем, есть ли уже этот товар в списке
    const existingItemIndex = formData.items.findIndex(
      item => item.product_id === selectedProduct.id
    );
    
    if (existingItemIndex !== -1) {
      // Если товар уже есть, увеличиваем количество
      const newItems = [...formData.items];
      newItems[existingItemIndex].quantity += parseInt(quantity, 10);
      
      setFormData({
        ...formData,
        items: newItems
      });
    } else {
      // Если товара нет, добавляем новый
      setFormData({
        ...formData,
        items: [
          ...formData.items,
          {
            product_id: selectedProduct.id,
            quantity: parseInt(quantity, 10),
            product_name: selectedProduct.name,
            price: selectedProduct.price
          }
        ]
      });
    }
    
    setSelectedProduct(null);
    setQuantity(1);
  };

  // Обработчик изменения количества товара
  const handleQuantityChange = (index, newQuantity) => {
    // Проверяем, что количество положительное
    if (newQuantity < 1) newQuantity = 1;
    
    const newItems = [...formData.items];
    newItems[index].quantity = parseInt(newQuantity, 10);
    
    setFormData({
      ...formData,
      items: newItems
    });
  };

  // Обработчик удаления продукта из заказа
  const handleRemoveProduct = (index) => {
    const newItems = [...formData.items];
    newItems.splice(index, 1);
    setFormData({
      ...formData,
      items: newItems
    });
  };

  // Вычисляем общую сумму заказа
  const totalPrice = useMemo(() => {
    return formData.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  }, [formData.items]);

  // Рассчитываем итоговую сумму заказа при изменении товаров
  useEffect(() => {
    const total = formData.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    setOrderTotal(total);
    
    // Перерасчет скидки, если применен промокод
    if (appliedPromoCode) {
      let discount = 0;
      if (appliedPromoCode.discountPercent) {
        discount = Math.floor(total * appliedPromoCode.discountPercent / 100);
      } else if (appliedPromoCode.discountAmount) {
        discount = Math.min(appliedPromoCode.discountAmount, total);
      }
      setDiscountAmount(discount);
    }
  }, [formData.items, appliedPromoCode]);

  // Обработчик проверки промокода
  const handleCheckPromoCode = async () => {
    if (!formData.promo_code || formData.promo_code.trim() === '') {
      setPromoCodeError('Введите промокод');
      return;
    }
    
    if (!formData.email || !formData.email.includes('@')) {
      setPromoCodeError('Введите корректный email для проверки промокода');
      return;
    }
    
    // Проверка на наличие товаров в заказе
    if (formData.items.length === 0) {
      setPromoCodeError('Добавьте хотя бы один товар перед применением промокода');
      return;
    }
    
    try {
      setPromoCodeLoading(true);
      setPromoCodeError(null);
      
      // Проверка телефона для API
      let phone = formData.phone || '';
      if (phone && !phone.startsWith('8') && !phone.startsWith('+7')) {
        phone = '8' + phone;
      }
      
      // Если телефон пустой или слишком короткий, используем дефолтное значение
      if (!phone || phone.length < 11) {
        phone = '80000000000';
      }
      
      const result = await checkPromoCode(formData.promo_code, formData.email, phone);
      
      if (result && result.is_valid) {
        const promoData = {
          code: formData.promo_code,
          discountPercent: result.discount_percent,
          discountAmount: result.discount_amount,
          promoCodeId: result.promo_code?.id
        };
        
        setAppliedPromoCode(promoData);
        
        // Рассчитываем скидку
        let discount = 0;
        if (result.discount_percent) {
          discount = Math.floor(orderTotal * result.discount_percent / 100);
        } else if (result.discount_amount) {
          discount = Math.min(result.discount_amount, orderTotal);
        }
        
        setDiscountAmount(discount);
      } else {
        setPromoCodeError('Недействительный промокод');
        setAppliedPromoCode(null);
        setDiscountAmount(0);
      }
    } catch (err) {
      console.error('Ошибка при проверке промокода:', err);
      setPromoCodeError('Ошибка при проверке промокода');
      setAppliedPromoCode(null);
      setDiscountAmount(0);
    } finally {
      setPromoCodeLoading(false);
    }
  };

  // Обработчик удаления промокода
  const handleRemovePromoCode = () => {
    setFormData({
      ...formData,
      promo_code: ''
    });
    setAppliedPromoCode(null);
    setDiscountAmount(0);
    setPromoCodeError(null);
  };

  // Вычисляем итоговую стоимость с учетом скидки
  const finalTotal = Math.max(0, orderTotal - discountAmount);

  // Обработчик отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (formData.items.length === 0) {
      setError('Заказ должен содержать хотя бы один товар');
      return;
    }
    
    if (!formData.full_name || !formData.email || !formData.region || !formData.city || !formData.street) {
      setError('Пожалуйста, заполните все обязательные поля');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // Создаем объект заказа для отправки на сервер
      const orderData = {
        ...formData,
        status_id: parseInt(formData.status_id, 10),
        is_paid: Boolean(formData.is_paid)
      };
      
      // Обработка телефона
      if (orderData.phone) {
        // Добавляем префикс 8, если его нет
        if (!orderData.phone.startsWith('8') && !orderData.phone.startsWith('+7')) {
          orderData.phone = '8' + orderData.phone;
        }
        
        // Проверяем минимальную длину
        if (orderData.phone.startsWith('8') && orderData.phone.length < 11) {
          const missingDigits = 11 - orderData.phone.length;
          orderData.phone = orderData.phone + '0'.repeat(missingDigits);
        } else if (orderData.phone.startsWith('+7') && orderData.phone.length < 12) {
          const missingDigits = 12 - orderData.phone.length;
          orderData.phone = orderData.phone + '0'.repeat(missingDigits);
        }
      } else {
        // Если телефон пустой, заполняем его дефолтным значением
        orderData.phone = '80000000000';
      }
      
      // Если промокод был проверен и применен, добавляем его ID
      if (appliedPromoCode && appliedPromoCode.promoCodeId) {
        orderData.promo_code_id = appliedPromoCode.promoCodeId;
      } else if (!orderData.promo_code || orderData.promo_code.length < 3) {
        orderData.promo_code = null;
      }
      
      // Отправляем запрос для создания заказа через контекст
      const response = await createAdminOrder(orderData);
      
      setSuccess(true);
      if (onSuccess) onSuccess(response);
    } catch (err) {
      console.error('Ошибка при создании заказа:', err);
      
      // Проверяем, является ли detail массивом ошибок валидации
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Форматируем ошибки в текстовый формат
        const errorMessages = detail.map(item => 
          `${item.loc[item.loc.length - 1]}: ${item.msg}`
        ).join(', ');
        setError(`Ошибка валидации: ${errorMessages}`);
      } else {
        // Если не массив, используем старую логику
        setError(detail || 'Не удалось создать заказ');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container className="my-4">

          {error && <Alert variant="danger">{error}</Alert>}
          {success && <Alert variant="success">Заказ успешно создан!</Alert>}
          
          <Form onSubmit={handleSubmit}>
            <h5 className="mb-3">Информация о получателе</h5>
            <Row className="mb-4">
              <Col md={8}>
                <Form.Group className="mb-3">
                  <Form.Label>Поиск пользователя</Form.Label>
                  <div className="position-relative">
                    <Form.Control
                      type="text"
                      placeholder="Введите имя, фамилию или email пользователя"
                      value={searchTerm}
                      onChange={handleUserSearch}
                    />
                    {loadingUsers && (
                      <div className="position-absolute top-50 end-0 translate-middle-y pe-3">
                        <Spinner animation="border" size="sm" />
                      </div>
                    )}
                    {formData.user_id && (
                      <div className="position-absolute top-50 end-0 translate-middle-y pe-3">
                        <Button
                          variant="link"
                          size="sm"
                          className="p-0 text-danger"
                          onClick={handleClearUser}
                        >
                          ✕
                        </Button>
                      </div>
                    )}
                    {searchResults.length > 0 && !formData.user_id && (
                      <div className="position-absolute start-0 w-100 shadow bg-white rounded z-index-1000" style={{ zIndex: 1000 }}>
                        <ul className="list-group">
                          {searchResults.map(user => (
                            <li
                              key={user.id}
                              className="list-group-item list-group-item-action"
                              style={{ cursor: 'pointer' }}
                              onClick={() => handleSelectUser(user)}
                            >
                              {user.first_name} {user.last_name} ({user.email})
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                  <Form.Text className="text-muted">
                    {formData.user_id 
                      ? `Выбран пользователь с ID: ${formData.user_id}` 
                      : 'Оставьте поле пустым для анонимного заказа'}
                  </Form.Text>
                </Form.Group>
              </Col>
            </Row>
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>ФИО получателя*</Form.Label>
                  <Form.Control
                    type="text"
                    name="full_name"
                    value={formData.full_name}
                    onChange={handleChange}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Email*</Form.Label>
                  <Form.Control
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Телефон</Form.Label>
                  <Form.Control
                    type="text"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Промокод</Form.Label>
                  <div className="d-flex">
                    <Form.Control
                      type="text"
                      name="promo_code"
                      value={formData.promo_code}
                      onChange={handleChange}
                      disabled={!!appliedPromoCode}
                    />
                    {!appliedPromoCode ? (
                      <Button 
                        variant="outline-primary" 
                        className="ms-2"
                        onClick={handleCheckPromoCode}
                        disabled={promoCodeLoading}
                      >
                        {promoCodeLoading ? (
                          <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" />
                        ) : (
                          "Проверить"
                        )}
                      </Button>
                    ) : (
                      <Button 
                        variant="outline-danger" 
                        className="ms-2"
                        onClick={handleRemovePromoCode}
                      >
                        Удалить
                      </Button>
                    )}
                  </div>
                  {promoCodeError && (
                    <Form.Text className="text-danger">{promoCodeError}</Form.Text>
                  )}
                  {appliedPromoCode && (
                    <Alert variant="success" className="mt-2 mb-0">
                      <div>
                        <strong>Промокод применен: {appliedPromoCode.code}</strong>
                      </div>
                      <div>
                        {appliedPromoCode.discountPercent ? (
                          <span>Скидка {appliedPromoCode.discountPercent}%</span>
                        ) : (
                          <span>Скидка {formatPrice(appliedPromoCode.discountAmount)} ₽</span>
                        )}
                        {orderTotal > 0 && (
                          <span className="ms-2">({formatPrice(discountAmount)} ₽)</span>
                        )}
                      </div>
                    </Alert>
                  )}
                </Form.Group>
              </Col>
            </Row>
            
            <h5 className="mb-3 mt-4">Адрес доставки</h5>
            <Row>
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>Регион*</Form.Label>
                  <Form.Control
                    type="text"
                    name="region"
                    value={formData.region}
                    onChange={handleChange}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>Город*</Form.Label>
                  <Form.Control
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={handleChange}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={4}>
                <Form.Group className="mb-3">
                  <Form.Label>Улица, дом, квартира*</Form.Label>
                  <Form.Control
                    type="text"
                    name="street"
                    value={formData.street}
                    onChange={handleChange}
                    required
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Row>
              <Col md={12}>
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
              </Col>
            </Row>
            
            <h5 className="mb-3 mt-4">Товары</h5>
            <Row className="mb-3">
              <Col md={5}>
                <Form.Group>
                  <Form.Label>Поиск товара</Form.Label>
                  <div className="position-relative">
                    <Form.Control
                      type="text"
                      placeholder="Название товара"
                      value={searchProduct}
                      onChange={handleProductSearch}
                    />
                    {loadingProducts && (
                      <div className="position-absolute top-50 end-0 translate-middle-y pe-3">
                        <Spinner animation="border" size="sm" />
                      </div>
                    )}
                    {products.length > 0 && (
                      <div className="position-absolute start-0 w-100 shadow bg-white rounded" style={{ zIndex: 1000 }}>
                        <ul className="list-group">
                          {products.map(product => (
                            <li
                              key={product.id}
                              className="list-group-item list-group-item-action"
                              style={{ cursor: 'pointer' }}
                              onClick={() => handleSelectProduct(product)}
                            >
                              {product.name} - {formatPrice(product.price)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Form.Group>
              </Col>
              <Col md={3}>
                <Form.Group>
                  <Form.Label>Количество</Form.Label>
                  <Form.Control
                    type="number"
                    min="1"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    disabled={!selectedProduct}
                  />
                </Form.Group>
              </Col>
              <Col md={4} className="d-flex align-items-end">
                <Button 
                  variant="primary" 
                  onClick={handleAddProduct} 
                  disabled={!selectedProduct}
                  className="mb-2"
                >
                  Добавить товар
                </Button>
              </Col>
            </Row>
            
            {selectedProduct && (
              <Alert variant="info" className="mb-3">
                Выбран товар: {selectedProduct.name} - {formatPrice(selectedProduct.price)}
              </Alert>
            )}
            
            {formData.items.length > 0 ? (
              <div className="table-responsive mb-4">
                <table className="table table-striped">
                  <thead>
                    <tr>
                      <th>Название</th>
                      <th>Цена</th>
                      <th>Количество</th>
                      <th>Сумма</th>
                      <th>Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {formData.items.map((item, index) => (
                      <tr key={index}>
                        <td>{item.product_name}</td>
                        <td>{formatPrice(item.price)}</td>
                        <td>
                          <Form.Control
                            type="number"
                            min="1"
                            value={item.quantity}
                            onChange={(e) => handleQuantityChange(index, e.target.value)}
                            size="sm"
                            style={{ width: '80px' }}
                            className="text-center"
                          />
                        </td>
                        <td>{formatPrice(item.price * item.quantity)}</td>
                        <td>
                          <Button 
                            variant="danger" 
                            size="sm"
                            onClick={() => handleRemoveProduct(index)}
                          >
                            Удалить
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th colSpan="3">Итого:</th>
                      <th>
                        {appliedPromoCode && discountAmount > 0 ? (
                          <>
                            <span style={{ textDecoration: 'line-through', color: '#999' }}>
                              {formatPrice(totalPrice)} ₽
                            </span>{' '}
                            <span className="text-success">
                              {formatPrice(totalPrice - discountAmount)} ₽
                            </span>
                          </>
                        ) : (
                          formatPrice(totalPrice)
                        )}
                      </th>
                      <th></th>
                    </tr>
                    {appliedPromoCode && discountAmount > 0 && (
                      <tr>
                        <td colSpan="3" className="text-end text-success">
                          <strong>Скидка по промокоду:</strong>
                        </td>
                        <td className="text-success">
                          <strong>-{formatPrice(discountAmount)} ₽</strong>
                        </td>
                        <td></td>
                      </tr>
                    )}
                  </tfoot>
                </table>
              </div>
            ) : (
              <Alert variant="warning" className="mb-4">
                Добавьте хотя бы один товар в заказ
              </Alert>
            )}
            
            <h5 className="mb-3 mt-4">Статус и оплата</h5>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Статус заказа</Form.Label>
                  <Form.Select
                    name="status_id"
                    value={formData.status_id}
                    onChange={handleChange}
                  >
                    {statuses.map(status => (
                      <option key={status.id} value={status.id}>
                        {status.name}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3 mt-4">
                  <Form.Check
                    type="checkbox"
                    id="is_paid"
                    name="is_paid"
                    label="Заказ оплачен"
                    checked={formData.is_paid}
                    onChange={handleChange}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <div className="d-flex justify-content-end mt-4">
              <Button variant="secondary" onClick={onClose} className="me-2">
                Отмена
              </Button>
              <Button 
                variant="primary" 
                type="submit" 
                disabled={loading || formData.items.length === 0}
              >
                {loading ? 'Создание заказа...' : 'Создать заказ'}
              </Button>
            </div>
          </Form>
    </Container>
  );
};

export default AdminOrderForm; 