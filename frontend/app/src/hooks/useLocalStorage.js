import { useState, useEffect } from 'react';

/**
 * Хук для работы с localStorage
 * @param {string} key - Ключ для хранения в localStorage
 * @param {any} initialValue - Начальное значение
 * @returns {[any, function]} Массив с текущим значением и функцией для его обновления
 */
function useLocalStorage(key, initialValue) {
  // Функция для получения сохраненного значения или использования начального
  const readValue = () => {
    if (typeof window === 'undefined') {
      return initialValue;
    }

    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Ошибка при чтении localStorage ключа "${key}":`, error);
      return initialValue;
    }
  };

  // Инициализация состояния
  const [storedValue, setStoredValue] = useState(readValue);

  // Функция для обновления состояния и localStorage
  const setValue = (value) => {
    try {
      // Проверка, является ли значение функцией
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      
      // Обновляем состояние
      setStoredValue(valueToStore);
      
      // Сохраняем в localStorage
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
        
        // Отправляем событие об изменении хранилища для синхронизации между вкладками
        window.dispatchEvent(new Event('local-storage'));
      }
    } catch (error) {
      console.warn(`Ошибка при сохранении в localStorage ключа "${key}":`, error);
    }
  };

  // Слушаем изменения localStorage из других вкладок
  useEffect(() => {
    const handleStorageChange = () => {
      setStoredValue(readValue());
    };
    
    // Подписываемся на событие 'storage' для синхронизации между вкладками
    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('local-storage', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('local-storage', handleStorageChange);
    };
  }, []);

  return [storedValue, setValue];
}

export default useLocalStorage; 