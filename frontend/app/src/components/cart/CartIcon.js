import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../../context/CartContext';
import { formatPrice } from '../../utils/helpers';
import { API_URLS } from '../../utils/constants';
import './CartIcon.css';

const CartIcon = () => {
  const { cart, removeFromCart, loading, fetchCart } = useCart();
  const [isOpen, setIsOpen] = useState(false);
  const [isRemoving, setIsRemoving] = useState({}); // состояние для отслеживания удаления товаров
  const dropdownRef = useRef(null);
  const mouseTimeoutRef = useRef(null);
  const navigate = useNavigate();
  
  // Логируем cartSummary при каждом изменении
  useEffect(() => {
    console.log('cartSummary изменился:', cart);
  }, [cart]);

  // При монтировании компонента и открытии дропдауна обновляем данные корзины
  useEffect(() => {
    // При первом рендере загружаем полные данные
    fetchCart();
    // Слушаем событие обновления корзины
    const handleCartUpdated = (event) => {
      // Просто обнови UI, если нужно, но не вызывай fetchCart
    };
    window.addEventListener('cart:updated', handleCartUpdated);
    window.addEventListener('cart:merged', handleCartUpdated);
    return () => {
      window.removeEventListener('cart:updated', handleCartUpdated);
      window.removeEventListener('cart:merged', handleCartUpdated);
    };
  }, [fetchCart]);

  // Обработчик клика вне выпадающего меню
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Обработчик наведения мыши
  const handleMouseEnter = () => {
    clearTimeout(mouseTimeoutRef.current);
    setIsOpen(true);
  };

  // Обработчик ухода мыши
  const handleMouseLeave = () => {
    mouseTimeoutRef.current = setTimeout(() => {
      setIsOpen(false);
    }, 300); // Небольшая задержка чтобы предотвратить случайное закрытие
  };

  // Обработчик удаления товара из корзины
  const handleRemoveItem = async (itemId, event) => {
    // Предотвращаем всплытие события для предотвращения закрытия dropdown
    event.stopPropagation();
    
    // Устанавливаем состояние загрузки для конкретного товара
    setIsRemoving(prev => ({ ...prev, [itemId]: true }));
    
    try {
      await removeFromCart(itemId);
      // После удаления обновляем корзину
      await fetchCart();
    } catch (error) {
      console.error('Ошибка при удалении товара из корзины:', error);
    } finally {
      setIsRemoving(prev => ({ ...prev, [itemId]: false }));
    }
  };

  // Функция для форматирования URL изображения
  const formatImageUrl = (imageUrl) => {
    if (!imageUrl) return null;
    
    // Если URL начинается с http, значит он уже полный
    if (imageUrl.startsWith('http')) {
      return imageUrl;
    }
    
    // Если URL начинается с /, то добавляем базовый URL продуктового сервиса
    if (imageUrl.startsWith('/')) {
      return `${API_URLS.PRODUCT}${imageUrl}`;
    }
    
    // В противном случае просто возвращаем URL как есть
    return imageUrl;
  };

  // Обработчик клика по иконке корзины
  const handleCartIconClick = () => {
    navigate('/cart');
  };

  // Получаем количество уникальных товаров в корзине
  const itemsCount = cart?.items?.length || 0;

  return (
    <div 
      className="cart-icon-container" 
      ref={dropdownRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button 
        className="btn btn-outline-light position-relative"
        onClick={handleCartIconClick}
        aria-expanded={isOpen}
        title="Корзина"
      >
        <i className="bi bi-cart3"></i>
        {itemsCount > 0 && (
          <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
            {itemsCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="cart-dropdown">
          <div className="cart-dropdown-header">
            <h6 className="mb-0">Корзина</h6>
            <button 
              className="btn-close btn-sm" 
              onClick={() => setIsOpen(false)}
              aria-label="Закрыть"
            />
          </div>
          
          <div className="cart-dropdown-body">
            {loading ? (
              <div className="text-center p-3">
                <div className="spinner-border spinner-border-sm text-secondary" role="status">
                  <span className="visually-hidden">Загрузка...</span>
                </div>
                <p className="mt-2">Загрузка корзины...</p>
              </div>
            ) : !cart || !cart.items || cart.items.length === 0 ? (
              <div className="cart-empty text-center py-4">
                <i className="bi bi-cart-x cart-empty-icon"></i>
                <p>Ваша корзина пуста</p>
                <Link 
                  to="/products" 
                  className="btn btn-outline-primary btn-sm"
                  onClick={() => setIsOpen(false)}
                >
                  Перейти к покупкам
                </Link>
              </div>
            ) : (
              <>
                <div className="cart-items">
                  {cart.items.map(item => (
                    <div className="cart-item" key={item.id}>
                      <div className="cart-item-img">
                        {item.product && item.product.image ? (
                          <img 
                            src={formatImageUrl(item.product.image)}
                            alt={item.product?.name || 'Товар'} 
                          />
                        ) : (
                          <div className="no-image">
                            <i className="bi bi-image"></i>
                          </div>
                        )}
                      </div>
                      <div className="cart-item-details">
                        <h6 className="cart-item-title">
                          {item.product?.name || 'Товар недоступен'}
                        </h6>
                        <div className="cart-item-info">
                          <span className="cart-item-quantity">
                            {item.quantity} шт.
                          </span>
                          <span className="cart-item-price">
                            {formatPrice(item.product?.price * item.quantity || 0)} ₽
                          </span>
                        </div>
                      </div>
                      <button 
                        className="cart-item-remove"
                        onClick={(e) => handleRemoveItem(item.id, e)}
                        disabled={isRemoving[item.id]}
                        title="Удалить"
                      >
                        {isRemoving[item.id] ? (
                          <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        ) : (
                          <i className="bi bi-x"></i>
                        )}
                      </button>
                    </div>
                  ))}
                </div>
                
                <div className="cart-summary">
                  <div className="cart-total">
                    <span>Итого:</span>
                    <strong>{formatPrice(cart.total_price)} ₽</strong>
                  </div>
                  <Link 
                    to="/cart" 
                    className="btn btn-primary btn-sm d-block w-100"
                    onClick={() => setIsOpen(false)}
                  >
                    Перейти в корзину
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CartIcon; 