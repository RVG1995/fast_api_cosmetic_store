import React, { memo, useState, useEffect } from 'react';
import useOnlineStatus from '../../hooks/useOnlineStatus';
import './OfflineIndicator.css';

/**
 * Компонент индикатора отсутствия интернет-соединения
 * Отображается, когда пользователь теряет подключение к интернету
 */
const OfflineIndicator = () => {
  const { isOnline, checkConnection } = useOnlineStatus();
  const [visible, setVisible] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    // Скрываем индикатор, если пользователь онлайн
    if (isOnline) {
      // Небольшая задержка перед скрытием для плавности
      const timer = setTimeout(() => {
        setMessage('Подключение восстановлено');
        
        // Скрываем сообщение через 2 секунды
        const hideTimer = setTimeout(() => {
          setVisible(false);
        }, 2000);
        
        return () => clearTimeout(hideTimer);
      }, 500);
      
      return () => clearTimeout(timer);
    } else {
      // Показываем индикатор, если пользователь оффлайн
      setMessage('Отсутствует подключение к интернету');
      setVisible(true);
    }
  }, [isOnline]);

  // Ручная проверка соединения при клике
  const handleRetryClick = async () => {
    setMessage('Проверка подключения...');
    await checkConnection();
  };

  // Если индикатор не должен быть видимым, не рендерим его
  if (!visible) {
    return null;
  }

  return (
    <div className={`offline-indicator ${isOnline ? 'online' : 'offline'}`}>
      <div className="offline-indicator-content">
        <i className={`bi ${isOnline ? 'bi-wifi' : 'bi-wifi-off'} me-2`}></i>
        <span>{message}</span>
        {!isOnline && (
          <button 
            className="offline-retry-button ms-3" 
            onClick={handleRetryClick}
          >
            Повторить
          </button>
        )}
      </div>
    </div>
  );
};

export default memo(OfflineIndicator); 