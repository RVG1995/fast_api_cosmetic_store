import React, { useState } from 'react';
import { useCart } from '../../context/CartContext';
import './SimpleAddToCartButton.css';

const SimpleAddToCartButton = ({ productId, stock, className = '' }) => {
  const { addToCart } = useCart();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  // Функция для создания всплывающего уведомления
  const showToast = (message, type) => {
    console.log('Показываю toast:', message, type);
    // Создаем и отправляем событие для отображения уведомления
    window.dispatchEvent(
      new CustomEvent('show:toast', {
        detail: { message, type }
      })
    );
    console.log('Toast событие отправлено');
  };

  // Обработчик добавления в корзину
  const handleAddToCart = async () => {
    if (stock <= 0) {
      showToast('Товар отсутствует на складе', 'danger');
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
        // Успешное добавление - показываем toast
        showToast('Товар добавлен в корзину', 'success');
      } else {
        // Проверяем сообщение об ошибке на наличие ключевых слов, связанных с наличием товара
        const errorMsg = result.message || '';
        const stockRelatedError = 
          errorMsg.includes('недостаточно') || 
          errorMsg.includes('наличии') || 
          errorMsg.includes('запасе') || 
          errorMsg.includes('stock') ||
          errorMsg.includes('количество');
        
        // Показываем оригинальное сообщение об ошибке от API вместо фиксированного текста
        if (stockRelatedError) {
          showToast(errorMsg, 'danger');
          setError('');
        } else if (result.error) {
          showToast(result.error, 'danger');
          setError(result.error);
        } else {
          showToast(errorMsg || 'Ошибка при добавлении товара', 'danger');
          setError('Ошибка при добавлении товара');
        }
        
        setTimeout(() => setError(''), 3000); // Скрываем ошибку через 3 секунды
      }
    } catch (err) {
      console.error('Ошибка при добавлении товара в корзину:', err);
      showToast('Ошибка при добавлении товара в корзину', 'danger');
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
      
      {/* Убираем отображение ошибки под кнопкой, так как теперь используем Toast */}
      {/* {error && (
        <div className="error-tooltip">{error}</div>
      )} */}
    </div>
  );
};

export default SimpleAddToCartButton; 