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
  
  // Получаем методы из контекста заказов
  const { getOrderStatuses, createAdminOrder } = useOrders();

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
    
    setSelectedProduct(null);
    setQuantity(1);
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

  // Вычисление общей суммы заказа
  const totalPrice = useMemo(() => {
    return formData.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  }, [formData.items]);

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
      
      // Обработка промокода - если пустой или меньше 3 символов, устанавливаем null
      if (!orderData.promo_code || orderData.promo_code.length < 3) {
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
      <Card>
        <Card.Header>
          <h4>Создание заказа</h4>
        </Card.Header>
        <Card.Body>
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
                  <Form.Control
                    type="text"
                    name="promo_code"
                    value={formData.promo_code}
                    onChange={handleChange}
                  />
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
                        <td>{item.quantity}</td>
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
                      <th>{formatPrice(totalPrice)}</th>
                      <th></th>
                    </tr>
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
        </Card.Body>
      </Card>
    </Container>
  );
};

export default AdminOrderForm; 