import { useState, useEffect } from 'react';

/**
 * Хук для дебоунса значений, позволяющий уменьшить количество обновлений состояния
 * при частых изменениях (например, при вводе пользователя)
 * 
 * @param {any} value - Исходное значение для дебоунса
 * @param {number} delay - Задержка в миллисекундах
 * @returns {any} Дебоунсированное значение
 */
function useDebouncedValue(value, delay = 500) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    // Создаем таймер, который обновит значение после указанной задержки
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Очищаем предыдущий таймер при каждом изменении value или delay
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

export default useDebouncedValue; 