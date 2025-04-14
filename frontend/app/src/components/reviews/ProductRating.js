import React, { useEffect, useState } from 'react';
import { useReviews } from '../../context/ReviewContext';
import { reviewAPI } from '../../utils/api';
import './ProductRating.css';

const ProductRating = ({ productId, size = 'sm', showText = true, useDirectFetch = false, reloadKey = 0, className = '' }) => {
  const { getProductRating } = useReviews();
  const [localRating, setLocalRating] = useState(null);
  const [localTotalReviews, setLocalTotalReviews] = useState(0);
  const [loading, setLoading] = useState(false);
  
  // Получаем рейтинг из контекста, если не нужно прямое обращение к API
  const productData = !useDirectFetch ? getProductRating(productId) : null;
  
  // Если нужно прямое обращение к API (для страницы отдельного товара)
  useEffect(() => {
    if (useDirectFetch && productId) {
      setLoading(true);
      reviewAPI.getProductStats(productId)
        .then(response => {
          console.log(`ProductRating: Получены данные для товара ${productId}:`, response.data);
          setLocalRating(response.data.average_rating);
          setLocalTotalReviews(response.data.total_reviews);
        })
        .catch(error => {
          console.error('Ошибка при загрузке рейтинга:', error);
          setLocalRating(0);
          setLocalTotalReviews(0);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [productId, useDirectFetch, reloadKey]); // Добавляем reloadKey для принудительной перезагрузки
  
  // Определяем финальные значения
  const rating = useDirectFetch ? localRating : (productData ? productData.average_rating : 0);
  const totalReviews = useDirectFetch ? localTotalReviews : (productData ? productData.total_reviews : 0);
  
  // Если идет загрузка при прямом запросе, показываем заглушку
  if (useDirectFetch && loading) {
    return <div className="product-rating-skeleton"></div>;
  }

  // Определяем размер звезд
  const getFontSize = () => {
    switch (size) {
      case 'xs': return '0.75rem';
      case 'sm': return '0.9rem';
      case 'md': return '1.1rem';
      case 'lg': return '1.3rem';
      default: return '0.9rem';
    }
  };

  const fontSize = getFontSize();
  const roundedRating = rating ? Math.round(rating * 2) / 2 : 0; // Округляем до ближайшего 0.5

  return (
    <div className={`product-rating d-flex align-items-center ${className}`}>
      <div className="stars-container">
        {[1, 2, 3, 4, 5].map((i) => {
          // Определяем заполнение звезды (полная, половина или пустая)
          const starClass = rating && i <= Math.floor(roundedRating)
            ? 'bi bi-star-fill text-warning'
            : 'bi bi-star text-muted';
          
          return (
            <i
              key={i}
              className={starClass}
              style={{ fontSize, marginRight: '2px' }}
            />
          );
        })}
      </div>
      
      {showText && (
        <span className="ms-1 rating-text" style={{ fontSize, whiteSpace: 'nowrap' }}>
          {rating ? rating.toFixed(1) : 'Нет отзывов'}
          {totalReviews > 0 && ` (${totalReviews})`}
        </span>
      )}
    </div>
  );
};

export default ProductRating; 