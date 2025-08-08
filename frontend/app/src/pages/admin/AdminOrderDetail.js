import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Table, Badge, Button, Form, Alert, Spinner, Modal, Container } from 'react-bootstrap';
import { useOrders } from '../../context/OrderContext';
import { useAuth } from '../../context/AuthContext';
import { formatDateTime } from '../../utils/dateUtils';
import { formatPrice } from '../../utils/helpers';
import OrderStatusBadge from '../../components/OrderStatusBadge';
import axios from 'axios';
import { adminAPI, deliveryAPI } from '../../utils/api';
import BoxberryPickupModal from '../../components/cart/BoxberryPickupModal';
import debounce from 'lodash/debounce';
import AdminBackButton from '../../components/common/AdminBackButton';
import { API_URLS } from '../../utils/constants';
import EditOrderModal from '../../components/admin/EditOrderModal';

// Компонент для редактирования товаров в заказе (не используется на странице деталей)
// Удалено из экспорта страницы для устранения предупреждений линтера
/* eslint-disable no-unused-vars */
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
                          <button
                            key={product.id}
                            type="button"
                            className="w-100 text-start p-2 border-0 bg-white border-bottom search-result-item"
                            onClick={() => handleSelectSearchResult(product)}
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
                          </button>
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
  const { user } = useAuth();
  const { 
    loading: contextLoading, 
    error: contextError, 
    getAdminOrderById, 
    updateOrderStatus,
    updateOrderPaymentStatus,
    createBoxberryParcel
  } = useOrders();
  
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
  const [deliveryData, setDeliveryData] = useState({
    delivery_type: '',
    delivery_address: ''
  });
  const [deliveryLoading, setDeliveryLoading] = useState(false);
  const [deliverySuccess, setDeliverySuccess] = useState(false);
  const [deliveryError, setDeliveryError] = useState(null);
  const [showBoxberryModal, setShowBoxberryModal] = useState(false);
  const [selectedPickupPoint, setSelectedPickupPoint] = useState(null);
  const [selectedAddressData, setSelectedAddressData] = useState(null); // Данные выбранного адреса DaData
  const [calculatedDeliveryCost, setCalculatedDeliveryCost] = useState(null);
  const [isPaymentOnDelivery, setIsPaymentOnDelivery] = useState(true);
  const [showDeliveryForm, setShowDeliveryForm] = useState(false);
  const [boxberryLoading, setBoxberryLoading] = useState(false);
  const [boxberryResult, setBoxberryResult] = useState(null);
  const [showBoxberryParcelModal, setShowBoxberryParcelModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  
  // Функция для расчета стоимости доставки при обновлении
  // Перенесена вверх и объявлена единожды
  // NOTE: duplicate definition existed ниже; используем только эту версию
  const calculateDeliveryCostForUpdate = useCallback(async (forcedPaymentOnDelivery = null) => {
    try {
      if (!deliveryData.delivery_type || !order.items || order.items.length === 0) {
        return null;
      }
      if (deliveryData.delivery_type === 'boxberry_pickup_point') {
        if (!selectedPickupPoint) {
          setDeliveryError('Для расчета стоимости доставки необходимо выбрать пункт выдачи');
          return null;
        }
      } else if (deliveryData.delivery_type === 'boxberry_courier') {
        if (!deliveryData.delivery_address) {
          setDeliveryError('Для расчета стоимости доставки необходимо указать адрес');
          return null;
        }
        if (!selectedAddressData || !selectedAddressData.postal_code) {
          setDeliveryError('Для расчета стоимости курьерской доставки необходим почтовый индекс. Выберите адрес из списка подсказок.');
          return null;
        }
      }
      const items = order.items.map(item => ({
        product_id: item.product_id,
        weight: item.product_weight || 500,
        width: item.product_width || 10,
        height: item.product_height || 10,
        depth: item.product_depth || 10,
        price: item.product_price,
        quantity: item.quantity
      }));
      let requestData = {
        items,
        delivery_type: deliveryData.delivery_type,
        is_payment_on_delivery: forcedPaymentOnDelivery !== null ? forcedPaymentOnDelivery : isPaymentOnDelivery
      };
      if (deliveryData.delivery_type === 'boxberry_pickup_point' && selectedPickupPoint) {
        requestData.pvz_code = selectedPickupPoint.Code;
      }
      if (deliveryData.delivery_type === 'boxberry_courier' && selectedAddressData) {
        requestData.zip_code = selectedAddressData.postal_code;
        requestData.city_name = selectedAddressData.city || '';
      }
      const response = await deliveryAPI.calculateDeliveryFromCart(requestData);
      setDeliveryError(null);
      setCalculatedDeliveryCost(response);
      return response;
    } catch (error) {
      if (error.response && error.response.data) {
        const errorDetail = error.response.data.detail;
        if (typeof errorDetail === 'string') {
          if (errorDetail.toLowerCase().includes('курьерская доставка') && 
              errorDetail.toLowerCase().includes('невозможна')) {
            setDeliveryError(`${errorDetail} Пожалуйста, выберите другой адрес или пункт выдачи.`);
          } else {
            setDeliveryError(`Ошибка: ${errorDetail}`);
          }
        } else {
          setDeliveryError(`Ошибка при расчете стоимости доставки: ${error.response?.status || 'неизвестная ошибка'}`);
        }
      } else {
        setDeliveryError(`Ошибка при расчете стоимости доставки: ${error.message || 'неизвестная ошибка'}`);
      }
      return null;
    }
  }, [deliveryData.delivery_type, deliveryData.delivery_address, order, selectedPickupPoint, selectedAddressData, isPaymentOnDelivery]);

  // Эффект для автоматического расчета стоимости доставки при открытии формы
  useEffect(() => {
    if (showDeliveryForm && order && deliveryData.delivery_type) {
      const canCalculate = (
        (deliveryData.delivery_type === 'boxberry_pickup_point' && selectedPickupPoint) ||
        (deliveryData.delivery_type === 'boxberry_courier' && selectedAddressData && selectedAddressData.postal_code)
      );
      if (canCalculate) {
        setDeliveryLoading(true);
        calculateDeliveryCostForUpdate()
          .finally(() => setDeliveryLoading(false));
      }
    }
  }, [showDeliveryForm, order, deliveryData.delivery_type, selectedPickupPoint, selectedAddressData, calculateDeliveryCostForUpdate]);
  const [addressOptions, setAddressOptions] = useState([]); // Добавляем состояние для подсказок адресов DaData
  
  // Добавляем функцию получения подсказок адресов DaData
  const fetchAddressSuggestions = useCallback(async (query) => {
    console.log('Dadata address fetch:', query);
    if (!query) {
      setAddressOptions([]);
      return;
    }
    try {
      const data = await deliveryAPI.getDadataAddressSuggestions(query);
      console.log('Dadata address resp:', data.suggestions);
      setAddressOptions(data.suggestions);
      
      // Убираем автоматический выбор лучшего совпадения,
      // теперь пользователь должен явно выбрать адрес из списка
    } catch(e) { 
      console.error('DaData address error', e); 
    }
  }, []);
  
  // Функция для выбора адреса из выпадающего списка
  const handleSelectAddress = (suggestion) => {
    console.log('Выбран адрес:', suggestion);
    
    setAddressOptions([]); // Закрываем выпадающий список
    
    // Устанавливаем данные выбранного адреса
    setSelectedAddressData({
      value: suggestion.value,
      postal_code: suggestion.data.postal_code,
      city: suggestion.data.city || suggestion.data.settlement,
      settlement: suggestion.data.settlement,
      street: suggestion.data.street,
      street_with_type: suggestion.data.street_with_type,
      house: suggestion.data.house,
      house_type: suggestion.data.house_type,
      house_type_full: suggestion.data.house_type_full,
      flat: suggestion.data.flat,
      flat_type: suggestion.data.flat_type,
      flat_type_full: suggestion.data.flat_type_full,
      block: suggestion.data.block,
      block_type: suggestion.data.block_type
    });
    
    // Обновляем адрес доставки
    setDeliveryData(prev => ({
      ...prev,
      delivery_address: suggestion.value
    }));
    
    // Запускаем расчет стоимости доставки, если тип доставки - курьерская BoxBerry и есть индекс
    if (deliveryData.delivery_type === 'boxberry_courier' && suggestion.data.postal_code) {
      setTimeout(async () => {
        try {
          setDeliveryLoading(true);
          await calculateDeliveryCostForUpdate();
        } catch (error) {
          console.error('Ошибка при расчете доставки после выбора адреса:', error);
        } finally {
          setDeliveryLoading(false);
        }
      }, 300);
    }
  };
  
  // Используем debounce для ввода адреса
  const debouncedFetchAddressSuggestions = useMemo(
    () => debounce((query) => fetchAddressSuggestions(query), 300),
    [fetchAddressSuggestions]
  );
  
  // Обработчик выбора пункта выдачи BoxBerry
  const handlePickupPointSelected = (point) => {
    setSelectedPickupPoint(point);
    setDeliveryData({
      ...deliveryData,
      delivery_address: point.Address
    });
    
    // После выбора пункта выдачи запускаем расчет стоимости доставки
    setDeliveryLoading(true);
    setTimeout(async () => {
      try {
        await calculateDeliveryCostForUpdate();
      } catch (err) {
        console.error('Ошибка при расчете стоимости доставки для ПВЗ:', err);
      } finally {
        setDeliveryLoading(false);
      }
    }, 300);
  };
  
  // Обработчик изменения адреса доставки
  const handleDeliveryAddressChange = async (e) => {
    const newAddress = e.target.value;
    setDeliveryData({
      ...deliveryData,
      delivery_address: newAddress
    });
    
    // Для курьерской доставки BoxBerry используем DaData
    if (deliveryData.delivery_type === 'boxberry_courier') {
      debouncedFetchAddressSuggestions(newAddress);
    }
  };
  
  // Обработчик изменения типа доставки
  const handleDeliveryTypeChange = (e) => {
    const newDeliveryType = e.target.value;
    
    // Если тип доставки меняется, сбрасываем расчет стоимости
    setCalculatedDeliveryCost(null);
    
    // Сбрасываем ошибки доставки при изменении типа
    setDeliveryError(null);
    
    // Обновляем тип доставки
    setDeliveryData({
      ...deliveryData,
      delivery_type: newDeliveryType,
      boxberry_point_id: null,
      boxberry_point_address: null
    });
    
    // Если выбран пункт выдачи BoxBerry и еще не выбран пункт,
    // предлагаем выбрать пункт выдачи
    if (newDeliveryType === 'boxberry_pickup_point') {
      // Если нет выбранного пункта, показываем сообщение
      if (!selectedPickupPoint) {
        // Сбрасываем адрес доставки
        setDeliveryData(prev => ({
          ...prev,
          delivery_type: newDeliveryType,
          delivery_address: '',
          boxberry_point_id: null,
          boxberry_point_address: null
        }));
      } else {
        // Если пункт выдачи уже выбран, пересчитываем стоимость доставки
        setTimeout(async () => {
          setDeliveryLoading(true);
          try {
            await calculateDeliveryCostForUpdate();
          } catch (err) {
            console.error('Ошибка при расчете стоимости доставки при смене типа на пункт выдачи:', err);
          } finally {
            setDeliveryLoading(false);
          }
        }, 300);
      }
    } else if (newDeliveryType === 'boxberry_courier') {
      // Если выбрана курьерская доставка, очищаем поле адреса и данные адреса
      setDeliveryData(prev => ({
        ...prev,
        delivery_type: newDeliveryType,
        delivery_address: '',
        boxberry_point_id: null,
        boxberry_point_address: null
      }));
      setSelectedAddressData(null);
      setAddressOptions([]);
      setSelectedPickupPoint(null);
      
      // Показываем подсказку для выбора адреса
      setDeliveryError('Для курьерской доставки необходимо выбрать адрес из списка подсказок');
      
      // Если уже есть выбранный адрес с почтовым индексом, пересчитываем стоимость
      if (selectedAddressData && selectedAddressData.postal_code) {
        setTimeout(async () => {
          setDeliveryLoading(true);
          try {
            await calculateDeliveryCostForUpdate();
          } catch (err) {
            console.error('Ошибка при расчете стоимости доставки при смене типа на курьерскую доставку:', err);
          } finally {
            setDeliveryLoading(false);
          }
        }, 300);
      }
    } else {
      // Для других типов доставки сбрасываем данные BoxBerry
      setSelectedPickupPoint(null);
    }
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
      
      // Инициализируем способ оплаты
      setIsPaymentOnDelivery(order.is_payment_on_delivery !== undefined ? order.is_payment_on_delivery : true);
      
      // Инициализируем данные о пункте выдачи, если это BoxBerry ПВЗ
      // Инициализируем данные о пункте выдачи, если это BoxBerry ПВЗ
      if (order.delivery_type === 'boxberry_pickup_point' && order.boxberry_point_id) {
        setSelectedPickupPoint({
          Code: order.boxberry_point_id.toString(),
          Address: order.boxberry_point_address || order.delivery_address,
          Name: 'Пункт выдачи BoxBerry'
        });
      } else {
        setSelectedPickupPoint(null);
      }
      
      // Инициализируем данные адреса из заказа
      const addressParts = order.delivery_address ? order.delivery_address.split(',') : [];
      let postalCode = null;
      
      // Пытаемся извлечь почтовый индекс из адреса
      for (const part of addressParts) {
        const trimmed = part.trim();
        if (/^\d{6}$/.test(trimmed)) { // Российский почтовый индекс имеет 6 цифр
          postalCode = trimmed;
          break;
        }
      }
      
      const addressData = {
        postal_code: postalCode,
        city: addressParts.length > 0 ? addressParts[0].trim() : '',
        full_address: order.delivery_address
      };
      
      setSelectedAddressData(addressData);
      
      // Если это курьерская доставка и есть почтовый индекс, сразу рассчитываем стоимость
      if (order.delivery_type === 'boxberry_courier' && postalCode) {
        setTimeout(async () => {
          setDeliveryLoading(true);
          try {
            await calculateDeliveryCostForUpdate();
          } catch (err) {
            console.error('Ошибка при инициализации расчета доставки:', err);
          }
          setDeliveryLoading(false);
        }, 500);
      }
      
      // Если есть сохраненная стоимость доставки, инициализируем её
      if (order.delivery_cost !== null && order.delivery_cost !== undefined) {
        setCalculatedDeliveryCost({
          price: order.delivery_cost,
          delivery_period: null
        });
      }
    }
  }, [showDeliveryForm, order, calculateDeliveryCostForUpdate]);
  
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
  // Отключено предупреждение: функция оставлена для возможного будущего использования
  // eslint-disable-next-line no-unused-vars
  const canEditItems = () => {
    if (!order || !order.status) return false;
    const nonEditableStatuses = ['Оплачен', 'Отправлен', 'Доставлен', 'Отменен'];
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
  
  // Обработчик обновления информации о доставке
  const handleUpdateDelivery = async () => {
    try {
      setDeliveryLoading(true);
      setDeliveryError(null);
      
      // Проверяем возможность доставки в зависимости от типа
      if (deliveryData.delivery_type === 'boxberry_courier') {
        // Для курьерской доставки нужно рассчитать стоимость (проверяет доступность)
        const deliveryCalculation = await calculateDeliveryCostForUpdate();
        
        // Если расчет вернул null (например, из-за недоступности доставки),
        // то прерываем обновление
        if (!deliveryCalculation) {
          // Если есть ошибка доставки, она уже установлена в calculateDeliveryCostForUpdate
          if (!deliveryError) {
            setDeliveryError('Не удалось рассчитать стоимость доставки. Возможно, курьерская доставка недоступна в выбранном городе.');
          }
          return;
        }
      }
      
      // Получаем стоимость доставки из рассчитанного значения или текущего заказа
      let deliveryCost = calculatedDeliveryCost ? calculatedDeliveryCost.price : (order.delivery_info?.delivery_cost || order.delivery_cost || 0);
      
      // Создаем объект delivery_info для обновления
      const deliveryInfo = {
        delivery_type: deliveryData.delivery_type,
        delivery_cost: deliveryCost,
        tracking_number: order.delivery_info?.tracking_number || order.tracking_number || null
      };

      // Если выбран пункт BoxBerry, добавляем его код
      if (deliveryData.delivery_type === 'boxberry_pickup_point' && selectedPickupPoint) {
        deliveryInfo.boxberry_point_id = parseInt(selectedPickupPoint.Code);
        deliveryInfo.boxberry_point_address = selectedPickupPoint.Address;
      } else if (deliveryData.delivery_type === 'boxberry_courier') {
        // Для курьерской доставки явно устанавливаем boxberry_point_id в null,
        // чтобы очистить его, если ранее был выбран пункт выдачи
        deliveryInfo.boxberry_point_id = null;
        deliveryInfo.boxberry_point_address = null;
      }
      
      console.log('Текущая стоимость доставки:', deliveryCost);
      
      // Базовые данные для обновления
      const updateData = {
        delivery_address: deliveryData.delivery_address,
        is_payment_on_delivery: isPaymentOnDelivery,
        delivery_info: {
          ...deliveryInfo,
          // Принудительно добавляем поля, даже если они null
          delivery_type: deliveryData.delivery_type,
          delivery_cost: deliveryCost
        }
      };
      
      console.log('Подробные данные для отправки:', updateData);
      
      console.log('Отправляем запрос на обновление доставки:', updateData);
      
      // Вызываем API для обновления данных о доставке
      const response = await adminAPI.updateOrderDeliveryInfo(orderId, updateData);
      
      if (response) {
        setDeliverySuccess(true);
        setTimeout(() => setDeliverySuccess(false), 3000);
        
        // Обновляем данные заказа
        const updatedOrder = await adminAPI.getOrderById(orderId);
        setOrder(updatedOrder);
        
        // Сбрасываем рассчитанную стоимость
        setCalculatedDeliveryCost(null);
        
        // Закрываем форму редактирования
        setShowDeliveryForm(false);
      }
    } catch (err) {
      console.error('Ошибка при обновлении информации о доставке:', err);
      
      // Проверяем наличие детальной информации об ошибке от API
      if (err.response && err.response.data && err.response.data.detail) {
        // Устанавливаем текст ошибки из ответа API
        setDeliveryError(err.response.data.detail);
        
        // Если ошибка связана с невозможностью курьерской доставки
        const errorText = err.response.data.detail.toLowerCase();
        if (errorText.includes('курьерская доставка') && errorText.includes('невозможна')) {
          console.log('Курьерская доставка невозможна по указанному адресу/индексу');
          
          // Можно предложить выбрать другой способ доставки
          // или оставить с ошибкой, чтобы админ выбрал другое
        }
      } else {
        setDeliveryError('Не удалось обновить информацию о доставке');
      }
    } finally {
      setDeliveryLoading(false);
    }
  };
  
  // (удалённый остаток дубликата)
  
  // Обработчик открытия модального окна для создания посылки
  // eslint-disable-next-line no-unused-vars
  const handleOpenBoxberryModal = () => {
    setShowBoxberryModal(true);
    setBoxberryResult(null);
  };
  
  // Обработчик закрытия модального окна для создания посылки
  // eslint-disable-next-line no-unused-vars
  const handleCloseBoxberryModal = () => {
    setShowBoxberryModal(false);
  };
  
  // Обработчик подтверждения создания посылки
  const handleConfirmBoxberryParcel = async () => {
    try {
      setBoxberryLoading(true);
      setError(null);
      
      // Проверяем, что заказ подходит для создания посылки
      if (!order.id) {
        setError('Не удалось получить идентификатор заказа');
        return;
      }
      
      // Вызываем API для создания посылки
      const result = await createBoxberryParcel(orderId);
      setBoxberryResult(result);
      
      if (result && result.success) {
        // Если есть трек-номер и этикетка, обновляем информацию о доставке
        if (result.track_number || result.label) {
          try {
            // Подготавливаем данные для обновления информации о доставке
            const deliveryUpdateData = {
              delivery_info: {
                tracking_number: result.track_number || null,
                label_url_boxberry: result.label || null
              }
            };
            
            // Обновляем информацию о доставке через API
            await adminAPI.updateOrderDeliveryInfo(orderId, deliveryUpdateData);
            console.log('Информация о доставке обновлена:', deliveryUpdateData);
          } catch (updateError) {
            console.error('Ошибка при обновлении информации о доставке:', updateError);
          }
        }
        
        // Обновление данных заказа после создания посылки
        const updatedOrder = await getAdminOrderById(orderId);
        if (updatedOrder) {
          setOrder(updatedOrder);
          console.log("Успешно обновлен заказ с трек-номером:", updatedOrder.delivery_info?.tracking_number);
          console.log("URL этикетки:", updatedOrder.delivery_info?.label_url_boxberry || "не указан");
        } else {
          console.error("Не удалось получить обновленные данные заказа");
        }
      }
    } catch (err) {
      console.error('Ошибка при создании посылки Boxberry:', err);
      
      if (err.response) {
        console.error('Статус ошибки:', err.response.status);
        console.error('Данные ошибки:', err.response.data);
      }
      
      setError(err.message || 'Не удалось создать посылку Boxberry');
      setBoxberryResult({
        success: false,
        error: err.message || 'Не удалось создать посылку Boxberry'
      });
    } finally {
      setBoxberryLoading(false);
    }
  };
  
  // Обработчик открытия модального окна для создания посылки
const handleOpenBoxberryParcelModal = () => {
  setShowBoxberryParcelModal(true);
  setBoxberryResult(null);
};

// Обработчик закрытия модального окна для создания посылки
const handleCloseBoxberryParcelModal = () => {
  setShowBoxberryParcelModal(false);
  // Если была создана посылка, перезагружаем данные заказа
  if (boxberryResult && boxberryResult.success) {
    getAdminOrderById(orderId).then(updatedOrder => {
      if (updatedOrder) {
        setOrder(updatedOrder);
      }
    });
  }
};
  
  return (
    <Container className="py-4">
      <AdminBackButton to="/admin/orders" label="Вернуться к списку заказов" />
      <h2 className="mb-4">Информация о заказе #{order.id}</h2>
      <Button variant="primary" className="mb-3" onClick={() => setShowEditModal(true)}>
        Редактировать заказ
      </Button>
      <EditOrderModal
        order={order}
        show={showEditModal}
        onHide={() => setShowEditModal(false)}
        onOrderUpdated={setOrder}
        statuses={statuses}
      />
      
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
                  <p>
                    <strong>Сумма заказа:</strong> {formatPrice(
                      (calculatedDeliveryCost && deliveryData.delivery_type)
                        ? (
                            // Берем стоимость товаров (без доставки)
                            (order.total_price - (order.delivery_info?.delivery_cost || order.delivery_cost || 0)) 
                            // И добавляем новую стоимость доставки
                            + calculatedDeliveryCost.price
                          )
                        : order.total_price
                    )}
                    {calculatedDeliveryCost && deliveryData.delivery_type && (
                      <span className="text-muted small ms-1">(обновится после сохранения)</span>
                    )}
                  </p>
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
              
              {/* Информация о доставке с возможностью редактирования */}
              <div className="mt-4">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h6 className="mb-0">Информация о доставке</h6>
                  {/* Кнопка 'Изменить' убрана, теперь всё редактируется через EditOrderModal */}
                </div>
                
                {showDeliveryForm ? (
                  <Form className="mt-3">
                    <Form.Group className="mb-3">
                      <Form.Label>Тип доставки</Form.Label>
                      <Form.Select 
                        value={deliveryData.delivery_type}
                        onChange={handleDeliveryTypeChange}
                        className="mb-2"
                      >
                        <option value="">Выберите тип доставки</option>
                        <option value="boxberry_pickup_point">Пункт выдачи BoxBerry</option>
                        <option value="boxberry_courier">Курьерская доставка BoxBerry</option>
                      </Form.Select>
                    </Form.Group>
                    
                    {/* Адрес доставки */}
                    <Form.Group className="mb-3">
                      <Form.Label>Адрес доставки</Form.Label>
                      {deliveryData.delivery_type === 'boxberry_pickup_point' ? (
                        <div className="d-flex">
                          <Form.Control
                            type="text"
                            value={deliveryData.delivery_address}
                            onChange={handleDeliveryAddressChange}
                            placeholder="Выберите пункт выдачи"
                            readOnly={true}
                            className="me-2"
                          />
                          <Button 
                            variant="outline-primary" 
                            size="sm"
                            onClick={() => setShowBoxberryModal(true)}
                          >
                            {selectedPickupPoint ? 'Изменить пункт выдачи' : 'Выбрать пункт выдачи'}
                          </Button>
                        </div>
                      ) : (
                        <div className="position-relative">
                          <Form.Control
                            type="text"
                            value={deliveryData.delivery_address}
                            onChange={handleDeliveryAddressChange}
                            placeholder="Введите адрес доставки"
                            className="mb-2"
                          />
                          {addressOptions.length > 0 && (
                            <div 
                              className="position-absolute w-100 border rounded bg-white shadow-sm overflow-hidden" 
                              style={{ zIndex: 1000, maxHeight: '300px', overflowY: 'auto' }}
                            >
                              {addressOptions.map((suggestion, index) => (
                                 <button
                                   key={index}
                                   type="button"
                                   className="w-100 text-start p-2 border-0 bg-white border-bottom"
                                   onClick={() => handleSelectAddress(suggestion)}
                                 >
                                   {suggestion.value}
                                 </button>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </Form.Group>
                    
                    {/* Информация о недоступности курьерской доставки */}
                    {deliveryData.delivery_type === 'boxberry_courier' && 
                     deliveryError && deliveryError.toLowerCase().includes('курьерская доставка') && 
                     deliveryError.toLowerCase().includes('невозможна') && (
                      <Alert variant="warning" className="mt-2 mb-3">
                        <Alert.Heading as="h6">Курьерская доставка недоступна</Alert.Heading>
                        <p className="mb-0">Для выбранного города или почтового индекса курьерская доставка BoxBerry недоступна. 
                        Пожалуйста, выберите другой адрес или используйте доставку в пункт выдачи.</p>
                      </Alert>
                    )}
                    
                    {isBoxberryPickupPoint && selectedPickupPoint && (
                      <div className="mt-2 p-2 border rounded bg-light mb-3">
                        <p className="mb-1"><strong>{selectedPickupPoint.Name}</strong></p>
                        <p className="mb-1 small">{selectedPickupPoint.Address}</p>
                        <p className="mb-0 small text-muted">График работы: {selectedPickupPoint.WorkShedule}</p>
                      </div>
                    )}
                    
                    {/* Отображение рассчитанной стоимости доставки */}
                    {calculatedDeliveryCost && (
                      <div className="mt-2 mb-3 p-2 border rounded bg-light">
                        <h6 className="mb-1">Расчетная стоимость доставки:</h6>
                        <p className="mb-1 fs-5 text-success fw-bold">
                          {formatPrice(calculatedDeliveryCost.price)}
                        </p>
                        {calculatedDeliveryCost.delivery_period && (
                          <p className="mb-0 small text-muted">
                            Срок доставки: {calculatedDeliveryCost.delivery_period} {
                              calculatedDeliveryCost.delivery_period === 1 ? 'день' : 
                              calculatedDeliveryCost.delivery_period < 5 ? 'дня' : 'дней'
                            }
                          </p>
                        )}
                      </div>
                    )}
                    
                    {/* Способ оплаты */}
                    <Form.Group className="mb-3">
                      <Form.Label>Способ оплаты</Form.Label>
                      <div>
                        <Form.Check
                          type="radio"
                          id="payment-on-delivery"
                          name="payment-method"
                          label="Оплата при получении"
                          checked={isPaymentOnDelivery}
                          onChange={() => {
                            // Сразу запускаем пересчет, не дожидаясь обновления состояния
                            setTimeout(async () => {
                              setDeliveryLoading(true);
                              try {
                                // Передаем true явно вместо isPaymentOnDelivery
                                await calculateDeliveryCostForUpdate(true);
                              } catch (err) {
                                console.error('Ошибка при пересчете доставки:', err);
                              } finally {
                                setDeliveryLoading(false);
                              }
                            }, 100);
                            
                            // Обновляем состояние после расчета
                            setIsPaymentOnDelivery(true);
                          }}
                          className="mb-2"
                        />
                        <Form.Check
                          type="radio"
                          id="payment-online"
                          name="payment-method"
                          label="Оплата на сайте"
                          checked={!isPaymentOnDelivery}
                          onChange={() => {
                            // Сразу запускаем пересчет, не дожидаясь обновления состояния
                            setTimeout(async () => {
                              setDeliveryLoading(true);
                              try {
                                // Передаем false явно вместо isPaymentOnDelivery
                                await calculateDeliveryCostForUpdate(false);
                              } catch (err) {
                                console.error('Ошибка при пересчете доставки:', err);
                              } finally {
                                setDeliveryLoading(false);
                              }
                            }, 100);
                            
                            // Обновляем состояние после расчета
                            setIsPaymentOnDelivery(false);
                          }}
                        />
                      </div>
                    </Form.Group>
                    
                    {deliveryLoading && !deliveryData.delivery_type.includes('pickup_point') && (
                      <div className="text-center py-2">
                        <Spinner animation="border" size="sm" className="me-2" />
                        <span className="text-muted">Расчет стоимости доставки...</span>
                      </div>
                    )}
                    
                    <div className="d-flex justify-content-end">
                      <Button 
                        variant="primary" 
                        size="sm" 
                        onClick={handleUpdateDelivery}
                        disabled={deliveryLoading || deliveryError || 
                          // Проверяем наличие данных для доставки согласно типу
                          (deliveryData.delivery_type === 'boxberry_pickup_point' && !selectedPickupPoint) ||
                          (deliveryData.delivery_type === 'boxberry_courier' && (!selectedAddressData || !selectedAddressData.postal_code))
                        }
                      >
                        {deliveryLoading ? (
                          <>
                            <Spinner as="span" animation="border" size="sm" />
                            <span className="ms-2">Сохранение...</span>
                          </>
                        ) : (
                          "Сохранить"
                        )}
                      </Button>
                    </div>
                    
                    {deliverySuccess && (
                      <Alert variant="success" className="mt-3">
                        Информация о доставке успешно обновлена
                      </Alert>
                    )}
                    
                    {deliveryError && (
                      <Alert variant="danger" className="mt-3">
                        {deliveryError}
                      </Alert>
                    )}
                  </Form>
                ) : (
                  <div>
                    <p><strong>Тип доставки:</strong> {formatDeliveryType(order.delivery_info?.delivery_type || order.delivery_type)}</p>
                    <p><strong>Адрес доставки:</strong> {order.delivery_address}</p>
                    <p><strong>Стоимость доставки:</strong> {formatPrice(order.delivery_info?.delivery_cost || order.delivery_cost || 0)}</p>
                    
                    {/* Отображение информации о пункте выдачи Boxberry, если есть */}
                    {(order.delivery_info?.delivery_type || order.delivery_type)?.includes('boxberry_pickup_point') && 
                     (order.delivery_info?.boxberry_point_address || order.boxberry_point_address) && (
                      <p><strong>Пункт выдачи BoxBerry:</strong> {order.delivery_info?.boxberry_point_address || order.boxberry_point_address}</p>
                    )}
                    
                    {/* Отображение трек-номера и кнопки для Boxberry */}
                    {(order.delivery_info?.delivery_type || order.delivery_type)?.includes('boxberry') && (
                      <div className="mt-3 border-top pt-3">
                        <div className="d-flex justify-content-between align-items-center">
                          <div>
                            <strong>Трек-номер:</strong> {(order.delivery_info?.tracking_number || order.tracking_number) ? (
                              <span>{order.delivery_info?.tracking_number || order.tracking_number}</span>
                            ) : (
                              <span className="text-muted">Не создан</span>
                            )}
                            <p>
                              <strong>Статус в доставке:</strong>{" "}
                              {order.delivery_info?.status_in_delivery_service
                                ? order.delivery_info.status_in_delivery_service
                                : <span className="text-muted">—</span>
                              }
                            </p>
                          </div>
                          
                          <Button 
                            variant="primary" 
                            size="sm"
                            onClick={handleOpenBoxberryParcelModal}
                            disabled={boxberryLoading || loading}
                          >
                            {(order.delivery_info?.tracking_number || order.tracking_number) ? "Обновить посылку" : "Выгрузить заказ в Boxberry"}
                          </Button>
                        </div>
                        {(order.delivery_info?.label_url_boxberry) && (
                          <p>
                            <strong>Этикетка Boxberry:</strong>{' '}
                            <a 
                              href={order.delivery_info.label_url_boxberry} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              className="btn btn-sm btn-outline-primary"
                            >
                              <i className="bi bi-printer me-1"></i>
                              Открыть этикетку
                            </a>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
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
                    <td colSpan="4" className="text-end"><strong>Стоимость товаров:</strong></td>
                    <td>
                      <strong>
                        {formatPrice(
                          order.items.reduce((total, item) => total + (item.unit_price || item.product_price || 0) * item.quantity, 0)
                        )}
                      </strong>
                    </td>
                  </tr>
                  <tr>
                    <td colSpan="4" className="text-end"><strong>Стоимость доставки:</strong></td>
                    <td>
                      <strong>
                        {formatPrice(calculatedDeliveryCost ? calculatedDeliveryCost.price : (order.delivery_info?.delivery_cost || order.delivery_cost || 0))}
                      </strong>
                      {calculatedDeliveryCost && deliveryData.delivery_type && (
                        <div className="text-muted small">
                          (обновится после сохранения)
                        </div>
                      )}
                    </td>
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
                  <tr>
                    <td colSpan="4" className="text-end"><strong>Итого:</strong></td>
                    <td>
                      <strong>
                        {formatPrice(
                          (
                            (calculatedDeliveryCost && deliveryData.delivery_type)
                              ? (
                                  order.items.reduce((total, item) => total + (item.unit_price || item.product_price || 0) * item.quantity, 0)
                                  + calculatedDeliveryCost.price
                                )
                              : (
                                  order.items.reduce((total, item) => total + (item.unit_price || item.product_price || 0) * item.quantity, 0)
                                  + (order.delivery_info?.delivery_cost || 0)
                                )
                          )
                          - (order.discount_amount || 0)
                        )}
                      </strong>
                      {calculatedDeliveryCost && deliveryData.delivery_type && (
                        <div className="text-muted small">
                          (обновится после сохранения)
                        </div>
                      )}
                    </td>
                  </tr>
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
                    order.status_history.map((statusChange) => (
                      <div key={statusChange.id || `${statusChange.status?.id}-${statusChange.changed_at || statusChange.timestamp}`} className="status-item mb-3">
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
              <p><strong>ID пользователя:</strong> {order.user_id}</p>
              <p><strong>Email:</strong> {order.email}</p>
              <p><strong>Телефон:</strong> {order.phone || 'Не указан'}</p>
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
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Управление статусом</h5>
            </Card.Header>
            <Card.Body>
              <Form>
                <Form.Group className="mb-3">
                  <Form.Label>Статус заказа</Form.Label>
                  <Form.Select 
                    value={selectedStatus || ''} 
                    onChange={handleStatusChange}
                    disabled={loading}
                  >
                    <option value="">Выберите статус</option>
                    {statuses.map(status => (
                      <option key={status.id} value={status.id}>
                        {status.name}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label>Комментарий к изменению статуса</Form.Label>
                  <Form.Control 
                    as="textarea" 
                    rows={3} 
                    value={statusNote}
                    onChange={handleNoteChange}
                    placeholder="Укажите причину изменения статуса"
                    disabled={loading}
                  />
                </Form.Group>
                <Button 
                  variant="primary" 
                  onClick={handleOpenModal}
                  disabled={loading || !selectedStatus || selectedStatus === (order.status?.id || '').toString()}
                >
                  Обновить статус
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

      {/* Модальное окно для создания посылки в Boxberry */}
      <Modal 
        show={showBoxberryParcelModal} 
        onHide={handleCloseBoxberryParcelModal}
        backdrop="static"
      >
        <Modal.Header closeButton>
          <Modal.Title>
            {order.tracking_number 
              ? "Обновление посылки в Boxberry" 
              : "Создание посылки в Boxberry"}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {boxberryLoading ? (
            <div className="text-center my-4">
              <Spinner animation="border" role="status">
                <span className="visually-hidden">Загрузка...</span>
              </Spinner>
              <p className="mt-3">
                {order.tracking_number 
                  ? "Идет обновление посылки в Boxberry..." 
                  : "Идет создание посылки в Boxberry..."}
              </p>
            </div>
          ) : boxberryResult ? (
            // Отображаем результат создания/обновления посылки
            <>
              {boxberryResult.success ? (
                <div>
                  <Alert variant="success">
                    {order.tracking_number 
                      ? "Посылка успешно обновлена в системе Boxberry."
                      : "Посылка успешно создана в системе Boxberry."}
                  </Alert>
                  <p><strong>Трек-номер:</strong> {boxberryResult.trackingNumber}</p>
                  {boxberryResult.label && (
                    <p>
                      <a 
                        href={boxberryResult.label} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="btn btn-outline-primary btn-sm"
                      >
                        Скачать этикетку
                      </a>
                    </p>
                  )}
                </div>
              ) : (
                <Alert variant="danger">
                  {boxberryResult.error || "Произошла ошибка при работе с посылкой в Boxberry"}
                </Alert>
              )}
            </>
          ) : (
            // Отображаем форму создания/обновления посылки
            <>
              <p>
                {order.delivery_info?.tracking_number || order.tracking_number
                ? `Вы уверены, что хотите обновить посылку ${order.delivery_info?.tracking_number || order.tracking_number} в Boxberry для этого заказа?` 
                  : "Вы уверены, что хотите создать посылку в Boxberry для этого заказа?"}
              </p>
              
              <Alert variant="info">
                {order.tracking_number 
                  ? "Обновление посылки позволит синхронизировать информацию о заказе с системой Boxberry."
                  : "После создания посылки в системе Boxberry, заказу будет присвоен трек-номер для отслеживания."}
              </Alert>
              
              {error && (
                <Alert variant="danger">
                  {error}
                </Alert>
              )}
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          {boxberryResult ? (
            <Button variant="secondary" onClick={handleCloseBoxberryParcelModal}>
              Закрыть
            </Button>
          ) : (
            <>
              <Button variant="secondary" onClick={handleCloseBoxberryParcelModal}>
                Отмена
              </Button>
              <Button 
                variant="primary" 
                onClick={handleConfirmBoxberryParcel}
                disabled={boxberryLoading}
              >
                {order.delivery_info?.tracking_number || order.tracking_number ? "Обновить" : "Создать"}
              </Button>
            </>
          )}
        </Modal.Footer>
      </Modal>
      
      
    </Container>
  );
};

export default AdminOrderDetail; 