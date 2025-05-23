import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { formatPrice } from '../utils/helpers';
import '../pages/CartPage.css';
import { useConfirm } from '../components/common/ConfirmContext';

const CartPage = () => {
  const { cart, loading, error, updateCartItem, removeFromCart, clearCart, fetchCart } = useCart();
  const [quantities, setQuantities] = useState({});
  const [isUpdating, setIsUpdating] = useState({});
  const [isRemoving, setIsRemoving] = useState({});
  const [isClearingCart, setIsClearingCart] = useState(false);
  const [updateMessage, setUpdateMessage] = useState({ type: '', text: '' });
  // Таймеры для дебаунсинга обновления количества
  const updateTimers = useRef({});
  // Сохраняем исходный порядок элементов корзины
  const [itemsOrder, setItemsOrder] = useState([]);
  const confirm = useConfirm();
  
  // Инициализируем локальное состояние количества товаров при загрузке/обновлении корзины
  useEffect(() => {
    if (cart && cart.items && cart.items.length > 0) {
      const newQuantities = {};
      cart.items.forEach(item => {
        const key = item.id !== undefined ? item.id : `anon_${item.product_id}`;
        newQuantities[key] = item.quantity;
      });
      setQuantities(newQuantities);

      // Стабилизируем порядок: удаляем отсутствующие ключи, добавляем новые
      const currentKeys = cart.items.map(item => item.id !== undefined ? item.id : `anon_${item.product_id}`);
      setItemsOrder(prevOrder => {
        // Удаляем отсутствующие
        let filtered = prevOrder.filter(key => currentKeys.includes(key));
        // Добавляем новые
        const newKeys = currentKeys.filter(key => !filtered.includes(key));
        return [...filtered, ...newKeys];
      });
    }
  }, [cart]);

  // Сортируем элементы корзины согласно сохраненному порядку
  const sortedCartItems = useMemo(() => {
    if (!cart || !cart.items) return [];
    const itemsCopy = [...cart.items];
    return itemsCopy.sort((a, b) => {
      const keyA = a.id !== undefined ? a.id : `anon_${a.product_id}`;
      const keyB = b.id !== undefined ? b.id : `anon_${b.product_id}`;
      const indexA = itemsOrder.indexOf(keyA);
      const indexB = itemsOrder.indexOf(keyB);
      if (indexA === -1) return 1;
      if (indexB === -1) return -1;
      return indexA - indexB;
    });
  }, [cart, itemsOrder]);

  // Обработчик изменения количества товара
  const handleQuantityChange = (itemKey, value) => {
    // Очищаем предыдущий таймер обновления для этого товара, если он есть
    if (updateTimers.current[itemKey]) {
      clearTimeout(updateTimers.current[itemKey]);
    }

    // Проверяем, что value - это число или может быть преобразовано в число
    let newQuantity = parseInt(value, 10);
    if (isNaN(newQuantity) || newQuantity < 1) {
      newQuantity = 1;
    }
    
    // Находим максимально доступное количество товара
    const itemInCart = cart.items.find(item => (item.id !== undefined ? item.id : `anon_${item.product_id}`) === itemKey);
    const maxStock = itemInCart && itemInCart.product ? itemInCart.product.stock : 1;
    
    // Ограничиваем новое количество максимальным значением
    if (newQuantity > maxStock) {
      newQuantity = maxStock;
    }
    
    // Обновляем локальное состояние
    setQuantities(prev => ({
      ...prev,
      [itemKey]: newQuantity
    }));

    // Устанавливаем новый таймер для обновления через 800 мс - увеличили задержку для стабильности
    updateTimers.current[itemKey] = setTimeout(() => {
      // Проверяем, изменилось ли количество по сравнению с корзиной
      const currentItem = cart.items.find(item => (item.id !== undefined ? item.id : `anon_${item.product_id}`) === itemKey);
      if (currentItem && currentItem.quantity !== newQuantity) {
        // Явно вызываем функцию обновления количества
        handleUpdateQuantity(itemKey, newQuantity);
      }
    }, 800);
  };

  // Очищаем все таймеры при размонтировании компонента
  useEffect(() => {
    // Сохраняем ссылку на текущее значение таймеров внутри эффекта
    const currentTimers = updateTimers.current;
    
    return () => {
      // Используем сохраненную переменную при очистке
      Object.values(currentTimers).forEach(timerId => {
        clearTimeout(timerId);
      });
    };
  }, []);

  // Обработчик обновления количества товара
  const handleUpdateQuantity = async (itemKey, quantity = null) => {
    // Используем переданное количество или берем из локального состояния
    const newQuantity = quantity !== null ? quantity : (quantities[itemKey] || 1);
    
    setIsUpdating(prev => ({ ...prev, [itemKey]: true }));
    setUpdateMessage({ type: '', text: '' });

    try {
      const item = cart.items.find(item => (item.id !== undefined ? item.id : `anon_${item.product_id}`) === itemKey);
      const result = await updateCartItem(item.id !== undefined ? item.id : cart.items.indexOf(item), newQuantity);
      
      if (result.success) {
        setUpdateMessage({ type: 'success', text: 'Количество товара обновлено' });
        // Обновляем корзину после успешного обновления
        await fetchCart();
      } else {
        setUpdateMessage({ type: 'danger', text: result.message || 'Ошибка при обновлении количества' });
        
        // Восстанавливаем предыдущее значение, если обновление не удалось
        if (item) {
          setQuantities(prev => ({
            ...prev,
            [itemKey]: item.quantity
          }));
        }
      }
    } catch (err) {
      console.error('Ошибка при обновлении количества товара:', err);
      setUpdateMessage({ type: 'danger', text: 'Ошибка при обновлении количества товара' });
      
      // Восстанавливаем предыдущее значение, если обновление не удалось
      const item = cart.items.find(item => (item.id !== undefined ? item.id : `anon_${item.product_id}`) === itemKey);
      if (item) {
        setQuantities(prev => ({
          ...prev,
          [itemKey]: item.quantity
        }));
      }
    } finally {
      setIsUpdating(prev => ({ ...prev, [itemKey]: false }));
      
      // Автоматически скрываем сообщение через 3 секунды
      setTimeout(() => {
        setUpdateMessage({ type: '', text: '' });
      }, 3000);
    }
  };

  // Обработчик удаления товара
  const handleRemoveItem = async (itemKey) => {
    setIsRemoving(prev => ({ ...prev, [itemKey]: true }));
    setUpdateMessage({ type: '', text: '' });

    try {
      const item = cart.items.find(item => (item.id !== undefined ? item.id : `anon_${item.product_id}`) === itemKey);
      const result = await removeFromCart(item.id !== undefined ? item.id : cart.items.indexOf(item));
      
      if (result.success) {
        setUpdateMessage({ type: 'success', text: 'Товар удален из корзины' });
        // Обновляем корзину после успешного удаления
        await fetchCart();
      } else {
        setUpdateMessage({ type: 'danger', text: result.message });
      }
    } catch (err) {
      console.error('Ошибка при удалении товара:', err);
      setUpdateMessage({ type: 'danger', text: 'Ошибка при удалении товара' });
    } finally {
      setIsRemoving(prev => ({ ...prev, [itemKey]: false }));
      
      // Автоматически скрываем сообщение через 3 секунды
      setTimeout(() => {
        setUpdateMessage({ type: '', text: '' });
      }, 3000);
    }
  };

  // Обработчик очистки корзины
  const handleClearCart = async () => {
    const ok = await confirm({
      title: 'Очистить корзину?',
      body: 'Вы действительно хотите удалить все товары из корзины?'
    });
    if (!ok) return;
    setIsClearingCart(true);
    setUpdateMessage({ type: '', text: '' });

    try {
      const result = await clearCart();
      
      if (result.success) {
        setUpdateMessage({ type: 'success', text: 'Корзина очищена' });
        // Обновляем корзину после успешной очистки
        await fetchCart();
      } else {
        setUpdateMessage({ type: 'danger', text: result.message });
      }
    } catch (err) {
      console.error('Ошибка при очистке корзины:', err);
      setUpdateMessage({ type: 'danger', text: 'Ошибка при очистке корзины' });
    } finally {
      setIsClearingCart(false);
      
      // Автоматически скрываем сообщение через 3 секунды
      setTimeout(() => {
        setUpdateMessage({ type: '', text: '' });
      }, 3000);
    }
  };

  // Если произошла ошибка, показываем сообщение
  if (error) {
    return (
      <div className="alert alert-danger my-4" role="alert">
        <h4 className="alert-heading">Ошибка!</h4>
        <p>{error}</p>
        <hr />
        <p className="mb-0">
          Пожалуйста, попробуйте <button className="btn btn-link p-0" onClick={() => window.location.reload()}>обновить страницу</button>.
        </p>
      </div>
    );
  }

  // Если корзина пуста, показываем соответствующее сообщение
  if (!cart || !cart.items || cart.items.length === 0) {
    return (
      <div className="text-center py-5">
        <div className="mb-4">
          <i className="bi bi-cart-x display-1 text-muted"></i>
        </div>
        <h2>Ваша корзина пуста</h2>
        <p className="text-muted mb-4">Добавьте товары в корзину, чтобы продолжить покупки</p>
        <Link to="/products" className="btn btn-primary">
          Перейти к покупкам
        </Link>
      </div>
    );
  }

  return (
    <div className="cart-page" style={{ position: 'relative' }}>
      {loading && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          background: 'rgba(255,255,255,0.7)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Загрузка...</span>
          </div>
        </div>
      )}
      <h1 className="mb-4">Корзина</h1>
      
      {/* Сообщение об обновлении */}
      {updateMessage.text && (
        <div className={`alert alert-${updateMessage.type} alert-dismissible fade show`} role="alert">
          {updateMessage.text}
          <button 
            type="button" 
            className="btn-close" 
            onClick={() => setUpdateMessage({ type: '', text: '' })}
            aria-label="Close"
          ></button>
        </div>
      )}
      
      <div className="row">
        <div className="col-lg-8">
          <div className="card mb-4">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Товары в корзине</h5>
              <button 
                className="btn btn-sm btn-outline-danger"
                onClick={handleClearCart}
                disabled={loading || isClearingCart}
              >
                {isClearingCart ? (
                  <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
                ) : (
                  <i className="bi bi-trash me-1"></i>
                )}
                Очистить корзину
              </button>
            </div>
            <div className="card-body p-0">
              <div className="table-responsive">
                <table className="table table-hover mb-0">
                  <thead className="table-light">
                    <tr>
                      <th scope="col" style={{ width: '50%' }}>Товар</th>
                      <th scope="col" className="text-center">Цена</th>
                      <th scope="col" className="text-center">Количество</th>
                      <th scope="col" className="text-center">Сумма</th>
                      <th scope="col" className="text-center">Действия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedCartItems.map((item, idx) => {
                      const key = item.id !== undefined ? item.id : `anon_${item.product_id}`;
                      return (
                        <tr key={key}>
                          <td>
                            <div className="d-flex align-items-center">
                              <div className="me-3">
                                {item.product && item.product.image ? (
                                  <img 
                                    src={`http://localhost:8001${item.product.image}`} 
                                    alt={item.product ? item.product.name : 'Товар'} 
                                    style={{ width: '60px', height: '60px', objectFit: 'cover' }}
                                    className="rounded"
                                  />
                                ) : (
                                  <div 
                                    className="bg-light rounded d-flex align-items-center justify-content-center"
                                    style={{ width: '60px', height: '60px' }}
                                  >
                                    <i className="bi bi-image text-muted"></i>
                                  </div>
                                )}
                              </div>
                              <div>
                                <h6 className="mb-0">
                                  {item.product ? (
                                    <Link to={`/products/${item.product.id}`} className="text-decoration-none">
                                      {item.product.name}
                                    </Link>
                                  ) : (
                                    'Товар недоступен'
                                  )}
                                </h6>
                                {item.product && item.product.stock > 0 ? (
                                  <small className="text-success">
                                    <i className="bi bi-check-circle me-1"></i>
                                    В наличии
                                  </small>
                                ) : (
                                  <small className="text-danger">
                                    <i className="bi bi-x-circle me-1"></i>
                                    Нет в наличии
                                  </small>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="text-center align-middle">
                            {item.product ? `${formatPrice(item.product.price)} ₽` : '-'}
                          </td>
                          <td className="text-center align-middle">
                            <div className="d-flex align-items-center justify-content-center">
                              <div className="input-group" style={{ width: '150px' }}>
                                <button 
                                  className="btn btn-outline-secondary" 
                                  type="button"
                                  onClick={() => {
                                    const newQuantity = Math.max(1, (quantities[key] || item.quantity) - 1);
                                    handleQuantityChange(key, newQuantity);
                                  }}
                                  disabled={isUpdating[key]}
                                >
                                  <i className="bi bi-dash"></i>
                                </button>
                                <input 
                                  type="text"
                                  pattern="[0-9]*"
                                  inputMode="numeric"
                                  className="form-control text-center fs-5"
                                  value={quantities[key] !== undefined ? quantities[key] : item.quantity}
                                  onChange={(e) => {
                                    // Разрешаем только цифры
                                    const value = e.target.value.replace(/[^0-9]/g, '');
                                    handleQuantityChange(key, value);
                                  }}
                                  style={{ 
                                    minWidth: '50px',
                                    textAlign: 'center',
                                    padding: '0.375rem 0.5rem'
                                  }}
                                  disabled={isUpdating[key]}
                                  aria-label="Количество товара"
                                />
                                <button 
                                  className="btn btn-outline-secondary" 
                                  type="button"
                                  onClick={() => {
                                    const maxStock = item.product ? item.product.stock : 1;
                                    const newQuantity = Math.min(maxStock, (quantities[key] || item.quantity) + 1);
                                    handleQuantityChange(key, newQuantity);
                                  }}
                                  disabled={isUpdating[key] || (item.product && (quantities[key] || item.quantity) >= item.product.stock)}
                                >
                                  <i className="bi bi-plus"></i>
                                </button>
                              </div>
                              {isUpdating[key] && (
                                <div className="ms-2">
                                  <span className="spinner-border spinner-border-sm text-primary" role="status" aria-hidden="true"></span>
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="text-center align-middle fw-bold">
                            {item.product ? `${formatPrice(item.product.price * item.quantity)} ₽` : '-'}
                          </td>
                          <td className="text-center align-middle">
                            <button 
                              type="button"
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => handleRemoveItem(key)}
                              disabled={isRemoving[key]}
                              title="Удалить из корзины"
                            >
                              {isRemoving[key] ? (
                                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                              ) : (
                                <i className="bi bi-trash"></i>
                              )}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        
        <div className="col-lg-4">
          <div className="card">
            <div className="card-header">
              <h5 className="mb-0">Сводка заказа</h5>
            </div>
            <div className="card-body">
              <div className="d-flex justify-content-between mb-2">
                <span>Товары ({cart.total_items}):</span>
                <span>{formatPrice(cart.total_price)} ₽</span>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span>Доставка:</span>
                <span title="Стоимость доставки будет рассчитана на странице оформления заказа" style={{ cursor: 'help' }}>
                  <i className="bi bi-truck"></i> —
                </span>
              </div>
              <div className="text-muted small text-end" style={{ marginTop: '-8px' }}>
                Стоимость будет рассчитана на следующем шаге
              </div>
              <hr />
              <div className="d-flex justify-content-between mb-3">
                <span className="fw-bold">Итого:</span>
                <span className="fw-bold fs-5">{formatPrice(cart.total_price)} ₽</span>
              </div>
              <div className="cart-summary-total">
                <div className="cart-summary-total-label">Итого:</div>
                <div className="cart-summary-total-value">
                  {formatPrice(cart?.total_price || 0)}
                </div>
              </div>
              
              <div className="cart-checkout-btns mt-4">
                <Link 
                  to="/products" 
                  className="btn btn-outline-secondary w-100 mb-2"
                >
                  Продолжить покупки
                </Link>
                <Link 
                  to="/checkout" 
                  className="btn btn-primary w-100"
                  disabled={!cart?.items?.length}
                >
                  Оформить заказ
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CartPage; 