import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { formatPrice } from '../utils/helpers';
import '../pages/CartPage.css';

const CartPage = () => {
  const { cart, loading, error, updateCartItem, removeFromCart, clearCart, fetchCart } = useCart();
  const [quantities, setQuantities] = useState({});
  const [isUpdating, setIsUpdating] = useState({});
  const [isRemoving, setIsRemoving] = useState({});
  const [isClearingCart, setIsClearingCart] = useState(false);
  const [updateMessage, setUpdateMessage] = useState({ type: '', text: '' });

  // Обработчик изменения количества товара
  const handleQuantityChange = (itemId, value) => {
    setQuantities(prev => ({
      ...prev,
      [itemId]: parseInt(value, 10) || 1
    }));
  };

  // Обработчик обновления количества товара
  const handleUpdateQuantity = async (itemId) => {
    setIsUpdating(prev => ({ ...prev, [itemId]: true }));
    setUpdateMessage({ type: '', text: '' });

    try {
      const quantity = quantities[itemId] || 1;
      const result = await updateCartItem(itemId, quantity);
      
      if (result.success) {
        setUpdateMessage({ type: 'success', text: 'Количество товара обновлено' });
        // Обновляем корзину после успешного обновления
        await fetchCart();
      } else {
        setUpdateMessage({ type: 'danger', text: result.message });
      }
    } catch (err) {
      console.error('Ошибка при обновлении количества товара:', err);
      setUpdateMessage({ type: 'danger', text: 'Ошибка при обновлении количества товара' });
    } finally {
      setIsUpdating(prev => ({ ...prev, [itemId]: false }));
      
      // Автоматически скрываем сообщение через 3 секунды
      setTimeout(() => {
        setUpdateMessage({ type: '', text: '' });
      }, 3000);
    }
  };

  // Обработчик удаления товара
  const handleRemoveItem = async (itemId) => {
    setIsRemoving(prev => ({ ...prev, [itemId]: true }));
    setUpdateMessage({ type: '', text: '' });

    try {
      const result = await removeFromCart(itemId);
      
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
      setIsRemoving(prev => ({ ...prev, [itemId]: false }));
      
      // Автоматически скрываем сообщение через 3 секунды
      setTimeout(() => {
        setUpdateMessage({ type: '', text: '' });
      }, 3000);
    }
  };

  // Обработчик очистки корзины
  const handleClearCart = async () => {
    if (window.confirm('Вы уверены, что хотите очистить корзину?')) {
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
    }
  };

  // Если идет загрузка, показываем спиннер
  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Загрузка...</span>
        </div>
        <p className="mt-2">Загрузка корзины...</p>
      </div>
    );
  }

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
    <div className="cart-page">
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
                disabled={loading}
              >
                <i className="bi bi-trash me-1"></i>
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
                    {cart.items.map((item) => (
                      <tr key={item.id}>
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
                            <div className="input-group" style={{ width: '120px' }}>
                              <button 
                                className="btn btn-outline-secondary" 
                                type="button"
                                onClick={() => {
                                  const newQuantity = Math.max(1, (quantities[item.id] || item.quantity) - 1);
                                  handleQuantityChange(item.id, newQuantity);
                                }}
                                disabled={isUpdating[item.id]}
                              >
                                <i className="bi bi-dash"></i>
                              </button>
                              <input 
                                type="number" 
                                className="form-control text-center"
                                value={quantities[item.id] !== undefined ? quantities[item.id] : item.quantity}
                                onChange={(e) => handleQuantityChange(item.id, e.target.value)}
                                min="1"
                                max={item.product ? item.product.stock : 1}
                                disabled={isUpdating[item.id]}
                              />
                              <button 
                                className="btn btn-outline-secondary" 
                                type="button"
                                onClick={() => {
                                  const maxStock = item.product ? item.product.stock : 1;
                                  const newQuantity = Math.min(maxStock, (quantities[item.id] || item.quantity) + 1);
                                  handleQuantityChange(item.id, newQuantity);
                                }}
                                disabled={isUpdating[item.id] || (item.product && (quantities[item.id] || item.quantity) >= item.product.stock)}
                              >
                                <i className="bi bi-plus"></i>
                              </button>
                            </div>
                            {quantities[item.id] !== undefined && quantities[item.id] !== item.quantity && (
                              <button 
                                className="btn btn-sm btn-primary ms-2"
                                onClick={() => handleUpdateQuantity(item.id)}
                                disabled={isUpdating[item.id]}
                              >
                                {isUpdating[item.id] ? (
                                  <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                                ) : (
                                  <i className="bi bi-check"></i>
                                )}
                              </button>
                            )}
                          </div>
                        </td>
                        <td className="text-center align-middle fw-bold">
                          {item.product ? `${formatPrice(item.product.price * item.quantity)} ₽` : '-'}
                        </td>
                        <td className="text-center align-middle">
                          <button 
                            className="btn btn-sm btn-outline-danger"
                            onClick={() => handleRemoveItem(item.id)}
                            disabled={isRemoving[item.id]}
                            title="Удалить из корзины"
                          >
                            {isRemoving[item.id] ? (
                              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                            ) : (
                              <i className="bi bi-trash"></i>
                            )}
                          </button>
                        </td>
                      </tr>
                    ))}
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
                <span className="text-success">Бесплатно</span>
              </div>
              <hr />
              <div className="d-flex justify-content-between mb-3">
                <span className="fw-bold">Итого:</span>
                <span className="fw-bold fs-5">{formatPrice(cart.total_price)} ₽</span>
              </div>
              <button className="btn btn-primary w-100">
                Оформить заказ
              </button>
              <div className="text-center mt-3">
                <Link to="/products" className="text-decoration-none">
                  <i className="bi bi-arrow-left me-1"></i>
                  Продолжить покупки
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