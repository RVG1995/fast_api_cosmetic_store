import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Row, Col, Table, Badge, Button, Form, Alert, Spinner, Modal, Container } from 'react-bootstrap';
import { useOrders } from '../../context/OrderContext';
import { useAuth } from '../../context/AuthContext';
import { formatDateTime } from '../../utils/dateUtils';
import { formatPrice } from '../../utils/helpers';
import OrderStatusBadge from '../../components/OrderStatusBadge';
import axios from 'axios';
import { API_URLS } from '../../utils/constants';
import AdminBackButton from '../../components/common/AdminBackButton';
import { adminAPI } from '../../utils/api';
import BoxberryPickupModal from '../../components/cart/BoxberryPickupModal';

// Компонент для редактирования товаров в заказе
const OrderItemsEditor = ({ order, onOrderUpdated }) => {
  const { updateOrderItems, getAdminOrderById } = useOrders();
  const [availableProducts, setAvailableProducts] = useState([]);
  const [dropdownProducts, setDropdownProducts] = useState([]);  // Продукты для выпадающего списка
  const [searchResults, setSearchResults] = useState([]);       // Результаты текстового поиска
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [error, setError] = useState(null);
  const debounceTimeoutRef = useRef(null);
  const searchContainerRef = useRef(null);
  const searchInputRef = useRef(null);
  
  // Локальное состояние для редактирования товаров
  const [itemsToAdd, setItemsToAdd] = useState([]);
  const [itemsToUpdate, setItemsToUpdate] = useState({});
  const [itemsToRemove, setItemsToRemove] = useState([]);
  
  // Состояние для нового товара
  const [newProduct, setNewProduct] = useState({
    product_id: "",
    quantity: 1
  });
  
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  
  // Загрузка списка доступных товаров
  const loadAvailableProducts = useCallback(async () => {
    try {
      setLoadingProducts(true);
      const response = await axios.get(`${API_URLS.PRODUCT_SERVICE}/products/admin`, {
        params: { page: 1, limit: 100 },
        withCredentials: true
      });
      
      // Фильтруем все продукты сразу:
      // 1. Исключаем товары, которых нет в наличии (stock === 0)
      // 2. Исключаем товары, которые уже есть в заказе
      const products = response.data.items || [];
      const filteredProducts = products.filter(product => 
        product.stock > 0 && !order?.items.some(item => item.product_id === product.id)
      );
      
      setAvailableProducts(filteredProducts);
      setDropdownProducts(filteredProducts);
    } catch (err) {
      console.error("Ошибка при загрузке товаров:", err);
      setError("Не удалось загрузить список доступных товаров");
    } finally {
      setLoadingProducts(false);
    }
  }, [order?.items]);
  
  // Локальная фильтрация товаров
  const filterProductsLocally = useCallback((query) => {
    if (availableProducts.length === 0) return [];
    
    const lowercaseQuery = query.toLowerCase();
    return availableProducts.filter(product => 
      product.name.toLowerCase().includes(lowercaseQuery) || 
      (product.sku && product.sku.toLowerCase().includes(lowercaseQuery)) ||
      product.id.toString().includes(lowercaseQuery)
    );
  }, [availableProducts]);
  
  // Поиск товаров через API
  const searchProductsFromApi = useCallback(async (query) => {
    setLoadingProducts(true);
    try {
      const response = await axios.get(`${API_URLS.PRODUCT_SERVICE}/products/search`, {
        params: { name: query },
        withCredentials: true
      });
      
      const apiProducts = response.data || [];
      
      // Фильтруем продукты:
      // 1. Исключаем товары, которых нет в наличии (stock === 0)
      // 2. Исключаем товары, которые уже есть в заказе
      const filteredApiProducts = apiProducts.filter(apiProduct => 
        apiProduct.stock > 0 && !order?.items.some(item => item.product_id === apiProduct.id)
      );
      
      setSearchResults(filteredApiProducts);
      setShowSearchResults(true);
    } catch (error) {
      console.error('Ошибка при поиске товаров через API:', error);
      // Если API не отвечает, используем локальную фильтрацию
      const localResults = filterProductsLocally(query);
      setSearchResults(localResults);
      setShowSearchResults(localResults.length > 0);
    } finally {
      setLoadingProducts(false);
    }
  }, [order?.items, filterProductsLocally]);
  
  // Загрузка доступных товаров при открытии редактора
  useEffect(() => {
    if (showModal) {
      loadAvailableProducts();
    }
  }, [showModal, loadAvailableProducts]);
  
  // Обработчик клика вне компонента поиска
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setShowSearchResults(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);
  
  // handleSearchChange теперь читает значение напрямую из ref
  const handleSearchChange = useCallback(() => {
    const value = searchInputRef.current ? searchInputRef.current.value : '';
    if (debounceTimeoutRef.current) clearTimeout(debounceTimeoutRef.current);
    if (!value.trim()) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }
    debounceTimeoutRef.current = setTimeout(() => {
      if (value.length >= 3) {
        searchProductsFromApi(value);
      } else {
        const localResults = filterProductsLocally(value);
        setSearchResults(localResults);
        setShowSearchResults(localResults.length > 0);
      }
    }, 300);
  }, [searchProductsFromApi, filterProductsLocally]);
  
  const handleClearSearch = () => {
    if (searchInputRef.current) searchInputRef.current.value = '';
    setSearchResults([]);
    setShowSearchResults(false);
  };
  
  const handleSelectSearchResult = (product) => {
    setNewProduct({
      ...newProduct,
      product_id: product.id.toString()
    });
    setShowSearchResults(false);
    if (searchInputRef.current) searchInputRef.current.focus();
  };
  
  // Обработчик изменения количества товара
  const handleQuantityChange = (itemId, newQuantity) => {
    // Проверяем, что количество корректное
    if (newQuantity <= 0) return;
    
    // Находим оригинальное количество
    const originalItem = order?.items.find(item => item.id === itemId);
    if (!originalItem) return;
    
    // Если количество не изменилось, удаляем из списка обновлений
    if (originalItem.quantity === newQuantity) {
      const updatedItems = { ...itemsToUpdate };
      delete updatedItems[itemId];
      setItemsToUpdate(updatedItems);
    } else {
      // Иначе добавляем в список обновлений
      setItemsToUpdate({
        ...itemsToUpdate,
        [itemId]: newQuantity
      });
    }
  };
  
  // Обработчик удаления товара
  const handleRemoveItem = (itemId) => {
    // Проверяем, был ли товар добавлен в рамках текущего редактирования
    if (itemsToAdd.some(item => item.temp_id === itemId)) {
      // Если да, просто удаляем из списка добавлений
      setItemsToAdd(itemsToAdd.filter(item => item.temp_id !== itemId));
    } else {
      // Если это существующий товар, добавляем в список удалений и удаляем из обновлений, если там есть
      setItemsToRemove([...itemsToRemove, itemId]);
      const updatedItems = { ...itemsToUpdate };
      delete updatedItems[itemId];
      setItemsToUpdate(updatedItems);
    }
  };
  
  // Обработчик добавления нового товара
  const handleAddNewProduct = () => {
    if (!newProduct.product_id || newProduct.quantity <= 0) {
      setError("Выберите товар и укажите корректное количество");
      return;
    }
    
    // Проверяем, выбран ли продукт
    let selectedProduct;
    
    // Сначала ищем в результатах поиска
    if (searchResults.length > 0) {
      selectedProduct = searchResults.find(p => p.id.toString() === newProduct.product_id);
    }
    
    // Если не найден в результатах поиска, ищем в общем списке
    if (!selectedProduct) {
      selectedProduct = availableProducts.find(p => p.id.toString() === newProduct.product_id);
    }
    
    if (!selectedProduct) {
      setError("Выбранный товар не найден");
      return;
    }
    
    // Проверяем, есть ли товар в заказе
    const existingInOrder = order?.items.find(item => item.product_id === parseInt(newProduct.product_id));
    if (existingInOrder) {
      setError(`Товар "${selectedProduct.name}" уже есть в заказе`);
      return;
    }
    
    // Проверяем, есть ли товар в списке добавлений
    const existingInAdd = itemsToAdd.find(item => item.product_id === parseInt(newProduct.product_id));
    if (existingInAdd) {
      setError(`Товар "${selectedProduct.name}" уже добавлен в список`);
      return;
    }
    
    // Проверка наличия товара на складе
    if (selectedProduct.stock < newProduct.quantity) {
      setError(`Недостаточно товара на складе. Доступно: ${selectedProduct.stock}`);
      return;
    }
    
    // Создаем временный ID для нового товара
    const tempId = `temp_${Date.now()}`;
    
    // Добавляем товар в список добавлений
    setItemsToAdd([
      ...itemsToAdd,
      {
        temp_id: tempId,
        product_id: parseInt(newProduct.product_id),
        quantity: parseInt(newProduct.quantity),
        product_name: selectedProduct.name,
        product_price: selectedProduct.price,
        total_price: selectedProduct.price * parseInt(newProduct.quantity)
      }
    ]);
    
    // Сбрасываем форму
    setNewProduct({
      product_id: "",
      quantity: 1
    });
    
    // Сбрасываем поиск
    setSearchResults([]);
    setShowSearchResults(false);
    
    // Сбрасываем ошибку
    setError(null);
  };
  
  // Обработчик сохранения изменений
  const handleSaveChanges = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log("Начинаем обновление товаров заказа ID:", order?.id);
      
      // Формируем данные для запроса
      const updateData = {
        items_to_add: itemsToAdd.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity
        })),
        items_to_update: itemsToUpdate,
        items_to_remove: itemsToRemove
      };
      
      // Проверяем, есть ли изменения
      const hasChanges = 
        updateData.items_to_add.length > 0 || 
        Object.keys(updateData.items_to_update).length > 0 || 
        updateData.items_to_remove.length > 0;
      
      if (!hasChanges) {
        setError("Нет изменений для сохранения");
        setLoading(false);
        return;
      }
      
      console.log("Отправляем обновления:", updateData);
      
      // Отправляем запрос
      const result = await updateOrderItems(order?.id, updateData);
      console.log("Получен результат обновления:", result);
      
      if (result && result.success) {
        console.log("Обновление успешно, обновляем интерфейс");
        
        // Из-за кэширования на бэкенде result.order может содержать устаревшие данные
        // Явно запрашиваем актуальные данные заказа
        console.log("Запрашиваем актуальное состояние заказа после обновления");
        const freshOrderData = await getAdminOrderById(order?.id);
        
        if (freshOrderData) {
          console.log("Получены свежие данные заказа:", freshOrderData);
          // Обновляем данные в родительском компоненте
          if (onOrderUpdated) {
            onOrderUpdated(freshOrderData);
          }
        } else {
          // В случае ошибки запроса используем данные из первого ответа
          console.warn("Не удалось получить свежие данные, используем данные из ответа");
          if (onOrderUpdated && result.order) {
            onOrderUpdated(result.order);
          }
        }
        
        // Очищаем состояние
        setItemsToAdd([]);
        setItemsToUpdate({});
        setItemsToRemove([]);
        
        // Закрываем редактор
        setShowModal(false);
      } else {
        console.error("Ошибка при обновлении товаров:", result);
        setError(result?.errors?.message || "Не удалось обновить товары в заказе");
      }
    } catch (err) {
      console.error("Ошибка при обновлении товаров:", err);
      
      if (err.response) {
        console.error("Ответ сервера:", err.response.data);
        setError(err.response.data?.detail || "Ошибка при обновлении товаров");
      } else {
        setError(err.message || "Произошла ошибка при обновлении товаров");
      }
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    console.log('OrderItemsEditor mounted');
    return () => console.log('OrderItemsEditor unmounted');
  }, []);
  
  if (!order) return <Spinner animation="border" size="sm" />;
  
  return (
    <>
      <Button 
        variant="primary" 
        className="mb-3" 
        onClick={() => setShowModal(true)}
      >
        Редактировать товары
      </Button>
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
        <Modal.Header closeButton>
          <Modal.Title>Редактирование товаров в заказе</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {error && (
            <Alert variant="danger" className="mb-3">
              {error}
            </Alert>
          )}
          <Card className="mb-3">
            <Card.Header>Добавить товар</Card.Header>
            <Card.Body>
              <Row>
                <Col md={7}>
                  <div className="position-relative">
                    <input
                      ref={searchInputRef}
                      type="text"
                      className="form-control"
                      placeholder="Введите название товара, SKU или ID"
                      autoComplete="off"
                      style={{ zIndex: 2 }}
                      onChange={handleSearchChange}
                    />
                    {searchInputRef.current && searchInputRef.current.value && (
                      <button
                        className="btn btn-sm position-absolute end-0 top-50 translate-middle-y bg-transparent border-0"
                        onClick={handleClearSearch}
                        style={{ zIndex: 5, right: "30px" }}
                        tabIndex={-1}
                      >
                        <i className="bi bi-x-circle"></i>
                      </button>
                    )}
                    {loadingProducts && (
                      <div className="position-absolute end-0 top-50 translate-middle-y me-2">
                        <Spinner animation="border" size="sm" />
                      </div>
                    )}
                    {showSearchResults && searchResults.length > 0 && (
                      <div className="position-absolute w-100 mt-1 border rounded bg-white shadow-sm" style={{ zIndex: 1000, maxHeight: "300px", overflowY: "auto" }}>
                        {searchResults.map(product => (
                          <div
                            key={product.id}
                            className="p-2 border-bottom search-result-item"
                            onClick={() => handleSelectSearchResult(product)}
                            style={{ cursor: "pointer" }}
                          >
                            <div className="d-flex align-items-center">
                              <div className="me-2" style={{ width: "40px", height: "40px" }}>
                                {product.image ? (
                                  <img
                                    src={`${API_URLS.PRODUCT_SERVICE}${product.image}`}
                                    alt={product.name}
                                    className="img-fluid"
                                    style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
                                  />
                                ) : (
                                  <div className="bg-light d-flex align-items-center justify-content-center" style={{ width: "100%", height: "100%" }}>
                                    <i className="bi bi-image"></i>
                                  </div>
                                )}
                              </div>
                              <div>
                                <div className="fw-bold">{product.name}</div>
                                <div className="small text-muted">
                                  ID: {product.id} | {formatPrice(product.price)} | Остаток: {product.stock}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {showSearchResults && searchInputRef.current && searchInputRef.current.value && searchResults.length === 0 && !loadingProducts && (
                      <div className="position-absolute w-100 mt-1 border rounded bg-white shadow-sm p-3 text-center text-muted" style={{ zIndex: 1000 }}>
                        <i className="bi bi-search me-2"></i>
                        Товары не найдены
                      </div>
                    )}
                  </div>
                  <Form.Group className="mb-2">
                    <Form.Label>Выбор из списка</Form.Label>
                    <Form.Select
                      value={newProduct.product_id}
                      onChange={(e) => setNewProduct({...newProduct, product_id: e.target.value})}
                      disabled={loadingProducts}
                    >
                      <option value="">Выберите товар</option>
                      {dropdownProducts.map(product => (
                        <option key={product.id} value={product.id}>
                          {product.name} (ID: {product.id}, {formatPrice(product.price)}, остаток: {product.stock})
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={3}>
                  <Form.Group className="mb-2">
                    <Form.Label>Количество</Form.Label>
                    <Form.Control
                      type="number"
                      min="1"
                      value={newProduct.quantity}
                      onChange={(e) => setNewProduct({...newProduct, quantity: parseInt(e.target.value) || 1})}
                    />
                  </Form.Group>
                </Col>
                <Col md={2} className="d-flex align-items-end">
                  <Button 
                    variant="success" 
                    className="mb-2 w-100"
                    onClick={handleAddNewProduct}
                    disabled={!newProduct.product_id || newProduct.quantity <= 0 || loadingProducts}
                  >
                    Добавить
                  </Button>
                </Col>
              </Row>
            </Card.Body>
          </Card>
          <Table responsive hover>
            <thead>
              <tr>
                <th>ID</th>
                <th>Наименование</th>
                <th>Цена</th>
                <th>Количество</th>
                <th>Сумма</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {/* Новые товары для добавления - всегда сверху */}
              {itemsToAdd.map(item => (
                <tr key={item.temp_id} className="table-success">
                  <td>{item.product_id}</td>
                  <td>{item.product_name} <Badge bg="success">Новый</Badge></td>
                  <td>{formatPrice(item.product_price)}</td>
                  <td>
                    <Form.Control
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => {
                        const newQty = parseInt(e.target.value) || 1;
                        setItemsToAdd(itemsToAdd.map(i => 
                          i.temp_id === item.temp_id 
                            ? {...i, quantity: newQty, total_price: newQty * i.product_price} 
                            : i
                        ));
                      }}
                      style={{ width: '80px' }}
                    />
                  </td>
                  <td>{formatPrice(item.quantity * item.product_price)}</td>
                  <td>
                    <Button 
                      variant="danger" 
                      size="sm"
                      onClick={() => handleRemoveItem(item.temp_id)}
                    >
                      Удалить
                    </Button>
                  </td>
                </tr>
              ))}
              
              {/* Существующие товары в заказе без фильтрации, но с разной отрисовкой в зависимости от статуса */}
              {order.items.map(item => {
                const isRemoved = itemsToRemove.includes(item.id);
                return (
                  <tr key={item.id} className={isRemoved ? 'table-danger' : ''}>
                    <td>{item.product_id}</td>
                    <td>
                      {item.product_name}
                      {isRemoved && <Badge bg="danger" className="ms-2">Удален</Badge>}
                    </td>
                    <td>{formatPrice(item.product_price)}</td>
                    <td>
                      {isRemoved ? (
                        item.quantity
                      ) : (
                        <Form.Control
                          type="number"
                          min="1"
                          value={itemsToUpdate[item.id] || item.quantity}
                          onChange={(e) => handleQuantityChange(item.id, parseInt(e.target.value) || 1)}
                          style={{ width: '80px' }}
                        />
                      )}
                    </td>
                    <td>{formatPrice((itemsToUpdate[item.id] || item.quantity) * item.product_price)}</td>
                    <td>
                      {isRemoved ? (
                        <Button 
                          variant="secondary" 
                          size="sm"
                          onClick={() => setItemsToRemove(itemsToRemove.filter(id => id !== item.id))}
                        >
                          Восстановить
                        </Button>
                      ) : (
                        <Button 
                          variant="danger" 
                          size="sm"
                          onClick={() => handleRemoveItem(item.id)}
                        >
                          Удалить
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
          <div className="d-flex justify-content-end gap-2 mt-3">
            <Button variant="secondary" onClick={() => setShowModal(false)}>
              Закрыть
            </Button>
            <Button variant="primary" onClick={handleSaveChanges} disabled={loading}>
              {loading ? <Spinner as="span" animation="border" size="sm" role="status" aria-hidden="true" /> : 'Сохранить изменения'}
            </Button>
          </div>
        </Modal.Body>
      </Modal>
    </>
  );
};

const AdminOrderDetail = () => {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const { 
    getAdminOrderById, 
    updateOrderStatus,
    updateOrderPaymentStatus,
    loading: contextLoading, 
    error: contextError 
  } = useOrders();
  const { user } = useAuth();
  
  const [order, setOrder] = useState(null);
  const [statuses, setStatuses] = useState([]);
  const [selectedStatus, setSelectedStatus] = useState('');
  const [statusNote, setStatusNote] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [paymentUpdateSuccess, setPaymentUpdateSuccess] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [updateData, setUpdateData] = useState({
    delivery_type: '',
    boxberry_point_address: ''
  });
  const [showDeliveryForm, setShowDeliveryForm] = useState(false);
  const [deliveryData, setDeliveryData] = useState({
    delivery_type: '',
    delivery_address: ''
  });
  const [updateDeliveryLoading, setUpdateDeliveryLoading] = useState(false);
  const [updateDeliverySuccess, setUpdateDeliverySuccess] = useState(false);
  const [updateDeliveryError, setUpdateDeliveryError] = useState(null);
  const [showBoxberryModal, setShowBoxberryModal] = useState(false);
  const [selectedPickupPoint, setSelectedPickupPoint] = useState(null);
  
  // Обработчик выбора пункта выдачи BoxBerry
  const handlePickupPointSelected = (point) => {
    setSelectedPickupPoint(point);
    setDeliveryData({
      ...deliveryData,
      delivery_address: point.Address
    });
  };
  
  // Нужно ли показывать кнопку выбора пункта выдачи
  const isBoxberryPickupPoint = deliveryData.delivery_type === 'boxberry_pickup_point';
  
  // useEffect для инициализации формы данными из заказа при открытии
  useEffect(() => {
    if (showDeliveryForm && order) {
      setDeliveryData({
        delivery_type: order.delivery_type || '',
        delivery_address: order.delivery_address || ''
      });
      setSelectedPickupPoint(null);
    }
  }, [showDeliveryForm, order]);
  
  // Загрузка деталей заказа и статусов
  useEffect(() => {
    const loadData = async () => {
      try {
        console.log('=== ДИАГНОСТИКА ЗАГРУЗКИ ЗАКАЗА АДМИНИСТРАТОРОМ ===');
        console.log('ID заказа:', orderId);
        console.log('Пользователь:', user);
        
        // Проверяем авторизацию пользователя
        if (!user) {
          console.error('Пользователь не авторизован');
          setLoadError('Для доступа к информации о заказе необходима авторизация');
          return;
        }
        
        // Проверка прав администратора
        const isAdmin = user?.is_admin || user?.is_super_admin;
        
        if (!isAdmin) {
          console.error('Пользователь не является администратором');
          setLoadError('Доступ запрещен. Для просмотра этой страницы необходимы права администратора');
          return;
        }
        
        // Напрямую вызываем axios вместо getAdminOrderById для диагностики
        console.log('===== НАЧАЛО ЗАПРОСА ЗАКАЗА АДМИНИСТРАТОРОМ =====');
        
        const config = {
          withCredentials: true,
          headers: {
            'Content-Type': 'application/json'
          }
        };
        
        const orderUrl = `${API_URLS.ORDER_SERVICE}/admin/orders/${orderId}`;
        console.log('URL запроса заказа:', orderUrl);
        console.log('Конфигурация:', JSON.stringify(config));
        
        // Выполняем запрос заказа
        const orderResponse = await axios.get(orderUrl, config);
        console.log('Ответ от сервера (заказ):', orderResponse.status);
        console.log('Данные заказа:', orderResponse.data);
        
        // Устанавливаем данные заказа
        setOrder(orderResponse.data);
        
        // Загружаем статусы заказов
        const statusesUrl = `${API_URLS.ORDER_SERVICE}/order-statuses`;
        console.log('URL запроса статусов:', statusesUrl);
        
        const statusesResponse = await axios.get(statusesUrl, { withCredentials: true });
        console.log('Ответ от сервера (статусы):', statusesResponse.status);
        console.log('Данные статусов:', statusesResponse.data);
        
        // Устанавливаем статусы
        setStatuses(statusesResponse.data || []);
        
        // Если у заказа есть статус, устанавливаем его как выбранный
        if (orderResponse.data && orderResponse.data.status && orderResponse.data.status.id) {
          setSelectedStatus(orderResponse.data.status.id.toString());
        }
      } catch (err) {
        console.error('===== ОШИБКА ЗАПРОСА ЗАКАЗА АДМИНИСТРАТОРОМ =====');
        console.error('Имя ошибки:', err.name);
        console.error('Сообщение ошибки:', err.message);
        
        if (err.response) {
          console.error('Статус ошибки:', err.response.status);
          console.error('Данные ошибки:', err.response.data);
          
          if (err.response.status === 401) {
            setLoadError('Для доступа к заказу необходима авторизация');
          } else if (err.response.status === 403) {
            setLoadError('У вас нет прав для просмотра этого заказа');
          } else if (err.response.status === 404) {
            setLoadError('Заказ не найден');
          } else {
            setLoadError(`Ошибка сервера: ${err.response?.data?.detail || 'Неизвестная ошибка'}`);
          }
        } else if (err.request) {
          console.error('Запрос был отправлен, но ответ не получен:', err.request);
          setLoadError('Не удалось получить ответ от сервера. Проверьте подключение к интернету');
        } else {
          setLoadError(`Ошибка при загрузке заказа: ${err.message}`);
        }
        setLoading(false);
      }
    };

    loadData();
  }, [orderId, user]);
  
  // Если произошла локальная ошибка загрузки
  if (loadError) {
    return (
      <Container className="py-5">
        <Alert variant="danger">
          {loadError}
        </Alert>
        <AdminBackButton 
          to="/admin/orders" 
          label="Вернуться к списку заказов" 
          className="mt-3"
        />
      </Container>
    );
  }
  
  // Обработчик изменения статуса заказа
  const handleStatusChange = (e) => {
    setSelectedStatus(e.target.value);
  };
  
  // Обработчик изменения примечания к статусу
  const handleNoteChange = (e) => {
    setStatusNote(e.target.value);
  };
  
  // Открытие модального окна для подтверждения изменения статуса
  const handleOpenModal = () => {
    if (!selectedStatus) return;
    
    // Проверяем, не пытается ли пользователь выбрать текущий статус
    if (order && order.status && selectedStatus === order.status.id.toString()) {
      setError('Заказ уже имеет данный статус');
      setTimeout(() => setError(null), 3000);
      return;
    }
    
    setShowModal(true);
  };
  
  // Закрытие модального окна
  const handleCloseModal = () => {
    setShowModal(false);
  };
  
  // Обработчик подтверждения изменения статуса
  const handleConfirmStatusUpdate = async () => {
    try {
      setLoading(true);
      
      // Формируем данные для обновления в соответствии со схемой API
      const updateData = {
        status_id: parseInt(selectedStatus)
      };
      
      // Если есть примечание, добавляем его как комментарий
      if (statusNote) {
        updateData.comment = statusNote;
      }
      
      // Выполняем запрос на обновление статуса заказа
      const result = await updateOrderStatus(orderId, updateData);
      
      if (result) {
        // Обновление данных заказа после изменения статуса
        const updatedOrder = await getAdminOrderById(orderId);
        
        setOrder(updatedOrder);
        setUpdateSuccess(true);
        setTimeout(() => setUpdateSuccess(false), 3000);
      } else {
        setError('Не удалось обновить статус заказа');
      }
      
      setShowModal(false);
    } catch (err) {
      console.error('Ошибка при обновлении статуса заказа:', err);
      
      if (err.response) {
        console.error('Статус ошибки:', err.response.status);
        console.error('Данные ошибки:', err.response.data);
      }
      
      setError(err.response?.data?.detail || 'Не удалось обновить статус заказа');
    } finally {
      setLoading(false);
    }
  };
  
  // Обработчик открытия модального окна для изменения статуса оплаты
  const handleOpenPaymentModal = () => {
    setShowPaymentModal(true);
  };
  
  // Обработчик закрытия модального окна для изменения статуса оплаты
  const handleClosePaymentModal = () => {
    setShowPaymentModal(false);
  };
  
  // Обработчик подтверждения изменения статуса оплаты
  const handleConfirmPaymentUpdate = async (isPaid) => {
    try {
      setLoading(true);
      
      // Выполняем запрос на обновление статуса оплаты заказа
      const result = await updateOrderPaymentStatus(orderId, isPaid);
      
      if (result) {
        // Обновление данных заказа после изменения статуса оплаты
        const updatedOrder = await getAdminOrderById(orderId);
        
        setOrder(updatedOrder);
        setPaymentUpdateSuccess(true);
        setTimeout(() => setPaymentUpdateSuccess(false), 3000);
      } else {
        setError('Не удалось обновить статус оплаты заказа');
      }
      
      setShowPaymentModal(false);
    } catch (err) {
      console.error('Ошибка при обновлении статуса оплаты заказа:', err);
      
      if (err.response) {
        console.error('Статус ошибки:', err.response.status);
        console.error('Данные ошибки:', err.response.data);
      }
      
      setError(err.response?.data?.detail || 'Не удалось обновить статус оплаты заказа');
    } finally {
      setLoading(false);
    }
  };
  
  // Проверка, можно ли редактировать товары в заказе
  const canEditItems = () => {
    if (!order || !order.status) return false;
    
    // Запрещаем редактирование для определенных статусов и для оплаченных заказов
    const nonEditableStatuses = ['Отправлен', 'Доставлен', 'Отменен', 'Оплачен'];
    return !nonEditableStatuses.includes(order.status.name) && !order.is_paid;
  };
  
  // Если заказ не загружен, показываем индикатор загрузки
  if ((loading || contextLoading) && !order) {
    return (
      <Container className="py-5 text-center">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </Spinner>
      </Container>
    );
  }
  
  // Если произошла ошибка, показываем сообщение
  if ((error || contextError) && !order) {
    const errorMessage = error || contextError;
    return (
      <Container className="py-5">
        <Alert variant="danger">
          {typeof errorMessage === 'object' ? JSON.stringify(errorMessage) : (errorMessage || 'Произошла ошибка при загрузке данных заказа')}
        </Alert>
        <AdminBackButton 
          to="/admin/orders" 
          label="Вернуться к списку заказов" 
          className="mt-3"
        />
      </Container>
    );
  }
  
  // Если заказ всё ещё не загружен, показываем индикатор загрузки
  if (!order) {
    return (
      <Container className="py-5 text-center">
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Загрузка данных заказа...</span>
        </Spinner>
        <AdminBackButton 
          to="/admin/orders" 
          label="Вернуться к списку заказов" 
          className="mt-3"
        />
      </Container>
    );
  }
  
  // Функция для форматирования типа доставки
  const formatDeliveryType = (type) => {
    if (!type) return 'Не указан';
    
    switch(type) {
      case 'boxberry_pickup_point':
        return 'Пункт выдачи BoxBerry';
      case 'boxberry_courier':
        return 'Курьер BoxBerry';
      case 'cdek_pickup_point':
        return 'Пункт выдачи СДЭК';
      case 'cdek_courier':
        return 'Курьер СДЭК';
      default:
        return type;
    }
  };
  
  const handleUpdateDelivery = async () => {
    setUpdateDeliveryLoading(true);
    setUpdateDeliveryError(null);
    
    try {
      console.log("Начинаем обновление информации о доставке заказа ID:", order?.id);
      
      // Формируем данные для запроса
      const updateData = {
        delivery_type: deliveryData.delivery_type,
        delivery_address: deliveryData.delivery_address
      };
      
      // Проверяем, есть ли изменения
      const hasChanges = 
        updateData.delivery_type !== order.delivery_type ||
        updateData.delivery_address !== order.delivery_address;
      
      if (!hasChanges) {
        setUpdateDeliveryError("Нет изменений для сохранения");
        setUpdateDeliveryLoading(false);
        return;
      }
      
      // Проверяем, что все обязательные поля заполнены
      if (!updateData.delivery_type) {
        setUpdateDeliveryError("Выберите тип доставки");
        setUpdateDeliveryLoading(false);
        return;
      }
      
      if (!updateData.delivery_address) {
        setUpdateDeliveryError("Укажите адрес доставки");
        setUpdateDeliveryLoading(false);
        return;
      }
      
      // Дополнительно проверяем, что для доставки в пункт выдачи BoxBerry выбран пункт
      if (updateData.delivery_type === 'boxberry_pickup_point' && !selectedPickupPoint) {
        setUpdateDeliveryError("Выберите пункт выдачи BoxBerry");
        setUpdateDeliveryLoading(false);
        return;
      }
      
      console.log("Отправляем обновления:", updateData);
      
      // Отправляем запрос
      const result = await adminAPI.updateOrderDeliveryInfo(order?.id, updateData);
      console.log("Получен результат обновления:", result);
      
      // Обновляем заказ в компоненте
      if (result) {
        // Запрашиваем актуальное состояние заказа после обновления
        const updatedOrder = await adminAPI.getOrderById(order?.id);
        if (updatedOrder) {
          setOrder(updatedOrder);
        }
        
        // Очищаем состояние
        setShowDeliveryForm(false);
        setUpdateDeliverySuccess(true);
        setTimeout(() => setUpdateDeliverySuccess(false), 3000);
      }
    } catch (err) {
      console.error("Ошибка при обновлении информации о доставке:", err);
      
      if (err.response) {
        console.error("Ответ сервера:", err.response.data);
        setUpdateDeliveryError(err.response.data?.detail || "Ошибка при обновлении информации о доставке");
      } else {
        setUpdateDeliveryError(err.message || "Произошла ошибка при обновлении информации о доставке");
      }
    } finally {
      setUpdateDeliveryLoading(false);
    }
  };
  
  return (
    <Container className="py-4">
      <AdminBackButton to="/admin/orders" label="Вернуться к списку заказов" />
      <h2 className="mb-4">Информация о заказе #{order.id}</h2>
      
      {updateSuccess && (
        <Alert variant="success" className="mb-4">
          Статус заказа успешно обновлен!
        </Alert>
      )}
      
      {error && (
        <Alert variant="danger" className="mb-4">
          {error}
        </Alert>
      )}
      
      <Row>
        {/* Основная информация о заказе */}
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Информация о заказе</h5>
            </Card.Header>
            <Card.Body>
              <Row>
                <Col md={6}>
                  <p><strong>ID заказа:</strong> {order.order_number}</p>
                  <p><strong>Дата создания:</strong> {formatDateTime(order.created_at)}</p>
                  <p><strong>Статус:</strong> <OrderStatusBadge status={order.status} /></p>
                </Col>
                <Col md={6}>
                  <p><strong>ID пользователя:</strong> {order.user_id}</p>
                  <p><strong>Email:</strong> {order.email}</p>
                  <p><strong>Телефон:</strong> {order.phone || 'Не указан'}</p>
                  <p><strong>Сумма заказа:</strong> {formatPrice(order.total_price)}</p>
                  {order.discount_amount > 0 && (
                    <p><strong>Скидка:</strong> {formatPrice(order.discount_amount)}</p>
                  )}
                  {order.promo_code && (
                    <p><strong>Промокод:</strong> <Badge bg="success">{order.promo_code.code}</Badge> 
                      {order.promo_code.discount_percent ? 
                        <span className="ms-1">({order.promo_code.discount_percent}%)</span> : 
                        order.promo_code.discount_amount ? 
                          <span className="ms-1">({formatPrice(order.promo_code.discount_amount)})</span> : 
                          null}
                    </p>
                  )}
                </Col>
              </Row>
              
              {order.comment && (
                <div className="mt-3">
                  <h6>Комментарий к заказу:</h6>
                  <p className="bg-light p-2 rounded">{order.comment}</p>
                </div>
              )}
            </Card.Body>
          </Card>
          
          {/* Товары в заказе */}
          <Card className="mb-4">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Товары в заказе</h5>
              {canEditItems() ? (
                <OrderItemsEditor order={order} onOrderUpdated={setOrder} />
              ) : (
                <Badge bg="secondary">
                  {order.is_paid ? 
                    "Редактирование недоступно для оплаченных заказов" : 
                    `Редактирование недоступно для заказов в статусе "${order.status.name}"`}
                </Badge>
              )}
            </Card.Header>
            <Card.Body>
              <Table responsive hover>
                <thead>
                  <tr>
                    <th>ID товара</th>
                    <th>Наименование</th>
                    <th>Цена за ед.</th>
                    <th>Кол-во</th>
                    <th>Сумма</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map(item => (
                    <tr key={item.id}>
                      <td>{item.product_id}</td>
                      <td>{item.product_name}</td>
                      <td>{formatPrice(item.unit_price || item.product_price || 0)}</td>
                      <td>{item.quantity}</td>
                      <td>{formatPrice((item.unit_price || item.product_price || 0) * item.quantity)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan="4" className="text-end"><strong>Итого:</strong></td>
                    <td><strong>{formatPrice(order.total_price || order.total_amount || 0)}</strong></td>
                  </tr>
                  {order.discount_amount > 0 && (
                    <tr>
                      <td colSpan="4" className="text-end"><em>Скидка по промокоду {order.promo_code?.code && (
                        <span>
                          ({order.promo_code.code}
                          {order.promo_code.discount_percent && <span> - {order.promo_code.discount_percent}%</span>})
                        </span>
                      )}:</em></td>
                      <td>-{formatPrice(order.discount_amount)}</td>
                    </tr>
                  )}
                </tfoot>
              </Table>
            </Card.Body>
          </Card>
          
          {/* История статусов заказа */}
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">История статусов</h5>
            </Card.Header>
            <Card.Body>
              <div className="status-timeline">
                {order.status_history && order.status_history.length > 0 ? (
                  order.status_history.map((statusChange, index) => (
                    <div key={index} className="status-item mb-3">
                      <div className="d-flex justify-content-between">
                        <div>
                          <OrderStatusBadge status={statusChange.status} />
                        </div>
                        <small className="text-muted">
                          {formatDateTime(statusChange.changed_at || statusChange.timestamp)}
                        </small>
                      </div>
                      {statusChange.notes || statusChange.note ? (
                        <div className="status-note mt-1 bg-light p-2 rounded">
                          {statusChange.notes || statusChange.note}
                        </div>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <p>История статусов отсутствует</p>
                )}
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        {/* Боковая панель с адресом доставки и управлением статусом */}
        <Col md={4}>
          {/* Адрес доставки */}
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Информация о получателе</h5>
            </Card.Header>
            <Card.Body>
              <p><strong>Получатель:</strong> {order.full_name}</p>
              
              {/* Информация о типе доставки и адресе с возможностью редактирования */}
              <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h6 className="mb-0">Информация о доставке</h6>
                  <Button 
                    variant="outline-primary" 
                    size="sm"
                    onClick={() => setShowDeliveryForm(!showDeliveryForm)}
                    disabled={order.is_paid || (order.status && ["Отправлен", "Доставлен"].includes(order.status.name))}
                    title={
                      order.is_paid ? 
                        "Невозможно изменить информацию о доставке для оплаченного заказа" : 
                        order.status && ["Отправлен", "Доставлен"].includes(order.status.name) ?
                          `Невозможно изменить информацию о доставке для заказа в статусе "${order.status.name}"` :
                          "Изменить информацию о доставке"
                    }
                  >
                    {showDeliveryForm ? "Отменить" : "Изменить"}
                  </Button>
                </div>
                
                {(order.is_paid || (order.status && ["Отправлен", "Доставлен"].includes(order.status.name))) && !showDeliveryForm && (
                  <Alert variant="info" className="mb-3">
                    {order.is_paid ? 
                      "Нельзя изменить информацию о доставке, так как заказ уже оплачен" : 
                      `Нельзя изменить информацию о доставке для заказа в статусе "${order.status.name}"`}
                  </Alert>
                )}
                
                {showDeliveryForm ? (
                  <Form className="mt-3">
                    <Form.Group className="mb-3">
                      <Form.Label>Тип доставки</Form.Label>
                      <Form.Select 
                        value={deliveryData.delivery_type} 
                        onChange={(e) => setDeliveryData({...deliveryData, delivery_type: e.target.value})}
                      >
                        <option value="">Выберите тип доставки</option>
                        <option value="boxberry_pickup_point">BoxBerry - Пункт выдачи</option>
                        <option value="boxberry_courier">BoxBerry - Курьер</option>
                        <option value="cdek_pickup_point">CDEK - Пункт выдачи</option>
                        <option value="cdek_courier">CDEK - Курьер</option>
                      </Form.Select>
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Label>Адрес доставки</Form.Label>
                      <div className="d-flex">
                        <Form.Control 
                          type="text" 
                          value={deliveryData.delivery_address}
                          onChange={(e) => setDeliveryData({...deliveryData, delivery_address: e.target.value})}
                          placeholder="Введите адрес доставки"
                          readOnly={isBoxberryPickupPoint}
                          className={isBoxberryPickupPoint ? "bg-light" : ""}
                        />
                        {isBoxberryPickupPoint && (
                          <Button 
                            variant="outline-primary"
                            onClick={() => setShowBoxberryModal(true)}
                            className="ms-2"
                          >
                            Выбрать пункт
                          </Button>
                        )}
                      </div>
                    </Form.Group>
                    
                    {isBoxberryPickupPoint && selectedPickupPoint && (
                      <div className="mt-2 p-2 border rounded bg-light mb-3">
                        <p className="mb-1"><strong>{selectedPickupPoint.Name}</strong></p>
                        <p className="mb-1 small">{selectedPickupPoint.Address}</p>
                        <p className="mb-0 small text-muted">График работы: {selectedPickupPoint.WorkShedule}</p>
                      </div>
                    )}
                    
                    <div className="d-flex justify-content-end">
                      <Button 
                        variant="primary" 
                        size="sm" 
                        onClick={handleUpdateDelivery}
                        disabled={updateDeliveryLoading}
                      >
                        {updateDeliveryLoading ? (
                          <>
                            <Spinner as="span" animation="border" size="sm" />
                            <span className="ms-2">Сохранение...</span>
                          </>
                        ) : (
                          "Сохранить"
                        )}
                      </Button>
                    </div>
                    
                    {updateDeliverySuccess && (
                      <Alert variant="success" className="mt-3">
                        Информация о доставке успешно обновлена
                      </Alert>
                    )}
                    
                    {updateDeliveryError && (
                      <Alert variant="danger" className="mt-3">
                        {updateDeliveryError}
                      </Alert>
                    )}
                  </Form>
                ) : (
                  <>
                    <p>
                      <strong>Тип доставки:</strong>{' '}
                      {formatDeliveryType(order.delivery_type)}
                    </p>
                    <p>
                      <strong>Адрес доставки:</strong> {order.delivery_address || "Не указан"}
                    </p>
                  </>
                )}
              </div>
              
              <p><strong>Телефон:</strong> {order.phone || "Не указан"}</p>
              <p><strong>Email:</strong> {order.email}</p>
              <p>
                <strong>Согласие на обработку ПД:</strong>{' '}
                {order.personal_data_agreement !== undefined ? (
                  <Badge bg={order.personal_data_agreement ? "success" : "danger"}>
                    {order.personal_data_agreement ? "Дано" : "Не дано"}
                  </Badge>
                ) : (
                  <Badge bg="warning">Нет данных</Badge>
                )}
              </p>
            </Card.Body>
          </Card>
          
          {/* Управление статусом оплаты */}
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Статус оплаты</h5>
            </Card.Header>
            <Card.Body>
              <div className="d-flex justify-content-between align-items-center mb-3">
                <div>
                  <Badge bg={order.is_paid ? "success" : "danger"}>
                    {order.is_paid ? "Оплачен" : "Не оплачен"}
                  </Badge>
                </div>
                
                <Button 
                  variant={order.is_paid ? "outline-danger" : "outline-success"} 
                  size="sm"
                  onClick={handleOpenPaymentModal}
                  disabled={loading}
                >
                  {order.is_paid ? "Отметить как неоплаченный" : "Отметить как оплаченный"}
                </Button>
              </div>
              
              {paymentUpdateSuccess && (
                <Alert variant="success" className="mb-0">
                  Статус оплаты успешно обновлен
                </Alert>
              )}
            </Card.Body>
          </Card>
          
          {/* Управление статусом заказа */}
          <Card>
            <Card.Header>
              <h5 className="mb-0">Изменить статус</h5>
            </Card.Header>
            <Card.Body>
              <Form>
                <Form.Group className="mb-3">
                  <Form.Label>Новый статус</Form.Label>
                  <Form.Select
                    value={selectedStatus}
                    onChange={handleStatusChange}
                  >
                    <option value="">Выберите статус</option>
                    {statuses.map(status => (
                      <option 
                        key={status.id} 
                        value={status.id.toString()}
                        disabled={status.id.toString() === order.status.id.toString()}
                      >
                        {status.name}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Примечание (необязательно)</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={statusNote}
                    onChange={handleNoteChange}
                    placeholder="Добавьте примечание к изменению статуса"
                  />
                </Form.Group>
                
                <Button 
                  variant="primary" 
                  className="w-100"
                  disabled={!selectedStatus || loading}
                  onClick={handleOpenModal}
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
                      <span className="ms-2">Обновление...</span>
                    </>
                  ) : (
                    'Обновить статус'
                  )}
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {/* Модальное окно подтверждения изменения статуса */}
      <Modal show={showModal} onHide={handleCloseModal}>
        <Modal.Header closeButton>
          <Modal.Title>Подтверждение изменения статуса</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Вы уверены, что хотите изменить статус заказа на <strong>
            {statuses.find(s => s.id.toString() === selectedStatus)?.name || selectedStatus}
          </strong>?</p>
          {statuses.find(s => s.id.toString() === selectedStatus)?.name === 'Отменен' && (
            <Alert variant="warning">
              Внимание! Отмена заказа необратима. После отмены заказ не может быть восстановлен.
            </Alert>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleCloseModal}>
            Отмена
          </Button>
          <Button variant="primary" onClick={handleConfirmStatusUpdate}>
            Подтвердить
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Модальное окно подтверждения изменения статуса оплаты */}
      <Modal show={showPaymentModal} onHide={handleClosePaymentModal}>
        <Modal.Header closeButton>
          <Modal.Title>Подтверждение изменения статуса оплаты</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Вы уверены, что хотите изменить статус оплаты заказа на <strong>
            {order?.is_paid ? "Не оплачен" : "Оплачен"}
          </strong>?</p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={handleClosePaymentModal}>
            Отмена
          </Button>
          <Button 
            variant={order?.is_paid ? "danger" : "success"} 
            onClick={() => handleConfirmPaymentUpdate(!order?.is_paid)}
          >
            {order?.is_paid ? "Отметить как неоплаченный" : "Отметить как оплаченный"}
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Модальное окно выбора пункта выдачи BoxBerry */}
      <BoxberryPickupModal
        show={showBoxberryModal}
        onHide={() => setShowBoxberryModal(false)}
        onPickupPointSelected={handlePickupPointSelected}
        selectedAddress={deliveryData.delivery_address}
      />
    </Container>
  );
};

export default AdminOrderDetail; 