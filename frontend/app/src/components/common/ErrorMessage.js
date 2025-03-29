import React from 'react';
import '../../styles/ErrorMessage.css';

const ErrorMessage = ({ 
  error, 
  title = 'Ошибка', 
  retry = null, 
  className = '',
  variant = 'danger' // danger, warning, info
}) => {
  if (!error) return null;
  
  // Парсинг ошибок API если они в JSON формате
  let errorMessage = error;
  if (typeof error === 'object') {
    if (error.message) {
      errorMessage = error.message;
    } else if (error.detail) {
      errorMessage = error.detail;
    } else {
      try {
        errorMessage = JSON.stringify(error);
      } catch (e) {
        errorMessage = 'Неизвестная ошибка';
      }
    }
  }
  
  // Улучшенные сообщения для часто встречающихся ошибок
  if (typeof errorMessage === 'string') {
    if (errorMessage.includes('network') || errorMessage.includes('соединение')) {
      errorMessage = 'Проблема с подключением к интернету. Проверьте соединение и попробуйте снова.';
    } else if (errorMessage.includes('timeout') || errorMessage.includes('таймаут')) {
      errorMessage = 'Превышено время ожидания ответа от сервера. Пожалуйста, попробуйте позже.';
    } else if (errorMessage.includes('401') || errorMessage.includes('unauthorized')) {
      errorMessage = 'Необходимо авторизоваться для выполнения этого действия.';
    } else if (errorMessage.includes('403') || errorMessage.includes('forbidden')) {
      errorMessage = 'У вас нет прав доступа к этому ресурсу.';
    } else if (errorMessage.includes('404') || errorMessage.includes('not found')) {
      errorMessage = 'Запрашиваемый ресурс не найден.';
    } else if (errorMessage.includes('500') || errorMessage.includes('server error')) {
      errorMessage = 'Произошла ошибка на сервере. Пожалуйста, попробуйте позже.';
    }
  }
  
  return (
    <div className={`error-message-container alert alert-${variant} ${className}`}>
      <div className="error-icon">
        {variant === 'danger' && <i className="bi bi-exclamation-triangle-fill"></i>}
        {variant === 'warning' && <i className="bi bi-exclamation-circle-fill"></i>}
        {variant === 'info' && <i className="bi bi-info-circle-fill"></i>}
      </div>
      <div className="error-content">
        <h4 className="error-title">{title}</h4>
        <p className="error-text">{errorMessage}</p>
        {retry && (
          <button 
            className={`btn btn-outline-${variant} btn-sm mt-2`} 
            onClick={retry}
          >
            <i className="bi bi-arrow-repeat me-1"></i>
            Повторить
          </button>
        )}
      </div>
    </div>
  );
};

export default ErrorMessage; 