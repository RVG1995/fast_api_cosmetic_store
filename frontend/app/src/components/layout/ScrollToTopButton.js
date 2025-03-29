import React, { useState, useEffect, useCallback, memo } from 'react';
import './ScrollToTopButton.css';

/**
 * Кнопка для прокрутки страницы вверх, которая появляется 
 * после прокрутки на определенное расстояние
 */
const ScrollToTopButton = ({ 
  showAfter = 300, 
  position = 'right',
  smoothScroll = true,
  className = ''
}) => {
  const [isVisible, setIsVisible] = useState(false);

  // Обработчик прокрутки
  const handleScroll = useCallback(() => {
    // Показываем кнопку, если прокрутка превышает указанное значение
    setIsVisible(window.pageYOffset > showAfter);
  }, [showAfter]);

  // Прокрутка страницы вверх
  const scrollToTop = useCallback(() => {
    if (smoothScroll) {
      // Плавная прокрутка
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    } else {
      // Мгновенная прокрутка
      window.scrollTo(0, 0);
    }
  }, [smoothScroll]);

  // Устанавливаем обработчик события прокрутки
  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    
    // Проверяем начальное положение прокрутки
    handleScroll();
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [handleScroll]);

  // Если кнопка не видима, не рендерим ее
  if (!isVisible) {
    return null;
  }

  // Определяем класс позиции
  const positionClass = position === 'left' ? 'left' : 'right';
  
  return (
    <button 
      className={`scroll-to-top-button ${positionClass} ${className}`}
      onClick={scrollToTop}
      aria-label="Прокрутить наверх"
    >
      <i className="bi bi-arrow-up-circle-fill"></i>
    </button>
  );
};

export default memo(ScrollToTopButton); 