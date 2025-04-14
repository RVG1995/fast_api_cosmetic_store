import React, { useState, useEffect, useCallback } from 'react';
import './Toast.css';

// Иконки для разных типов уведомлений
const ICONS = {
  success: <i className="bi bi-check-circle-fill"></i>,
  danger: <i className="bi bi-exclamation-circle-fill"></i>,
  warning: <i className="bi bi-exclamation-triangle-fill"></i>,
  info: <i className="bi bi-info-circle-fill"></i>,
};

// Компонент отдельного уведомления
const ToastItem = ({ id, message, type = 'info', onClose }) => {
  const [isExiting, setIsExiting] = useState(false);

  // Функция закрытия с анимацией
  const handleClose = useCallback(() => {
    setIsExiting(true);
    // Ждем завершения анимации выхода перед удалением
    setTimeout(() => {
      onClose(id);
    }, 300); // Длительность анимации в мс
  }, [id, onClose]);

  // Автоматическое закрытие через 3 секунды
  useEffect(() => {
    const timer = setTimeout(() => {
      handleClose();
    }, 3000);
    
    return () => clearTimeout(timer);
  }, [handleClose]);

  return (
    <div className={`toast toast-${type} ${isExiting ? 'toast-exit' : ''}`}>
      <div className="toast-icon">
        {ICONS[type] || ICONS.info}
      </div>
      <div className="toast-body">
        {message}
      </div>
      <button className="toast-close" onClick={handleClose}>
        ×
      </button>
    </div>
  );
};

// Главный компонент для всплывающих уведомлений
const Toast = () => {
  const [toasts, setToasts] = useState([]);

  // Функция для добавления уведомления
  const addToast = useCallback((message, type = 'info') => {
    console.log('Добавляем toast:', message, type);
    const id = Date.now();
    setToasts(prevToasts => [...prevToasts, { id, message, type }]);
  }, []);

  // Функция для удаления уведомления
  const removeToast = useCallback((id) => {
    setToasts(prevToasts => prevToasts.filter(toast => toast.id !== id));
  }, []);

  // Слушаем событие для отображения уведомления
  useEffect(() => {
    const handleToastEvent = (event) => {
      console.log('Получено событие show:toast:', event.detail);
      const { message, type } = event.detail;
      addToast(message, type);
    };

    // Добавляем обработчик события
    console.log('Добавляем слушатель события show:toast');
    window.addEventListener('show:toast', handleToastEvent);

    // Удаляем обработчик при размонтировании
    return () => {
      console.log('Удаляем слушатель события show:toast');
      window.removeEventListener('show:toast', handleToastEvent);
    };
  }, [addToast]);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map(toast => (
        <ToastItem
          key={toast.id}
          id={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={removeToast}
        />
      ))}
    </div>
  );
};

export default Toast; 