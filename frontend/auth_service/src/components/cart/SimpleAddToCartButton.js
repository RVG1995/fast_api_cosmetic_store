import React, { useState } from 'react';
import { useCart } from '../../context/CartContext';

const SimpleAddToCartButton = ({ productId, stock, className = '' }) => {
  const { addToCart } = useCart();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  // Обработчик добавления в корзину
  const handleAddToCart = async () => {
    if (stock <= 0) {
      return; // Не выполняем действие, если товара нет в наличии
    }

    setLoading(true);
    
    try {
      // Всегда добавляем 1 штуку товара
      const result = await addToCart(productId, 1);
      
      if (result.success) {
        // Показываем индикатор успеха на короткое время
        setSuccess(true);
        setTimeout(() => setSuccess(false), 1500);
      }
    } catch (err) {
      console.error('Ошибка при добавлении товара в корзину:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button 
      className={`btn ${success ? 'btn-success' : 'btn-primary'} ${className}`}
      onClick={handleAddToCart}
      disabled={loading || stock <= 0}
    >
      {loading ? (
        <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
      ) : success ? (
        <i className="bi bi-check-lg me-2"></i>
      ) : (
        <i className="bi bi-cart-plus me-2"></i>
      )}
      {stock > 0 ? (success ? 'Добавлено' : 'В корзину') : 'Нет в наличии'}
    </button>
  );
};

export default SimpleAddToCartButton; 