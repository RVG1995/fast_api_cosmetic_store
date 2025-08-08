import React, { useState } from 'react';
import PropTypes from 'prop-types';

const StarRating = ({ initialRating = 0, onRatingChange, size = 'lg', interactive = true }) => {
  const [rating, setRating] = useState(initialRating);
  const [hoverRating, setHoverRating] = useState(0);

  // Создаем обработчик клика по звезде
  const handleClick = (value) => {
    if (!interactive) return;
    
    // Если нажали на текущий рейтинг - сбрасываем до нуля
    const newRating = value === rating ? 0 : value;
    setRating(newRating);
    
    // Вызываем callback, если он передан
    if (onRatingChange) {
      onRatingChange(newRating);
    }
  };

  // Обработчики для эффекта при наведении
  const handleMouseEnter = (value) => {
    if (!interactive) return;
    setHoverRating(value);
  };

  const handleMouseLeave = () => {
    if (!interactive) return;
    setHoverRating(0);
  };

  // Определяем размер звезд
  const getStarSize = () => {
    switch (size) {
      case 'sm': return { fontSize: '1rem' };
      case 'lg': return { fontSize: '1.75rem' };
      case 'xl': return { fontSize: '2.25rem' };
      default: return { fontSize: '1.5rem' }; // 'md' - средний размер
    }
  };

  // Возвращаем разметку со звездами
  return (
    <div className="star-rating d-flex align-items-center">
      {[1, 2, 3, 4, 5].map((star) => {
        // Определяем, закрашена ли звезда
        const isFilled = star <= (hoverRating || rating);
        
        return (
          <button
            key={star}
            type="button"
            onClick={() => handleClick(star)}
            onMouseEnter={() => handleMouseEnter(star)}
            onMouseLeave={handleMouseLeave}
            style={{
              cursor: interactive ? 'pointer' : 'default',
              ...getStarSize(),
              padding: '0 0.2rem'
            }}
            aria-label={interactive ? `Оценить на ${star} из 5` : `${rating} из 5 звезд`}
          >
            <i 
              className={isFilled ? 'bi bi-star-fill text-warning' : 'bi bi-star text-muted'}
            />
          </button>
        );
      })}
      
      {rating > 0 && (
        <span className="ms-2 badge bg-warning">{rating}/5</span>
      )}
    </div>
  );
};

export default StarRating; 

StarRating.propTypes = {
  initialRating: PropTypes.number,
  onRatingChange: PropTypes.func,
  size: PropTypes.oneOf(['sm', 'md', 'lg', 'xl']),
  interactive: PropTypes.bool,
};