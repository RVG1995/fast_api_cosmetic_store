import React, { memo } from 'react';
import './Button.module.css';

const Button = ({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  onClick, 
  disabled = false, 
  type = 'button',
  className = '',
  isLoading = false,
  icon = null,
  fullWidth = false,
  ...rest
}) => {
  // Используем стандартный класс bootstrap с дополнительными классами из модуля
  const buttonClass = `btn btn-${variant} btn-${size} ${fullWidth ? 'w-100' : ''} ${className}`;
  
  return (
    <button
      type={type}
      className={buttonClass}
      onClick={onClick}
      disabled={disabled || isLoading}
      {...rest}
    >
      {isLoading ? (
        <>
          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
          <span className="visually-hidden">Загрузка...</span>
        </>
      ) : icon && (
        <i className={`bi bi-${icon} me-2`}></i>
      )}
      {children}
    </button>
  );
};

export default memo(Button); 