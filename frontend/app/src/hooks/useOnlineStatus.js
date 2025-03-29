import { useState, useEffect } from 'react';

/**
 * Хук для отслеживания онлайн/офлайн статуса приложения
 * @returns {Object} Объект с информацией о статусе соединения
 * @returns {boolean} Object.isOnline - флаг онлайн статуса
 * @returns {function} Object.checkConnection - функция для проверки соединения
 */
function useOnlineStatus() {
  // Изначально считаем, что соединение есть, если браузер говорит, что оно есть
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' && typeof navigator.onLine === 'boolean' 
      ? navigator.onLine 
      : true
  );

  // Дополнительно проверяем соединение, делая запрос к серверу
  const checkConnection = async () => {
    try {
      // Создаем временную метку, чтобы избежать кэширования
      const timestamp = new Date().getTime();
      // Делаем запрос к Google, как к стабильному ресурсу
      await fetch(`https://www.google.com/favicon.ico?${timestamp}`, {
        mode: 'no-cors', // no-cors для работы с CORS ограничениями
        cache: 'no-store' // Избегаем кэширования
      });
      
      // Если получили ответ, значит мы онлайн
      setIsOnline(true);
      return true;
    } catch (error) {
      // Если ошибка, значит мы офлайн
      setIsOnline(false);
      return false;
    }
  };

  useEffect(() => {
    // Устанавливаем начальный статус при монтировании
    checkConnection();

    // Обработчик изменения онлайн статуса
    const handleOnline = () => {
      setIsOnline(true);
    };

    // Обработчик изменения офлайн статуса
    const handleOffline = () => {
      setIsOnline(false);
    };

    // Добавляем слушатели событий
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Периодически проверяем соединение (каждые 30 секунд)
    const intervalId = setInterval(checkConnection, 30000);

    // Удаляем слушатели при размонтировании
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(intervalId);
    };
  }, []);

  return { isOnline, checkConnection };
}

export default useOnlineStatus; 