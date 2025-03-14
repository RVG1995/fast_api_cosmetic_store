import React, { useState } from 'react';
import { useCart } from '../../context/CartContext';
import './SimpleAddToCartButton.css';

const SimpleAddToCartButton = ({ productId, stock, className = '' }) => {
  const { addToCart } = useCart();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  // Обработчик добавления в корзину
  const handleAddToCart = async () => {
    if (stock <= 0) {
      setError('Товар отсутствует на складе');
      setTimeout(() => setError(''), 3000);
      return;
    }

    setLoading(true);
    setError(''); // Сбрасываем ошибку при каждой попытке
    
    try {
      // Всегда добавляем 1 штуку товара
      const result = await addToCart(productId, 1);
      
      if (result.success) {
        // Показываем индикатор успеха на короткое время
        setSuccess(true);
        setTimeout(() => setSuccess(false), 1500);
      } else {
        // Показываем сообщение об ошибке
        // Проверяем сообщение об ошибке на наличие ключевых слов, связанных с наличием товара
        const errorMsg = result.message || '';
        const stockRelatedError = 
          errorMsg.includes('недостаточно') || 
          errorMsg.includes('наличии') || 
          errorMsg.includes('запасе') || 
          errorMsg.includes('stock') ||
          errorMsg.includes('количество');
        
        if (stockRelatedError) {
          setError('Недостаточно товара на складе');
        } else if (result.error) {
          setError(result.error);
        } else {
          setError('Ошибка при добавлении товара');
        }
        
        setTimeout(() => setError(''), 3000); // Скрываем ошибку через 3 секунды
      }
    } catch (err) {
      console.error('Ошибка при добавлении товара в корзину:', err);
      setError('Ошибка при добавлении товара');
      setTimeout(() => setError(''), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="simple-add-to-cart-container">
      <button 
        className={`btn ${success ? 'btn-success' : error ? 'btn-danger' : 'btn-primary'} ${className}`}
        onClick={handleAddToCart}
        disabled={loading || stock <= 0}
      >
        {loading ? (
          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
        ) : error ? (
          <i className="bi bi-exclamation-triangle me-2"></i>
        ) : success ? (
          <i className="bi bi-check-lg me-2"></i>
        ) : (
          <i className="bi bi-cart-plus me-2"></i>
        )}
        {stock > 0 ? (
          error ? 'Ошибка' : success ? 'Добавлено' : 'В корзину'
        ) : 'Нет в наличии'}
      </button>
      
      {error && (
        <div className="error-tooltip">{error}</div>
      )}
    </div>
  );
};

export default SimpleAddToCartButton; 