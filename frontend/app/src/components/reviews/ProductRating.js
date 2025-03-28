import React, { useEffect, useState } from 'react';
import { reviewAPI } from '../../utils/api';

const ProductRating = ({ productId, size = 'sm', showText = true }) => {
  const [rating, setRating] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRating = async () => {
      if (!productId) return;
      
      setLoading(true);
      try {
        const response = await reviewAPI.getProductStats(productId);
        setRating(response.data.average_rating);
      } catch (error) {
        console.error('Ошибка при загрузке рейтинга:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRating();
  }, [productId]);

  if (loading || rating === null) return null;

  // Если нет отзывов или рейтинг 0, не показываем ничего
  if (!rating) return null;

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
  const roundedRating = Math.round(rating * 2) / 2; // Округляем до ближайшего 0.5

  return (
    <div className="product-rating d-flex align-items-center">
      {[1, 2, 3, 4, 5].map((i) => {
        // Определяем заполнение звезды (полная, половина или пустая)
        const starClass = i <= Math.floor(roundedRating)
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
      
      {showText && (
        <span className="ms-1" style={{ fontSize }}>
          {rating.toFixed(1)}
        </span>
      )}
    </div>
  );
};

export default ProductRating; 