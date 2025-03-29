import { useState, useEffect, useRef } from 'react';

/**
 * Хук для создания анимированных переходов между состояниями
 * 
 * @param {any} initialValue - Начальное значение
 * @param {Object} options - Опции анимации
 * @param {number} options.duration - Продолжительность анимации в миллисекундах (по умолчанию 300)
 * @param {string} options.timing - Функция времени CSS (по умолчанию ease)
 * @param {boolean} options.immediate - Применить начальное значение без анимации
 * @returns {Array} [currentValue, setValue, { isAnimating, prevValue }]
 */
function useAnimatedState(initialValue, options = {}) {
  const {
    duration = 300,
    timing = 'ease',
    immediate = true,
  } = options;

  // Текущее значение после анимации
  const [value, setValue] = useState(initialValue);
  
  // Значение, от которого начинается анимация
  const [prevValue, setPrevValue] = useState(immediate ? initialValue : null);
  
  // Флаг, указывающий, идет ли в данный момент анимация
  const [isAnimating, setIsAnimating] = useState(false);
  
  // Таймер для анимации
  const timerRef = useRef(null);

  // Обработка изменения значения
  const updateValue = (newValue) => {
    // Запоминаем предыдущее значение для анимации
    setPrevValue(value);
    
    // Устанавливаем флаг анимации
    setIsAnimating(true);
    
    // Устанавливаем новое значение
    setValue(newValue);
    
    // Очищаем предыдущий таймер, если он был
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    
    // Создаем новый таймер для сброса флага анимации
    timerRef.current = setTimeout(() => {
      setIsAnimating(false);
    }, duration);
  };

  // Очистка таймера при размонтировании компонента
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  // Возвращаем текущее значение, функцию обновления и дополнительную информацию
  return [
    value, 
    updateValue, 
    { 
      isAnimating, 
      prevValue,
      duration,
      timing
    }
  ];
}

export default useAnimatedState; 