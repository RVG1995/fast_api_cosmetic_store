import React, { useState } from 'react';
import { useCart } from '../../context/CartContext';
import './AddToCartButton.css';

const AddToCartButton = ({ productId, stock, className = '' }) => {
  const { addToCart } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Обработчик изменения количества
  const handleQuantityChange = (value) => {
    const newValue = parseInt(value, 10);
    if (isNaN(newValue) || newValue < 1) {
      setQuantity(1);
    } else if (newValue > stock) {
      setQuantity(stock);
    } else {
      setQuantity(newValue);
    }
  };

  // Функция для создания всплывающего уведомления
  const showToast = (message, type) => {
    // Создаем и отправляем событие для отображения уведомления
    window.dispatchEvent(
      new CustomEvent('show:toast', {
        detail: { message, type }
      })
    );
  };

  // Обработчик добавления в корзину
  const handleAddToCart = async () => {
    if (stock <= 0) {
      showToast('Товар отсутствует на складе', 'danger');
      return;
    }

    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const result = await addToCart(productId, quantity);
      
      if (result.success) {
        setMessage({ type: 'success', text: 'Товар добавлен в корзину' });
      } else {
        // Показываем ошибку как всплывающее уведомление
        showToast(result.message, 'danger');
        
        // Для ошибок о недостаточном количестве товара не показываем сообщение под кнопкой
        if (result.message.includes('Недостаточно товара') || 
            result.message.includes('максимально доступное количество')) {
          setMessage({ type: '', text: '' });
        } else {
          // Для других ошибок оставляем сообщение под кнопкой
          setMessage({ type: 'danger', text: result.message });
        }
      }
    } catch (err) {
      showToast('Ошибка при добавлении товара в корзину', 'danger');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`add-to-cart-container ${className}`}>
      <div className="d-flex align-items-center mb-2">
        <div className="input-group me-2" style={{ width: '120px' }}>
          <button 
            className="btn btn-outline-secondary" 
            type="button"
            onClick={() => handleQuantityChange(quantity - 1)}
            disabled={loading || stock <= 0 || quantity <= 1}
          >
            <i className="bi bi-dash"></i>
          </button>
          <input 
            type="number" 
            className="form-control text-center"
            value={quantity}
            onChange={(e) => handleQuantityChange(e.target.value)}
            min="1"
            max={stock}
            disabled={loading || stock <= 0}
          />
          <button 
            className="btn btn-outline-secondary" 
            type="button"
            onClick={() => handleQuantityChange(quantity + 1)}
            disabled={loading || stock <= 0 || quantity >= stock}
          >
            <i className="bi bi-plus"></i>
          </button>
        </div>
        
        <button 
          className="btn btn-primary flex-grow-1"
          onClick={handleAddToCart}
          disabled={loading || stock <= 0}
        >
          {loading ? (
            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
          ) : (
            <i className="bi bi-cart-plus me-2"></i>
          )}
          {stock > 0 ? 'В корзину' : 'Нет в наличии'}
        </button>
      </div>
      
      {message.text && (
        <div className={`alert alert-${message.type} py-2 px-3 mb-0`} role="alert">
          {message.text}
        </div>
      )}
      
      {stock > 0 && stock <= 5 && (
        <div className="text-danger small mt-1">
          <i className="bi bi-exclamation-triangle me-1"></i>
          Осталось всего {stock} шт.
        </div>
      )}
    </div>
  );
};

export default AddToCartButton; 